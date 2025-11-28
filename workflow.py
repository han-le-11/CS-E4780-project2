# -*- encoding: utf-8 -*-
# File: workflow.py
# Description: None

import os
from typing import Any, Union

import dspy
import kuzu
from dotenv import load_dotenv
from pydantic import BaseModel
from pydantic import Field


class Query(BaseModel):
    query: str = Field(description="Valid Cypher query with no newlines")


class Property(BaseModel):
    name: str
    type: str = Field(description="Data type of the property")


class Node(BaseModel):
    label: str
    properties: list[Property] | None


class Edge(BaseModel):
    label: str = Field(description="Relationship label")
    from_: Union[str, Node] = Field(alias="from", description="Source node label")
    to: Union[str, Node] = Field(alias="to", description="Target node label")
    properties: list[Property] | None


class GraphSchema(BaseModel):
    nodes: list[Node]
    edges: list[Edge]


class PruneSchema(dspy.Signature):
    """
    Understand the given labelled property graph schema and the given user question. Your task
    is to return ONLY the subset of the schema (node labels, edge labels and properties) that is
    relevant to the question.
        - The schema is a list of nodes and edges in a property graph.
        - The nodes are the entities in the graph.
        - The edges are the relationships between the nodes.
        - Properties of nodes and edges are their attributes, which helps answer the question.
    """

    question: str = dspy.InputField()
    input_schema: str = dspy.InputField()
    pruned_schema: GraphSchema = dspy.OutputField()

    def __post_init__(self):
        node_label_to_node = {}
        for nodes in self.pruned_schema.nodes:
            node_label_to_node[nodes.label] = nodes
        for edge in self.pruned_schema.edges:
            if isinstance(edge.from_, str):
                edge.from_ = node_label_to_node[edge.from_]
            if isinstance(edge.to, str):
                edge.to = node_label_to_node[edge.to]

        return self.pruned_schema


class Text2Cypher(dspy.Signature):
    """
    Translate the question into a valid Cypher query that respects the graph schema.

    <SYNTAX>
    - When matching on Scholar names, ALWAYS match on the `knownName` property
    - For countries, cities, continents and institutions, you can match on the `name` property
    - Use short, concise alphanumeric strings as names of variable bindings (e.g., `a1`, `r1`, etc.)
    - Always strive to respect the relationship direction (FROM/TO) using the schema information.
    - When comparing string properties, ALWAYS do the following:
        - Lowercase the property values before comparison
        - Use the WHERE clause
        - Use the CONTAINS operator to check for presence of one substring in the other
    - DO NOT use APOC as the database does not support it.
    </SYNTAX>

    <RETURN_RESULTS>
    - If the result is an integer, return it as an integer (not a string).
    - When returning results, return property values rather than the entire node or relationship.
    - Do not attempt to coerce data types to number formats (e.g., integer, float) in your results.
    - NO Cypher keywords should be returned by your query.
    </RETURN_RESULTS>
    """

    question: str = dspy.InputField()
    input_schema: str = dspy.InputField()
    query: Query = dspy.OutputField()


class AnswerQuestion(dspy.Signature):
    """
    - Use the provided question, the generated Cypher query and the context to answer the question.
    - If the context is empty, state that you don't have enough information to answer the question.
    - When dealing with dates, mention the month in full.
    """

    question: str = dspy.InputField()
    cypher_query: str = dspy.InputField()
    context: str = dspy.InputField()
    response: str = dspy.OutputField()


def create_graph_db(db_name: str):
    """
    Create a graph database connection.

    Args:
        connection_string (str): The connection string for the graph database.

    Returns:
        A graph database connection instance.
    """
    db = kuzu.Database(db_name, read_only=True)
    conn = kuzu.Connection(db)
    return (conn,)


