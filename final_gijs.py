#!/usr/bin/python3
import sys
import requests
import spacy

# get all possible property id's
def get_property(property):
    url = "https://www.wikidata.org/w/api.php"
    params = {"action":"wbsearchentities","language":"en","format":"json","type":"property"}
    params["search"] = property
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36"}
    json = requests.get(url, params, headers=headers).json()
    proplist = []
    for result in json["search"]:
        proplist.append(result["id"])
    return proplist


# get all possible entity id's
def get_entity(entity):
    url = "https://www.wikidata.org/w/api.php"
    params = {"action":"wbsearchentities","language":"en","format":"json"}
    params["search"] = entity
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36"}
    json = requests.get(url, params, headers=headers).json()
    entlist = []
    for result in json["search"]:
        entlist.append(result["id"])
    return entlist


def create_and_fire_query(line):
    nlp = spacy.load('en_core_web_sm')
    result = nlp(line)
    ll = []
    root = []
    for token in result:
        if token.pos_ != "DET":  # remove determiners
            ll.append(token.text)
        if token.dep_ == "ROOT":
            root.append(token.lemma_)
    result = nlp(' '.join(ll))
    nounlist = []
    for token in result.noun_chunks:
        nounlist.append(token.text)
    entity = nounlist[-1]  # last noun chunk is entity
    if len(nounlist) > 2:  # if list of noun chunks is longer than 3 the second item is property
        property = nounlist[-2]
    else:  # else the lemma of the root of the sentence is the property
        property = root[0]
    propertylist = get_property(property)
    entitylist = get_entity(entity)

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36"}
    url = 'https://query.wikidata.org/sparql'

    # for every possible entity and property do the query, only include queries that return answer
    resultlist = []
    for ent in entitylist:
        for prop in propertylist:
            query = "SELECT ?xLabel WHERE {wd:" + ent + " wdt:" + prop + " ?x SERVICE wikibase:label {bd:serviceParam wikibase:language 'en' .}}"
            try:
                data = requests.get(url, headers=headers, params={'query': query, 'format': 'json'}).json()
                multilist = []
                for item in data['results']['bindings']:
                    for var in item:
                        multilist.append(item[var]['value'])
                resultlist.append(multilist)
            except:
                pass
    resultlist = [x for x in resultlist if x != []]
    return resultlist


def print_example_queries():
    print("Example queries:")
    print("How many people attended the moon?")
    print("Which languages did Albert Einstein speak?")
    print("What is the atomic number of thorium?")
    print("What is the birth date of Marie Curie?")
    print("What is the chemical formula of trenbolone?")
    print("What are the symptoms of the flu?")
    print("What is the speed of light?")
    print("Who invented the telescope?")
    print("Where is the birthplace of Alexander Graham Bell? ")
    print("What is the official website of National Geographic? ")


def main(argv):
    print_example_queries()
    for line in sys.stdin:
        try:
            answer = create_and_fire_query(line)
            for result in answer[0]:
                print(result)  # print first result (most obvious one)
        except:
            print("Could not find answer")


if __name__ == "__main__":
    main(sys.argv)
