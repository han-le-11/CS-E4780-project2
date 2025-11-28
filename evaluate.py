import dspy
from tqdm import tqdm
from baseline_graph_rag import GraphRAG as BaselineGraphRAG
from workflow import GraphRAG as EnhancedGraphRAG
from workflow import create_LM, KuzuDatabaseManager

# Import the evaluation data
from evaluation_dataset import evaluation_set


def evaluate_system(system_class, dataset, db_manager):
    syntactic_correct = 0
    functional_correct = 0

    # Initialize the system (either baseline or enhanced)
    rag_system = system_class()
    schema_str = str(db_manager.get_schema_dict)

    for item in tqdm(dataset, desc=f"Evaluating {system_class.__name__}"):
        question = item["question"]
        gold_result = item["gold_result"]

        final_query = None

        # 1. Generate the query using the specific system's logic
        try:
            if isinstance(rag_system, BaselineGraphRAG):
                query_obj = rag_system.get_cypher_query(question, schema_str)
                final_query = query_obj.query
            elif isinstance(rag_system, EnhancedGraphRAG):
                # The enhanced system has the validation/repair loop in `run_query`
                query_obj = rag_system.get_cypher_query(question, schema_str)
                final_query = rag_system._validate_and_repair_query(db_manager, query_obj.query)

            if not final_query:
                continue

            # 2. Test Syntactic Accuracy
            # Try to execute the query. If it fails, it's a syntactic error.
            generated_result_set = db_manager.conn.execute(final_query)
            generated_result = [row[0] for row in generated_result_set.get_all()]
            syntactic_correct += 1

            # 3. Test Functional Accuracy
            # Use sets for comparison to ignore order for non-ordered queries.
            if set(generated_result) == set(gold_result):
                functional_correct += 1

        except Exception as e:
            # Any error during generation or execution is a failure for this data point
            # print(f"Failed on question '{question}' with query '{final_query}'. Error: {e}")
            continue

    total = len(dataset)
    syntactic_accuracy = (syntactic_correct / total) * 100 if total > 0 else 0
    functional_accuracy = (functional_correct / total) * 100 if total > 0 else 0

    return {
        "syntactic_accuracy": syntactic_accuracy,
        "functional_accuracy": functional_accuracy,
    }


if __name__ == "__main__":
    create_LM()  # Configure dspy with LLM
    db = KuzuDatabaseManager("nobel.kuzu")

    print("--- Evaluating Baseline System ---")
    baseline_metrics = evaluate_system(BaselineGraphRAG, evaluation_set, db)
    print(baseline_metrics)

    print("\n--- Evaluating Enhanced System ---")
    enhanced_metrics = evaluate_system(EnhancedGraphRAG, evaluation_set, db)
    print(enhanced_metrics)

    # --- Compare and Report Results ---
    print("\n" + "=" * 30)
    print("      ACCURACY IMPROVEMENT      ")
    print("=" * 30)
    print(
        f"Syntactic Accuracy:  {baseline_metrics['syntactic_accuracy']:.2f}%  ->  {enhanced_metrics['syntactic_accuracy']:.2f}%")
    print(
        f"Functional Accuracy: {baseline_metrics['functional_accuracy']:.2f}%  ->  {enhanced_metrics['functional_accuracy']:.2f}%")
    print("=" * 30)