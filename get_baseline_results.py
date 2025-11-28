import kuzu

db = kuzu.Database("nobel.kuzu")
conn = kuzu.Connection(db)

# Paste the query to run here
query_to_run ="MATCH (s:Scholar)-[:AFFILIATED_WITH]->(i:Institution), (s)-[:WON]->(p:Prize) WHERE lower(s.gender) = 'male' AND lower(i.name) CONTAINS 'university of oxford' AND lower(p.category) = 'chemistry' RETURN s.knownName"

print(f"Running query: {query_to_run}\n")

try:
    result_set = conn.execute(query_to_run)
    results = [row[0] for row in result_set.get_all()]

    # Print the final result
    print("--- Result to be used as baseline: ---")
    print(results)

except Exception as e:
    print(f"An error occurred: {e}")
