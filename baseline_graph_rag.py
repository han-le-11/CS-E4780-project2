# -*- encoding: utf-8 -*-
# File: workflow.py
# Description: This file represents the baseline system BEFORE enhancements.

import dspy
from typing import Any
from workflow import KuzuDatabaseManager, PruneSchema, Text2Cypher, AnswerQuestion, Query

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