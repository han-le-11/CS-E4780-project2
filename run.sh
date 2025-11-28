export OPENROUTER_API_KEY="your_openrouter_api_key_here"
uv run main.py  --questions_file queries.txt --tag BigGraphRAG --max_num 20
uv run main.py  --questions_file queries_cache_test.txt --tag BigGraphRAGCache --max_num 20

# uv run main.py  --questions_file queries.txt --tag BigGraphRAG --max_num 10
# uv run main.py  --questions_file queries.txt --tag BigGraphRAG --max_num 30
# uv run main.py  --questions_file queries.txt --tag BigGraphRAG --max_num 40
# uv run main.py  --questions_file queries.txt --tag BigGraphRAG --max_num 50
