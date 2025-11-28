# -*- encoding: utf-8 -*-
# File: workflow.py
# Description: Enhanced workflow for GraphRAG with dynamic examples and self-refinement.

import json
import os
import re
import time
from typing import Any, Tuple, Union

import dspy
import kuzu
from dotenv import load_dotenv
from functools import lru_cache
from pydantic import BaseModel, Field
from tqdm import tqdm
from sentence_transformers import SentenceTransformer, util

# Import few-shot examples
from exemplars import exemplars


# === Timer ===
class StatTracker(object):
    def __init__(self):
        self._stats = []
        self._tag = "default"

    def set_tag(self, tag: str):
        self._tag = tag

    def timeit(self, name: str, **kwargs):
        class TimerContext(object):
            def __enter__(inner_self):
                inner_self.start = time.perf_counter()
                return inner_self

            def __exit__(inner_self, type, value, traceback):
                end_timestamp = time.perf_counter()
                duration = end_timestamp - inner_self.start
                stat_entry = {
                    "name": name,
                    "tag": self._tag,
                    "duration": duration,
                    "start_timestamp": inner_self.start,
                    "end_timestamp": end_timestamp,
                }
                stat_entry["info"] = kwargs
                self._stats.append(stat_entry)

        return TimerContext()

    def get_all_stats(self):
        return self._stats

    def clear_all_stats(self):
        self._stats = []


def dump_stats(path: str, stats):
    with open(path, "w") as f:
        for stat in tqdm(stats):
            f.write(f"{json.dumps(stat)}\n")


_TRACKER = StatTracker()


def timeit(name: str, **kwargs):
    return _TRACKER.timeit(name, **kwargs)


# === Pydantic Models for Data Validation ===
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


# === DSPy Signatures ===
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


# === Database Manager ===
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


# === Enhanced GraphRAG Module ===
class GraphRAG(dspy.Module):
    """
    DSPy custom module that applies Text2Cypher to generate a query and run it
    on the Kuzu database, to generate a natural language response.
    """

    def __init__(self, k=2):
        super().__init__()
        self.prune = dspy.Predict(PruneSchema)

        # Dynamic few-shot exemplar selection
        self.k = k
        self.retriever_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.trainset = exemplars
        exemplar_questions = [ex["question"] for ex in self.trainset]
        self.trainset_embeddings = self.retriever_model.encode(exemplar_questions, convert_to_tensor=True)

        self.text2cypher = dspy.ChainOfThought(Text2Cypher)
        self.generate_answer = dspy.ChainOfThought(AnswerQuestion)


    def _get_retrieved_examples(self, question: str) -> list[dspy.Example]:
        """Manually retrieve k-similar examples using sentence-transformers."""
        question_embedding = self.retriever_model.encode(question, convert_to_tensor=True)
        hits = util.semantic_search(question_embedding, self.trainset_embeddings, top_k=self.k)
        retrieved_data = [self.trainset[hit['corpus_id']] for hit in hits[0]]
        return [dspy.Example(question=ex["question"], query=ex["query"]) for ex in retrieved_data]

    def _validate_and_repair_query(self, db_manager: KuzuDatabaseManager, query: str, max_retries: int = 2) -> str:
        """
        Self-refinement loop: generate -> validate (syntax check) -> repair.
        """
        for i in range(max_retries):
            try:
                db_manager.conn.execute(f"EXPLAIN {query}")  # Syntax check
                print("Query syntax is valid.")
                return self._post_process_query(query)
            except Exception as e:
                print(f"Query validation failed on attempt {i + 1}: {e}. Repairing...")
                response = self.text2cypher(
                    question=f"The previous query failed. Fix this query: {query}. Error: {e}",
                    input_schema=""  # Schema might not be needed for simple repairs
                )
                query = response.query.query

        print("Could not repair the query after multiple attempts.")
        return self._post_process_query(query)

    def _post_process_query(self, query: str) -> str:
        """
        3. Rule-based post-processor.
        """
        # Enforce lowercase on string comparisons for .name properties
        query = re.sub(
            r"(\w+\.name\s*CONTAINS)\s*'([^']*)'",
            lambda m: f"lower({m.group(1)}) CONTAINS '{m.group(2).lower()}'",
            query,
            flags=re.IGNORECASE
        )
        return query

    @lru_cache(maxsize=128)
    def get_cypher_query(self, question: str, input_schema: str) -> Query:
        # Step 1: Dynamically select few-shot exemplars
        retrieved_examples = self._get_retrieved_examples(question)

        # Step 2: Prune the schema
        prune_result = self.prune(question=question, input_schema=input_schema)
        schema_as_str = str(prune_result.pruned_schema.model_dump())

        # Step 3: Generate the Cypher query with dynamic examples
        with dspy.context(lm=dspy.settings.lm, examples=retrieved_examples):
            text2cypher_result = self.text2cypher(question=question, input_schema=schema_as_str)

        return text2cypher_result.query

    def run_query(
            self,
            db_manager: KuzuDatabaseManager,
            question: str,
            input_schema: str,
    ) -> tuple[str, list[Any] | None]:
        """
        Run a query synchronously on the database, including validation and repair.
        """
        with timeit("graph_rag_get_cypher_query"):
            initial_query_result = self.get_cypher_query(question=question, input_schema=input_schema)

            # Step 4 & 5: Validate, repair, and post-process the query
            final_query = self._validate_and_repair_query(db_manager, initial_query_result.query)

        with timeit("graph_rag_execute_query"):
            try:
                result = db_manager.conn.execute(final_query)
                results = [item for row in result for item in row]
            except RuntimeError as e:
                print(f"Error running query: {e}")
                results = None
        return final_query, results

    def forward(self, db_manager: KuzuDatabaseManager, question: str, input_schema: str):
        final_query, final_context = self.run_query(db_manager, question, input_schema)

        with timeit("graph_rag_generate_answer"):
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
    API_BASE_URL = "https://openrouter.ai/api/v1"
    MODEL = "openrouter/google/gemini-2.5-flash"

    # Using OpenRouter. Switch to another LLM provider as needed
    lm = dspy.LM(
        model=MODEL,
        api_base=API_BASE_URL,
        api_key=OPENROUTER_API_KEY,
        max_retries=5,
        delay=2,
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
    dump_stats("graph_rag_stats.jsonl", _TRACKER.get_all_stats())