class KuzuDatabaseManager:
    """Manages Kuzu database connection and schema retrieval."""

    def __init__(self, db_path: str = "ldbc_1.kuzu"):
        self.db_path = db_path
        self.db = kuzu.Database(db_path, read_only=True)
        self.conn = kuzu.Connection(self.db)

    @property
    def get_schema_dict(self) -> dict[str, list[dict]]:
        response = self.conn.execute("CALL SHOW_TABLES() WHERE type = 'NODE' RETURN *;")
        nodes = [row[1] for row in response]  # type: ignore
        response = self.conn.execute("CALL SHOW_TABLES() WHERE type = 'REL' RETURN *;")
        rel_tables = [row[1] for row in response]  # type: ignore
        relationships = []
        for tbl_name in rel_tables:
            response = self.conn.execute(f"CALL SHOW_CONNECTION('{tbl_name}') RETURN *;")
            for row in response:
                relationships.append({"name": tbl_name, "from": row[0], "to": row[1]})  # type: ignore
        schema = {"nodes": [], "edges": []}

        for node in nodes:
            node_schema = {"label": node, "properties": []}
            node_properties = self.conn.execute(f"CALL TABLE_INFO('{node}') RETURN *;")
            for row in node_properties:  # type: ignore
                node_schema["properties"].append({"name": row[1], "type": row[2]})  # type: ignore
            schema["nodes"].append(node_schema)

        for rel in relationships:
            edge = {
                "label": rel["name"],
                "from": rel["from"],
                "to": rel["to"],
                "properties": [],
            }
            rel_properties = self.conn.execute(f"""CALL TABLE_INFO('{rel["name"]}') RETURN *;""")
            for row in rel_properties:  # type: ignore
                edge["properties"].append({"name": row[1], "type": row[2]})  # type: ignore
            schema["edges"].append(edge)
        return schema


class GraphRAG(dspy.Module):
    """
    DSPy custom module that applies Text2Cypher to generate a query and run it
    on the Kuzu database, to generate a natural language response.
    """

    def __init__(self):
        self.prune = dspy.Predict(PruneSchema)
        self.text2cypher = dspy.ChainOfThought(Text2Cypher)
        self.generate_answer = dspy.ChainOfThought(AnswerQuestion)

    def get_cypher_query(self, question: str, input_schema: str) -> Query:
        prune_result = self.prune(question=question, input_schema=input_schema)
        schema = prune_result.pruned_schema
        text2cypher_result = self.text2cypher(question=question, input_schema=schema)
        cypher_query = text2cypher_result.query
        return cypher_query

    def run_query(
        self,
        db_manager: KuzuDatabaseManager,
        question: str,
        input_schema: str,
    ) -> tuple[str, list[Any] | None]:
        """
        Run a query synchronously on the database.
        """
        result = self.get_cypher_query(question=question, input_schema=input_schema)
        query = result.query
        try:
            # Run the query on the database
            result = db_manager.conn.execute(query)
            results = [item for row in result for item in row]
        except RuntimeError as e:
            print(f"Error running query: {e}")
            results = None
        return query, results

    def forward(self, db_manager: KuzuDatabaseManager, question: str, input_schema: str):
        final_query, final_context = self.run_query(db_manager, question, input_schema)
        if final_context is None:
            print("Empty results obtained from the graph database. Please retry with a different question.")
            return {}
        else:
            answer = self.generate_answer(question=question, cypher_query=final_query, context=str(final_context))
            response = {
                "question": question,
                "query": final_query,
                "answer": answer,
            }
            return response

    async def aforward(self, db_manager: KuzuDatabaseManager, question: str, input_schema: str):
        final_query, final_context = self.run_query(db_manager, question, input_schema)
        if final_context is None:
            print("Empty results obtained from the graph database. Please retry with a different question.")
            return {}
        else:
            answer = self.generate_answer(question=question, cypher_query=final_query, context=str(final_context))
            response = {
                "question": question,
                "query": final_query,
                "answer": answer,
            }
            return response


def run_graph_rag(questions: list[str], db_manager: KuzuDatabaseManager) -> list[Any]:
    schema = str(db_manager.get_schema_dict)
    rag = GraphRAG()
    # Run pipeline
    results = []
    for question in questions:
        response = rag(db_manager=db_manager, question=question, input_schema=schema)
        results.append(response)
    return results


def create_LM():
    load_dotenv()

    OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
    API_BASE_URL = os.environ.get("API_BASE_URL")
    MODEL = os.environ.get("MODEL", "openai/qwen3-8b")

    # Using OpenRouter. Switch to another LLM provider as needed
    # we recommend gemini-2.0-flash for the cost-efficiency
    lm = dspy.LM(
        model=MODEL,
        api_base=API_BASE_URL,
        api_key=OPENROUTER_API_KEY,
    )
    dspy.configure(lm=lm)
    return lm


def main():
    questions = [
        "Which scholars won prizes in Physics and were affiliated with University of Cambridge?",
        # "List the Nobel laureates in Chemistry from USA.",
        # "Who are the Nobel Prize winners in Literature born before 1900?",
    ]
    create_LM()

    db_manager = KuzuDatabaseManager("nobel.kuzu")
    results = run_graph_rag(questions, db_manager)
    for res in results:
        print(res)


if __name__ == "__main__":
    main()
