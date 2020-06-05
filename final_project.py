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

def get_answer(property_var, entity_list):
    property_id = get_property_id(property_var)
    entity_id = get_entity_id(entity_list)
    print(property_id, entity_id)
    if property_id != False or entity_id != False:
        query = '''SELECT ?resultLabel WHERE { wd:'''+entity_id+''' wdt:'''+property_id+''' ?result . SERVICE wikibase:label { bd:serviceParam wikibase:language "en" . } }'''
        data = requests.get(URL,params={'query': query, 'format': 'json'}, headers=HEADERS).json()
        if data['results']['bindings']:
            answer_list = []
            for result in data['results']['bindings']:
                answer = result['resultLabel']['value']
                answer_list.append(answer)
            return answer_list
        else:
            return False
    else:
        return False
    

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
    elif result[0].dep_ == "ROOT"  and result[-1].pos_ == "NOUN":
        entity_list = get_full_subject(result, nsubj="nsubj")
        property_var = relation[result[0].text]
        q_answer = get_full_subject(result, nsubj="attr")
        if q_answer.strip() == '':
            q_answer = get_full_subject(result, nsubj="dobj")
            entity_list = entity_list.replace(q_answer, '')
    elif result[0].dep_ == "ROOT"  and result[-1].pos_ == "ADJ":
        entity_list = get_full_subject(result, nsubj="compound")
        property_var = relation[result[0].text]
        q_answer = get_full_subject(result, nsubj="acomp")
    else:
        property_var = False
        entitity_var = False

    answer_list = get_answer(property_var, entity_list)
    answer = 'No'
    for item in answer_list:
        if q_answer in item.lower():
            answer = 'Yes'
    return answer

def count_questions(question):
    question = question.lower().rstrip()
    nlp = spacy.load('en_core_web_sm')
    if question[-1] == '?':
        question = question[:-1]
    result = nlp(question)
    for item in result:
        print(item, item.lemma_, item.pos_, item.dep_)
    if result[0].dep_ == "advmod" and result[1].dep_ == "amod" and result[-1].pos_ == 'VERB' and result[2].dep_ == 'dobj':
        property_var = get_full_subject(result, nsubj="dobj", dep="amod")
        property_var = property_var.replace('how', '')
        entity_var = get_full_subject(result, dep="amod")
        print(entity_var, property_var)
    elif result[0].dep_ == "advmod" and result[1].dep_ == "amod" and result[-1].pos_ == 'VERB' and result[2].dep_ != 'dobj':
        entity_var = get_full_subject(result, dep="amod")
        property_var = result[1].head.text
        entity_var = entity_var.replace(property_var, '')
        entity_var = entity_var.replace('how', '')
        print(entity_var, property_var)
    else:
        property_var = False
        entity_var = False
    
    
    answer_list = get_answer(property_var, entity_var)
    if answer_list != False:
        return len(answer_list)
    else:
        return 'No answer'

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
    propertylist = get_property_id(property)
    entitylist = get_entity_id(entity)

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
    

def order_questions(question):
    pass


def main(argv):
        print("Example of questions you can ask me:\n",
        "How many awards has Albert Einstein received? \n"
        "How many languages did Nikola Tesla speak?\n"
        "Is HTML a markup language?\n"
        "In what year was Google founded?\n"
        "In what city was Joe Rogan born? \n"
        "When did Albert Einstein die?\n"
        "Who is the discoverer of penicilin?\n"
        "Who invented penicillin?"
    )

        print("Ask me a question:")
        for line in sys.stdin:
            line = line.lower().rstrip()
            error = False
            # Lennart vertel ons ff wanneer we welke functie kunnen runnen
            # Alleen voor Yes/No questions
            # Breid main vooral ook uit voor de andere vraagsoorten
            if line.split(' ') [0] == 'how':
                answer = count_questions(line)
            else:
                answer = binary_questions(line)
            print(answer)
            try:
                answer = create_and_fire_query(line)
                for result in answer[0]:
                    print(result)  # print first result (most obvious one)
            except:
                print("Could not find answer")
            
            print("New quesstion:\n")
            
            

if __name__ == "__main__":
    main(sys.argv)