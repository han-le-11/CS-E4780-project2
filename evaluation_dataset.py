# This is the dataset for evaluating accuracy in task 1.
evaluation_set = [
    {
        "question": "How many female scholars are there?",
        "gold_query": "MATCH (s:Scholar) WHERE lower(s.gender) = 'female' RETURN count(s)",
        "gold_result": [25]  # result obtained by get_baseline_results.py
    },
    {
        "question": "Which male scholars affiliated with the University of oxford won prizes in chemistry?",
        "gold_query": "MATCH (s:Scholar)-[:AFFILIATED_WITH]->(i:Institution), (s)-[:WON]->(p:Prize) WHERE lower(s.gender) = 'male' AND lower(i.name) CONTAINS 'university of oxford' AND lower(p.category) = 'chemistry' RETURN s.knownName",
        "gold_result": ['Sir Robert Robinson', 'Frederick Soddy', 'Sir Cyril Hinshelwood']
    },
    {
        "question": "Which scholars affiliated with the University of Cambridge won prizes in Physics?",
        "gold_query": "MATCH (s:Scholar)-[:AFFILIATED_WITH]->(i:Institution) WHERE lower(i.name) CONTAINS 'university of cambridge' MATCH (s)-[:WON]->(p:Prize) WHERE lower(p.category) CONTAINS 'physics' RETURN s.fullName",
        "gold_result": ['Antony Hewish', 'Brian David Josephson', 'Charles Thomson Rees Wilson', 'Didier Queloz', 'Joseph John Thomson', 'Sir Martin Ryle', 'Paul Adrien Maurice Dirac', 'Sir Nevill Francis Mott']
    },
    {
        "question": "Find scholars who won a prize for 'Physics' and 'Chemistry'",
        "gold_query": "MATCH (s:Scholar)-[:WON]->(p1:Prize), (s)-[:WON]->(p2:Prize) WHERE lower(p1.category) = 'physics' AND lower(p2.category) = 'chemistry' RETURN DISTINCT s.knownName",
        "gold_result": ["Marie Curie"]
    },
    {
        "question": "what is the birth date of albert einstein?", # intentional lowercase to test post-processor
        "gold_query": "MATCH (s:Scholar) WHERE lower(s.knownName) CONTAINS 'albert einstein' RETURN s.birthDate",
        "gold_result": ["1879-03-14"]
    },
    {
        "question": "Which scholars were affiliated with an institution in Paris?",
        "gold_query": "MATCH (s:Scholar)-[:AFFILIATED_WITH]->(i:Institution)-[:IS_LOCATED_IN]->(c:City) WHERE lower(c.name) = 'paris' RETURN s.knownName",
        "gold_result": ['Pierre-Gilles de Gennes', 'Alfred Kastler', 'Charles Nicolle', 'François Jacob', 'Ilya Mechnikov', 'Louis de Broglie', 'Serge Haroche', 'Serge Haroche', 'Alphonse Laveran', 'Georges Charpak', 'Gérard Mourou', 'Jean-Marie Lehn', 'Alain Aspect', 'Alain Aspect', 'Gabriel Lippmann', 'Irène Joliot-Curie', 'Jacques Monod', 'Maurice Allais', 'Charles Richet', 'Claude Cohen-Tannoudji', 'Claude Cohen-Tannoudji', 'Luc Montagnier', 'Pierre Curie', 'André Lwoff', 'Françoise Barré-Sinoussi', 'Henri Becquerel', 'Frédéric Joliot', 'Henri Moissan', 'Jean Baptiste Perrin', 'Jean Dausset', 'Marie Curie']
    },
]