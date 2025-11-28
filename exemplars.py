# Few-shot exemplars for Text2Cypher
exemplars = [
    {
        "question": "Which scholars affiliated with the University of Cambridge won prizes in Physics?",
        "query": "MATCH (s:Scholar)-[:AFFILIATED_WITH]->(i:Institution) WHERE lower(i.name) CONTAINS 'university of cambridge' MATCH (s)-[:WON]->(p:Prize) WHERE lower(p.category) CONTAINS 'physics' RETURN s.knownName"
    },
    {
        "question": "Which Chemistry laureates were female?",
        "query": "MATCH (s:Scholar)-[:WON]->(p:Prize) WHERE lower(p.category) CONTAINS 'chemistry' AND lower(s.gender) = 'female' RETURN s.knownName"
    },
    {
        "question": "List the Nobel laureates in Medicine born before 1900.",
        "query": "MATCH (s:Scholar)-[:WON]->(p:Prize) WHERE lower(p.category) = 'medicine' AND s.birthDate < '1900-01-01' RETURN s.knownName"
    },
    {
        "question": "Who is the most recent winner in the Physics category?",
        "query": "MATCH (s:Scholar)-[:WON]->(p:Prize) WHERE lower(p.category) = 'physics' RETURN s.knownName ORDER BY p.awardYear DESC LIMIT 1"
    },
    {
        "question": "How many prizes were awarded in the year 2000?",
        "query": "MATCH ()-[:WON]->(p:Prize) WHERE p.awardYear = 2000 RETURN count(p)"
    },
    {
        "question": "Find laureates who won a prize in 'Economics'.",
        "query": "MATCH (s:Scholar)-[:WON]->(p:Prize) WHERE lower(p.category) = 'economics' RETURN DISTINCT s.knownName"
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
        "question": "Find scholars who won a prize after 1980.",
        "query": "MATCH (s:Scholar)-[:WON]->(p:Prize) WHERE p.awardYear > 1980 RETURN s.knownName"
    }
]