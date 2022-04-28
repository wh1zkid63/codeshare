# Tony_Onabanjo_Test.py
# NB.
# I have no previous experience with SPARQL or RDF so had to learn from scratch
# My implementation assumes only 2 types of questions 1. How old is <subject> and 2. what is the population of <subject>
#
#
from enum import Enum
from unittest import TestCase
from SPARQLWrapper import SPARQLWrapper, JSON


class EntityType(Enum):
    Human = 'wd:Q5'
    City = 'wd:Q515'


class Guru:
    def __init__(self, endpoint: str = 'https://query.wikidata.org/sparql'):
        self.endpoint = endpoint
        self.sparql = SPARQLWrapper(self.endpoint)
        self.sparql.setReturnFormat(JSON)

    property_maps = {
        'age': 'how old is ',
        'population': 'what is the population of ',
    }

    # some cached City URIs to avoid fetch_subject_uri call - cities not listed can also be queried
    popular_cities = {
        'London': 'wd:Q84',
        'Paris': 'wd:Q90',
        'Amsterdam': 'wd:Q727',
        'New York City': 'wd:Q60',
    }

    # some cached Human URIs to avoid fetch_subject_uri call - humans not listed can also be queried
    popular_humans = {
        "Tony Blair": 'wd:Q9545',
        'trump': 'wd:Q22686',
        'Donald Trump': 'wd:Q22686',
        'Richard Branson': 'wd:Q194419',
        'Nelson Mandela': 'wd:Q8023',
    }

    def fetch_subject_uri(self, entity_type, subject):
        """Gets the URI for a subject if it doesn't exist in the popular list. The first item seems to always match
        what we are looking for even for items in the popular list."""
        query = """
        SELECT ?item ?itemLabel WHERE {{
            ?item wdt:P31 {} .
            SERVICE wikibase:mwapi {{
                bd:serviceParam wikibase:endpoint "www.wikidata.org";
                wikibase:api "EntitySearch";
                mwapi:search "{}"; # Search for entity by name
                mwapi:language "en".
              ?item wikibase:apiOutputItem mwapi:item.
          }}
          SERVICE wikibase:label {{
              bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en".
            }}
        }}
        LIMIT 1
        """
        self.sparql.setQuery(query.format(entity_type.value, subject))
        response = self.sparql.queryAndConvert()
        return f"<{response['results']['bindings'][0]['item']['value']}>"

    def extract_subject_n_predicate(self, question: str):
        """Based on question extract subject (s) and predicate (p) portions of triple to facilitate construction of
        query that will return object (o) portion (where s (entity identifier) and o (attribute value) are resources
        and p (attribute name) signifies the nature of their relationship)."""
        subject, predicate = None, None

        for key, prefix in self.property_maps.items():
            if question.startswith(prefix):
                predicate = key
                subject = question[len(prefix):]
                break
        return subject, predicate

    def ask(self, question: str):
        """Respond to the question asked."""
        subject, predicate = self.extract_subject_n_predicate(question)
        query = self.create_wdqs_query(subject, predicate)
        response = self.execute_query(query)

        return response['results']['bindings'][0][predicate]['value']

    def create_wdqs_query(self, subject, predicate):
        """Create a WDQS query representing the subject and predicate to retrieve property value."""
        def create_population_query():
            q_code = self.popular_cities.get(subject) or self.fetch_subject_uri(EntityType.City, subject)
            return f"""
                    SELECT ?item ?itemLabel ?population 
                    WHERE {{
                        ?item wdt:P31 wd:Q515 .
                        ?item wdt:P1082 ?population .
                        ?item wdt:P1448 ? {q_code} .
                        
                        SERVICE wikibase:label {{ 
                          bd:serviceParam wikibase:language "en" 
                        }}
                    }}
                    """

        def create_age_query():
            q_code = self.popular_humans.get(subject) or self.fetch_subject_uri(EntityType.Human, subject)
            return f"""
                SELECT * WHERE {{   
                  {q_code} wdt:P569 ?birth .   
                  BIND(now() as ?today)   
                  BIND(year(?today) - year(?birth) - if(month(?today) < month(?birth) || 
                      (month(?today) = month(?birth) && 
                      day(?today)< day(?birth)), 1, 0) as ?age 
                  )   
                  SERVICE wikibase:label {{ 
                    bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". 
                  }} 
                }}
                """

        return create_population_query() if predicate == 'population' else create_age_query()

    def execute_query(self, query):
        self.sparql.setQuery(query)
        return self.sparql.queryAndConvert()


class TestGuru(TestCase):

    def test_ask(self):
        # note these values may change a little as time moves on
        questions_and_answers = {
            'how old is Tony Blair': '68',
            'how old is trump': '75',
            'how old is Bill Clinton': '75',
            'what is the population of London': '8908081',
            # 'what is the population of Paris': '2175601',
            'what is the population of Amsterdam': '860124',
            'how old is Hillary Clinton': '74',
        }

        guru: Guru = Guru()
        for question, answer in questions_and_answers.items():
            self.assertEqual(answer, guru.ask(question))


if __name__ == "__main__":
    q_and_a = {
        'how old is Tony Blair': '68',
        'how old is trump': '75',
        'how old is Bill Clinton': '75',
        'what is the population of London': '8908081',
        # 'what is the population of Paris': '2175601',
        'what is the population of Amsterdam': '860124',
        'how old is Hillary Clinton': '74',
    }

    g: Guru = Guru()
    for q, a in q_and_a.items():
        print(q, 'Actual:', g.ask(q), 'Expected:', a)