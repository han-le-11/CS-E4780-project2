# Few-shot exemplars for Text2Cypher
exemplars = [
    {
        "question": "Which scholars affiliated with the University of Cambridge won prizes in Physics?",
        "query": "MATCH (s:Scholar)-[:AFFILIATED_WITH]->(i:Institution) WHERE lower(i.name) CONTAINS 'university of cambridge' MATCH (s)-[:WON]->(p:Prize) WHERE lower(p.category) CONTAINS 'physics' RETURN s.knownName"
    },
    {
        "question": "How many Nobel laureates were born in the USA?",
        "query": "MATCH (s:Scholar) WHERE lower(s.birth_country) CONTAINS 'usa' RETURN count(s)"
    },
    {
        "question": "List the mentors of Marie Curie.",
        "query": "MATCH (m:Scholar)-[:MENTORED]->(s:Scholar) WHERE lower(s.knownName) CONTAINS 'marie curie' RETURN m.knownName"
    },
    {
        "question": "Which Chemistry laureates were female?",
        "query": "MATCH (s:Scholar)-[:WON]->(p:Prize) WHERE lower(p.category) CONTAINS 'chemistry' AND lower(s.gender) = 'female' RETURN s.knownName"
    },
    {
        "question": "Which laureates were mentored by other laureates outside of U.S. institutions?",
        "query": "MATCH (mentor:Scholar)-[:MENTORED]->(mentee:Scholar), (mentor)-[:AFFILIATED_WITH]->(i:Institution) WHERE i.country <> 'USA' RETURN mentee.knownName"
    },
    # --- New Exemplars ---
    {
        "question": "List the Nobel laureates in Literature born before 1900.",
        "query": "MATCH (s:Scholar)-[:WON]->(p:Prize) WHERE lower(p.category) = 'literature' AND s.birth_date < '1900-01-01' RETURN s.knownName"
    },
    {
        "question": "Who is the most recent winner in the Peace category?",
        "query": "MATCH (s:Scholar)-[r:WON]->(p:Prize) WHERE lower(p.category) = 'peace' RETURN s.knownName ORDER BY r.year DESC LIMIT 1"
    },
    {
        "question": "How many prizes were awarded in the year 2000?",
        "query": "MATCH ()-[r:WON]->() WHERE r.year = 2000 RETURN count(r)"
    },
    {
        "question": "Find laureates who won a prize in either 'Peace' or 'Economics'.",
        "query": "MATCH (s:Scholar)-[:WON]->(p:Prize) WHERE lower(p.category) = 'peace' OR lower(p.category) = 'economics' RETURN DISTINCT s.knownName"
    },
    {
        "question": "What is the name of the institution where Albert Einstein was affiliated?",
        "query": "MATCH (s:Scholar)-[:AFFILIATED_WITH]->(i:Institution) WHERE lower(s.knownName) CONTAINS 'albert einstein' RETURN i.name"
    },
    {
        "question": "List all prize categories.",
        "query": "MATCH (p:Prize) RETURN DISTINCT p.category"
    },
    {
        "question": "Find scholars who were born in Poland and won a prize after 1980.",
        "query": "MATCH (s:Scholar)-[r:WON]->(p:Prize) WHERE lower(s.birth_country) = 'poland' AND r.year > 1980 RETURN s.knownName"
    },
    {
        "question": "Which institutions are located in Germany?",
        "query": "MATCH (i:Institution) WHERE lower(i.country) = 'germany' RETURN i.name"
    }
]