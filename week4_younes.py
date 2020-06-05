#!/usr/bin/env python3
import requests
import sys
import re
import spacy
from nltk.corpus import wordnet as wn


headers = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36'
}
url = 'https://query.wikidata.org/sparql'

def nounify(verb_word):
    print(verb_word)
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

def get_property_entity(question):
    question = question.lower().rstrip()
    nlp = spacy.load('en_core_web_sm')
    if question[-1] == '?':
        question = question[:-1]
    result = nlp(question)
    for item in result:
        print(item, item.lemma_, item.pos_, item.dep_)

    for ent in result.ents:
        print(ent.text, ent.start_char, ent.end_char, ent.label_)

    related_to_dict = {'born':'birth', 'where':'place of ', 'die':'death', 'when':'date of ', 'how':'cause of ', 'in what city': 'place of '}
    if result[1].dep_ != "ROOT" and (result[0].dep_ == "advmod" and result[1].dep_ != "auxpass"):
        property_var = related_to_dict[result[0].text] + related_to_dict[result[-1].text]
        entity_list = get_full_subject(result)
        return property_var, entity_list
    elif (result[0].dep_ == "nsubj" and result[1].dep_ == "ROOT"):
        r = nounify(result[1].lemma_)
        property_var = list(r)[0].name().split('.')[0]
        entity_list = get_full_subject(result, nsubj="dobj")
        return property_var, entity_list
    elif (result[1].dep_ == "auxpass") and (result[0].dep_ == "advmod"):
        property_var = related_to_dict[result[0].text] + related_to_dict[result[-1].text]
        entity_list = [(x.text) for x in result.ents][0]
        return property_var, entity_list
    elif result[0].dep_ == "prep" and result[1].dep_ == "det" and result[-1].dep_ == "ROOT":
        property_var = result[-1].text
        entity_list = get_full_subject(result, nsubj="dep")
        return property_var, entity_list
    elif result[0].dep_ == "prep" and result[1].dep_ == "det" and result[-1].dep_ != "ROOT":
        property_var = related_to_dict[result[0].text + ' ' +result[1].text + ' ' + result[2].text] + related_to_dict[result[-1].text]
        entity_list =  [(x.text) for x in result.ents][0]
        return property_var, entity_list
    elif result[0].dep_ == "advmod" and result[1].dep_ == "ROOT":
        property_var = related_to_dict[result[0].text] + related_to_dict[result[-1].text]
        entity_list =  get_full_subject(result, dep="acl")
        return property_var, entity_list
    else:
        property_tokens = []
        entity_tokens = []
        if result[0].dep_ == "nsubj":
            for item in result[1:]:
                if item.dep_ == "nsubj":
                    subject = []
                    for d in item.subtree:
                        if d.dep_ != 'det':
                            subject.append(d)
                    for i in range(len(subject)):
                        if subject[i].dep_ == 'case':
                            entity_tokens = subject[:i]
                            property_tokens = subject[i+1:]
                    property_list = []
                    entity_list = []
                    for token in property_tokens:
                        property_list.append(token.text)
                    for token in entity_tokens:
                        entity_list.append(token.text)
                    return " ".join(property_list), " ".join(entity_list)
        else:
            for item in result[1:]:
                if item.dep_ == "nsubj":
                    subject = []
                    for d in item.subtree:
                        if d.dep_ != 'det':
                            subject.append(d)
                    for i in range(len(subject)):
                        if subject[i].dep_ == 'prep':
                            property_tokens = subject[:i]
                            entity_tokens = subject[i+1:]
                    property_list = []
                    entity_list = []
                    for token in property_tokens:
                        property_list.append(token.text)
                    for token in entity_tokens:
                        entity_list.append(token.text)
                    return " ".join(property_list), " ".join(entity_list)

def binary_questions(question):
    question = question.lower().rstrip()
    nlp = spacy.load('en_core_web_sm')
    if question[-1] == '?':
        question = question[:-1]
    result = nlp(question)
    for item in result:
        print(item, item.lemma_, item.pos_, item.dep_)

    if result[0].dep_ == "aux" and result[1].dep_ == "nsubj":
        for item in result:
            if item.dep_ == "ROOT":
                r = nounify(item.lemma_)
                print(r)
                total_list = [(x.name().split('.')[0], x.name().split('.')[-1]) for x in r]
                total_list.sort(key=lambda x: x[1])
                property_var = total_list[0][0]
                print(property_var)
        q_answer = get_full_subject(result)
        entity_list = get_full_subject(result, nsubj="dobj")
        print(property_var, entity_list, q_answer)


    property_id = get_property_id(property_var)
    entity_id = get_entity_id(entity_list)
    if property_id != None or entity_id != None:
        query = '''SELECT ?resultLabel WHERE { wd:'''+entity_id+''' wdt:'''+property_id+''' ?result . SERVICE wikibase:label { bd:serviceParam wikibase:language "en" . } }'''
        data = requests.get(url,params={'query': query, 'format': 'json'}, headers=headers).json()
        if data['results']['bindings']:
            answer_list = []
            for result in data['results']['bindings']:
                answer = result['resultLabel']['value']
                answer_list.append(answer)
        else:
            pass
    answer = 'no'
    for item in answer_list:
        if q_answer in item.lower:
            answer = 'yes'
    return answer_list

def get_property_id(property_var):
    url = 'https://www.wikidata.org/w/api.php'
    params = {'action':'wbsearchentities','language':'en','format':'json','type':'property'}
    params['search'] = property_var
    json = requests.get(url,params, headers=headers).json()
    if len(json['search']) == 0:
        return False
    else:
        result_id = json['search'][0]['id']
        return result_id

def get_entity_id(entity_var):
    url = 'https://www.wikidata.org/w/api.php'
    params = {'action':'wbsearchentities','language':'en','format':'json'}
    params['search'] = entity_var
    json = requests.get(url,params, headers=headers).json()
    if len(json['search']) == 0:
        return False
    else:
        result_id = json['search'][0]['id']
        return result_id

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
        url = 'https://query.wikidata.org/sparql'
        for line in sys.stdin:
            error = False
            #try:
            property_var, entity_var = binary_questions(line)
            print(property_var, entity_var, "2")
            #except Exception as e:
            print("\nCould not find answer! Try again:")
            
            error = True
            if error == False:
                try:
                    property_id = get_property_id(property_var)
                    entity_id = get_entity_id(entity_var)
                    if property_id == False or entity_id == False:
                        print("Could not find answer! Ty again:")
                    else:
                        query = '''SELECT ?resultLabel WHERE { wd:'''+entity_id+''' wdt:'''+property_id+''' ?result . SERVICE wikibase:label { bd:serviceParam wikibase:language "en" . } }'''
                        data = requests.get(url,params={'query': query, 'format': 'json'}).json()
                        if data['results']['bindings']:
                            for result in data['results']['bindings']:
                                answer = result['resultLabel']['value']
                                print(answer)
                            print("\nAsk me another question:")
                        else:
                            print("\nCould not find answer! Try again:")
                except IndexError:
                    print("\nCould not find answer! Try again:")
            else:
                pass

if __name__ == "__main__":
    main(sys.argv)