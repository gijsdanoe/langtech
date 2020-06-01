#!/usr/bin/env python3
import requests
import sys
import re
import spacy
from nltk.corpus import wordnet as wn

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36'
}
URL = 'https://query.wikidata.org/sparql'


def nounify(verb_word):
    set_of_related_nouns = set()
    for lemma in wn.lemmas(wn.morphy(verb_word, wn.VERB), pos="v"):
        for related_form in lemma.derivationally_related_forms():
            for synset in wn.synsets(related_form.name(), pos=wn.NOUN):
                if wn.synset('person.n.01') in synset.closure(lambda s:s.hypernyms()):
                    set_of_related_nouns.add(synset)
    return set_of_related_nouns

def get_full_subject(result, dep="det", nsubj="nsubj"):
    entity_list = []
    for item in result:
        if item.dep_ == nsubj:
            subject = []
            for d in item.subtree:
                if d.dep_ != dep:
                    subject.append(d)
            for token in subject:
                entity_list.append(token.text)
    return " ".join(entity_list)

def get_property_id(property_var):
    url = 'https://www.wikidata.org/w/api.php'
    params = {'action':'wbsearchentities','language':'en','format':'json','type':'property'}
    params['search'] = property_var
    json = requests.get(url,params, headers=HEADERS).json()
    if len(json['search']) == 0:
        return False
    else:
        result_id = json['search'][0]['id']
        return result_id

def get_entity_id(entity_var):
    url = 'https://www.wikidata.org/w/api.php'
    params = {'action':'wbsearchentities','language':'en','format':'json'}
    params['search'] = entity_var
    json = requests.get(url,params, headers=HEADERS).json()
    if len(json['search']) == 0:
        return False
    else:
        result_id = json['search'][0]['id']
        return result_id

def binary_questions(question):
    question = question.lower().rstrip()
    nlp = spacy.load('en_core_web_sm')
    if question[-1] == '?':
        question = question[:-1]
    result = nlp(question)
    # Debug statement om te kijken wat de lemma, pos en dep is van elk woord in de zin
    for item in result:
        print(item, item.lemma_, item.pos_, item.dep_)
    relation = {'is': 'subclass of'}
    if result[0].dep_ == "aux" and result[1].dep_ == "nsubj":
        for item in result:
            if item.dep_ == "ROOT":
                # Nouns vinden die bij lemma passen
                r = nounify(item.lemma_)
                total_list = [(x.name().split('.')[0], x.name().split('.')[-1]) for x in r]
                total_list.sort(key=lambda x: x[1])
                property_var = total_list[0][0]
        q_answer = get_full_subject(result)
        entity_list = get_full_subject(result, nsubj="dobj")
        print(property_var, entity_list, q_answer)
    if result[0].dep_ == "ROOT"  and result[-1].pos_ == "NOUN":
        entity_list = get_full_subject(result)
        property_var = relation[result[0].text]
        q_answer = get_full_subject(result, nsubj="attr")
        print(entity_list, property_var)
    if result[0].dep_ == "ROOT"  and result[-1].pos_ == "ADJ":
        entity_list = get_full_subject(result, nsubj="compound")
        property_var = relation[result[0].text]
        q_answer = get_full_subject(result, nsubj="acomp")
        print(entity_list, property_var)

    property_id = get_property_id(property_var)
    entity_id = get_entity_id(entity_list)
    if property_id != None or entity_id != None:
        query = '''SELECT ?resultLabel WHERE { wd:'''+entity_id+''' wdt:'''+property_id+''' ?result . SERVICE wikibase:label { bd:serviceParam wikibase:language "en" . } }'''
        data = requests.get(URL,params={'query': query, 'format': 'json'}, headers=HEADERS).json()
        if data['results']['bindings']:
            answer_list = []
            for result in data['results']['bindings']:
                answer = result['resultLabel']['value']
                answer_list.append(answer)
        else:
            pass
    answer = 'No'
    for item in answer_list:
        if q_answer in item.lower():
            answer = 'Yes'
    return answer

def main(argv):
        print("Example of questions you can ask me:\n",
        "What are symptoms of COVID-19?\n"
        "Where was Albert Einstein born?\n"
        "What are the components of air?\n"
        "In what year was Google founded?\n"
        "In what city was Joe Rogan born? \n"
        "When did Albert Einstein die?\n"
        "Who is the discoverer of penicilin?\n"
        "Who invented penicillin?"
    )

        print("Ask me a question:")
        for line in sys.stdin:
            error = False
            # Alleen voor Yes/No questions
            # Breid main vooral ook uit voor de andere vraagsoorten
            answer = binary_questions(line)
            print(answer)
            print("New quesstion:\n")
            
            

if __name__ == "__main__":
    main(sys.argv)