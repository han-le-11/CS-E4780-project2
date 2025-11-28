import time
from typing import Any

from tqdm import tqdm

from workflow import _TRACKER
from workflow import GraphRAG
from workflow import KuzuDatabaseManager
from workflow import dspy
from workflow import dump_stats
from workflow import load_dotenv


def run_graph_rag(questions: list[str], db_manager: KuzuDatabaseManager) -> list[Any]:
    schema = str(db_manager.get_schema_dict)
    rag = GraphRAG()
    # Run pipeline
    results = []
    for question in tqdm(questions):
        response = rag(db_manager=db_manager, question=question, input_schema=schema)
        results.append(response)
    return results


def create_LM():
    load_dotenv()

    OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
    API_BASE_URL = "https://openrouter.ai/api/v1"
    MODEL = "openrouter/google/gemini-2.5-flash"

    # Using OpenRouter. Switch to another LLM provider as needed
    # we recommend gemini-2.0-flash for the cost-efficiency
    lm = dspy.LM(
        model=MODEL,
        api_base=API_BASE_URL,
        api_key=OPENROUTER_API_KEY,
    )
    dspy.configure(lm=lm)
    return lm


def main(questions=None, max_num: int = 10):
    create_LM()

    questions = questions[:max_num]

    db_manager = KuzuDatabaseManager("nobel.kuzu")

    start = time.time()
    results = run_graph_rag(questions, db_manager)
    end = time.time()
    print(f"Total time taken for {len(questions)} questions: {end - start} seconds")

    for res in results:
        print(res)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--questions_file",
        type=str,
        default="queries.txt",
        help="Path to the file containing questions",
    )
    parser.add_argument(
        "--tag",
        type=str,
        default="graph_rag_experiment",
        help="Tag for tracking the experiment",
    )
    parser.add_argument(
        "--max_num",
        type=int,
        default=10,
        help="Maximum number of questions to process",
    )
    args = parser.parse_args()
    with open(args.questions_file, "r") as f:
        questions = [line.strip() for line in f.readlines() if line.strip()]

    _TRACKER.set_tag(args.tag)
    _TRACKER.set_num_samples(args.max_num)

    main(questions=questions, max_num=args.max_num)

    output = f"graph_rag_results_{args.tag}_{args.max_num}.jsonl"

    dump_stats(output, _TRACKER.get_all_stats())
