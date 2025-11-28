import dspy

# Each example is a question and its corresponding Cypher query.
# These will be used to dynamically select examples based on similarity to the user's question.
# Add more examples to improve the accuracy of the Text2Cypher conversion.
# Good examples cover different types of questions and Cypher clauses.
exemplars = [
    dspy.Example(
        question="Which scholars won prizes in Physics and were affiliated with the University of Cambridge?",
        query="""MATCH (s:Scholar)-[r:AFFILIATED_WITH]->(i:Institution)
WHERE s.prizes CONTAINS 'physics' AND i.name CONTAINS 'university of cambridge'
RETURN s.knownName, s.prizes""",
    ),

    dspy.Example(
        question="Who were the mentors of Marie Curie?",
        query="""MATCH (mentor:Scholar)-[:MENTORED]->(mentee:Scholar)
WHERE mentee.knownName CONTAINS 'Marie Curie'
RETURN mentor.knownName""",
    ),

    dspy.Example(
        question="How many Nobel laureates were born in the United States?",
        query="""MATCH (l:Laureate)
WHERE l.birth_country CONTAINS 'USA'
RETURN count(l)""",
    ),

    dspy.Example(
        question="List all Nobel prizes won by scholars from the University of Berlin.",
        query="""MATCH (s:Scholar)-[:AFFILIATED_WITH]->(i:Institution)
WHERE i.name CONTAINS 'University of Berlin' AND s.prizes IS NOT NULL
RETURN s.knownName, s.prizes""",
    ),

    dspy.Example(
        question="Which female scholars won a Nobel prize in Chemistry?",
        query="""MATCH (s:Scholar)
WHERE s.gender = 'female' AND s.prizes CONTAINS 'chemistry'
RETURN s.knownName""",
    ),

    dspy.Example(
        question="What was the motivation for Albert Einstein's Nobel prize?",
        query="""MATCH (l:Laureate)
WHERE l.knownName CONTAINS 'Albert Einstein'
RETURN l.motivation""",
    ),

    dspy.Example(
        question="Find laureates who were mentored by other laureates outside of U.S. institutions.",
        query="""MATCH (mentor:Laureate)-[:MENTORED]->(mentee:Laureate),
      (mentor)-[:AFFILIATED_WITH]->(i:Institution)
WHERE i.country <> 'USA'
RETURN mentee.knownName, mentor.knownName, i.name""",
    ),

    dspy.Example(
        question="Which laureates died in the same city they were born in?",
        query="""MATCH (l:Laureate)
WHERE l.birth_city = l.death_city
RETURN l.knownName, l.birth_city""",
    ),

    dspy.Example(
        question="Get the names of all institutions in France.",
        query="""MATCH (i:Institution)
WHERE i.country = 'France'
RETURN i.name""",
    ),
    dspy.Example(
        question="Who are the scholars that have no recorded mentor?",
        query="""MATCH (s:Scholar)
WHERE NOT EXISTS ((:Scholar)-[:MENTORED]->(s))
RETURN s.knownName""",
    ),
]