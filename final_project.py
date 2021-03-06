#!/usr/bin/env python3
import requests
import sys
import spacy
from nltk.corpus import wordnet as wn
from difflib import ndiff

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36'
}
URL = 'https://query.wikidata.org/sparql'

# calculate levenshtein distance
def levenshtein_distance(str1, str2):
    counter = {"+": 0, "-": 0}
    distance = 0
    for edit_code, *_ in ndiff(str1, str2):
        if edit_code == " ":
            distance += max(counter.values())
            counter = {"+": 0, "-": 0}
        else:
            counter[edit_code] += 1
    distance += max(counter.values())
    return distance

# make nouns of verbs
def nounify(verb_word):
    set_of_related_nouns = set()
    for lemma in wn.lemmas(wn.morphy(verb_word, wn.VERB), pos="v"):
        for related_form in lemma.derivationally_related_forms():
            for synset in wn.synsets(related_form.name(), pos=wn.NOUN):
                if wn.synset('person.n.01') in synset.closure(lambda s: s.hypernyms()):
                    set_of_related_nouns.add(synset)
    return set_of_related_nouns

# get the full subject of a question
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


# get all possible property id's and sort them by levenshtein distance
def get_property(property):
    url = "https://www.wikidata.org/w/api.php"
    params = {"action": "wbsearchentities", "language": "en", "format": "json", "type": "property"}
    params["search"] = property
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36"}
    json = requests.get(url, params, headers=headers).json()
    proplist = []
    for result in json["search"]:
        proplist.append((result["id"], levenshtein_distance(result["label"], property)))
    proplist = sorted(proplist, key=lambda x: x[1])
    proplist = [i[0] for i in proplist]
    return proplist


# get all possible entity id's and sort them by levenshtein distance
def get_entity(entity):
    url = "https://www.wikidata.org/w/api.php"
    params = {"action": "wbsearchentities", "language": "en", "format": "json"}
    params["search"] = entity
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36"}
    json = requests.get(url, params, headers=headers).json()
    entlist = []
    for result in json["search"]:
        entlist.append((result["id"], levenshtein_distance(result["label"], entity)))
    entlist = sorted(entlist, key=lambda x: x[1])
    entlist = [i[0] for i in entlist]
    return entlist

# try the query for all combinations, get the first answer that is not none
def get_answer(property_var, entity_list):
    propertylist = get_property(property_var)
    entitylist = get_entity(entity_list)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36"}
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
    return resultlist[0]

# yes or no questions
def binary_questions(question, id):
    question = question.lower().rstrip()
    nlp = spacy.load('en_core_web_sm')
    if question[-1] == '?':
        question = question[:-1]
    result = nlp(question)
    # Debug statement om te kijken wat de lemma, pos en dep is van elk woord in de zin
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
    elif result[0].dep_ == "ROOT" and result[-1].pos_ == "NOUN":
        entity_list = get_full_subject(result, nsubj="nsubj")
        property_var = relation[result[0].text]
        q_answer = get_full_subject(result, nsubj="attr")
        if q_answer.strip() == '':
            q_answer = get_full_subject(result, nsubj="dobj")
            entity_list = entity_list.replace(q_answer, '')
    elif result[0].dep_ == "ROOT" and result[-1].pos_ == "ADJ":
        entity_list = get_full_subject(result, nsubj="compound")
        property_var = relation[result[0].text]
        q_answer = get_full_subject(result, nsubj="acomp")
    else:
        property_var = False
        entity_list = False
    try:
        answer_list = get_answer(property_var, entity_list)
        answer = 'no'
        for item in answer_list:
            if q_answer in item.lower():
                answer = 'yes'
        print(id + "\t" + answer)
    except:
        print(id + "\t" + 'No answer')

# count questions (how many)
def count_questions(question, id):
    question = question.lower().rstrip()
    nlp = spacy.load('en_core_web_sm')
    if question[-1] == '?':
        question = question[:-1]
    result = nlp(question)
    if result[0].dep_ == "advmod" and result[1].dep_ == "amod" and result[-1].pos_ == 'VERB' and result[
        2].dep_ == 'dobj':
        property_var = get_full_subject(result, nsubj="dobj", dep="amod")
        property_var = property_var.replace('how', '')
        entity_var = get_full_subject(result, dep="amod")
    elif result[0].dep_ == "advmod" and result[1].dep_ == "amod" and result[-1].pos_ == 'VERB' and result[
        2].dep_ != 'dobj':
        entity_var = get_full_subject(result, dep="amod")
        property_var = result[1].head.text
        entity_var = entity_var.replace(property_var, '')
        entity_var = entity_var.replace('how', '')
    else:
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
        entity_var = nounlist[-1]  # last noun chunk is entity
        if len(nounlist) > 2:  # if list of noun chunks is longer than 3 the second item is property
            property_var = nounlist[-2]
        else:  # else the lemma of the root of the sentence is the property
            property_var = root[0]

    try:
        answer_list = get_answer(property_var, entity_var)
        print(id + "\t", end='')
        if answer_list != False:
            print(len(answer_list))
        else:
            print('No answer')
    except:
        print(id + '\t' + 'No answer')

# description questions (who is X)
def description(line, id):
    nlp = spacy.load('en_core_web_sm')
    result = nlp(line)
    ll = []
    for token in result:
        if token.pos != "DET":  # remove determiners
            ll.append(token.text)
    result = nlp(' '.join(ll))
    nounlist = []
    for token in result.noun_chunks:
        nounlist.append(token.text)
    nounlist.pop(0)

    try:
        entity = nounlist[-1]  # last noun chunk is entity

        url = "https://www.wikidata.org/w/api.php"
        params = {"action": "wbsearchentities", "language": "en", "format": "json"}
        params["search"] = entity.rstrip()
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36"}
        json = requests.get(url, params, headers=headers).json()

        lslist = []
        desclist = []

        for result in json['search']:
            try:
                lslist.append(levenshtein_distance(result['label'], entity))
                desclist.append(result['description'])
            except:
                pass
        print(id, '\t', desclist[lslist.index(min(lslist))])
    except:
        print("No answer")

# all other questions including X of Y and list questions
def get_questions_other(question, id):
    question = question.lower().rstrip()
    nlp = spacy.load('en_core_web_sm')
    if question[-1] == '?':
        question = question[:-1]
    result = nlp(question)
    related_to_dict = {'born': 'birth', 'where': 'place of ', 'die': 'death', 'when': 'date of ', 'how': 'cause of ',
                       'in what city': 'place of ', 'invented': 'invention ', 'discovered': 'invention ',
                       'big': 'diameter', 'heavy': 'mass', 'study': 'study', 'old': 'age', 'weigh': 'mass',
                       'effects of ': 'has effect'}
    if result[1].dep_ != "ROOT" and (
            result[0].dep_ == "advmod" and result[1].dep_ != "auxpass" and result[1].dep_ != "acomp"):
        try:
            property_var = related_to_dict[result[0].text] + related_to_dict[result[-1].text]
        except:
            property_var = get_full_subject(result)
        if property_var.strip() == 'place of study':
            property_var = 'educated at'
        if property_var.strip() == 'cause of mass':
            property_var == 'mass'
        entity_list = get_full_subject(result)
    elif (result[0].dep_ == "advmod" and result[1].dep_ != "auxpass" and result[1].dep_ == "acomp"):
        property_var = related_to_dict[result[1].text]
        entity_list = get_full_subject(result)
    elif (result[0].dep_ == "nsubj" and result[1].dep_ == "ROOT"):
        try:
            r = nounify(result[1].lemma_)
            property_var = list(r)[0].name().split('.')[0]
        except:
            property_var = get_full_subject(result, nsubj="attr")
        entity_list = get_full_subject(result, nsubj="dobj")
        if entity_list.strip() == "":
            entity_list = get_full_subject(result, nsubj="pobj")
    elif (result[1].dep_ == "auxpass") and (result[0].dep_ == "advmod"):
        property_var = result[-1].text
        entity_list = get_full_subject(result, nsubj="dep")
    elif result[0].dep_ == "prep" and result[1].dep_ == "det" and result[-1].dep_ != "ROOT":
        property_var = related_to_dict[result[0].text + ' ' + result[1].text + ' ' + result[2].text] + related_to_dict[
            result[-1].text]
        entity_list = [(x.text) for x in result.ents][0]
    elif result[0].dep_ == "advmod" and result[1].dep_ == "ROOT":
        property_var = related_to_dict[result[0].text] + related_to_dict[result[-1].text]
        try:
            entity_list = [(x.text) for x in result.ents][0]
        except:
            entity_list = get_full_subject(result)
    elif result[0].dep_ == "attr" and result[1].dep_ == "ROOT":
        entity_list = get_full_subject(result, nsubj='pobj')
        try:
            property_var = [(x.text) for x in result.ents][0]
        except:
            property_var = get_full_subject(result)
        if entity_list in property_var:
            property_var = property_var.replace(entity_list, '')

        try:
            property_var = related_to_dict[property_var]
        except:
            property_var = property_var.replace('of', '')

    elif result[0].dep_ == "ROOT" and result[-1].dep_ == "pobj":
        property_var = get_full_subject(result, nsubj='dobj')
        entity_list = get_full_subject(result, nsubj='pobj')
        if entity_list in property_var:
            property_var = property_var.replace(entity_list, '')
        if 'of' in property_var:
            property_var = property_var.replace('of', '')
        if 'members' in property_var:
            property_var = property_var.replace('members', 'member')
        if 'mission' in entity_list:
            entity_list = entity_list.replace('mission', '')
    elif result[0].dep_ == "nsubjpass" and result[1].dep_ == "auxpass":
        p = [item for item in result if item.dep_ == 'ROOT']
        r = nounify(p[0].lemma_)
        property_var = list(r)[1].name().split('.')[0]
        if property_var == 'finder':
            property_var = 'inventor'
        try:
            entity_list = [(x.text) for x in result.ents][0]
        except:
            entity_list = get_full_subject(result, nsubj='nsubjpass')
    elif result[0].pos_ == "ADP" and result[-1].dep_ == 'acl':
        property_var = result[-1].text + ' ' + result[0].text
        try:
            entity_list = [(x.text) for x in result.ents][0]
        except:
            entity_list = get_full_subject(result, nsubj='attr', dep='acl')

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
                            property_tokens = subject[i + 1:]
                    property_list = []
                    entity_list = []
                    for token in property_tokens:
                        property_list.append(token.text)
                    for token in entity_tokens:
                        entity_list.append(token.text)
                    property_var = " ".join(property_list)
                    entity_list = " ".join(entity_list)
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
                            entity_tokens = subject[i + 1:]
                    property_list = []
                    entity_list = []
                    for token in property_tokens:
                        property_list.append(token.text)
                    for token in entity_tokens:
                        entity_list.append(token.text)
                    property_var = " ".join(property_list)
                    entity_list = " ".join(entity_list)
    try:
        answer_list = get_answer(property_var, entity_list)
        print(id, "\t", end='')
        for item in answer_list:
            print(item, '\t', end='')
        print('')
    except:
        last_resort(question,id)

# last resort with noun chunks
def last_resort(line, id):
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
    if len(nounlist) == 0:
        entity = 'none'
    else:
        entity = nounlist[-1]  # last noun chunk is entity
    if len(nounlist) > 2:  # if list of noun chunks is longer than 3 the second item is property
        property = nounlist[-2]
    else:  # else the lemma of the root of the sentence is the property
        property = root[0]
    try:
        answerlist = get_answer(property,entity)
        print(id + "\t", end='')
        if answerlist is not None:
            for item in answerlist:
                print(item, '\t', end='')
            print('')
        else:
            print('No answer')


    except:
        print(id + '\t' + 'No answer')

# takes as input a question and returns one of the different types as specified on slide 5 of the instructions
def questiontype(question):
    nlp = spacy.load('en_core_web_sm')
    tokens = nlp(question)
    # filter specific words related to highest/lowest/first/last questions
    superlatives = ["biggest", "highest", "longest", "hottest", "lowest", "first", "last"]
    superlative = [i for i in question.split(" ") if i in superlatives]
    if len(superlative) > 0:
        return 'superlative_' + superlative[0]

    elif tokens[0].pos_ == 'AUX':
        return 'binary'

    elif question.split(" ")[0] == 'when':
        return 'when'

    elif question.split(" ")[0] == 'where':
        return 'where'

    elif tokens[0].pos_ == 'ADV' and tokens[1].pos_ == 'ADJ':
        if question.split(" ")[1] == 'many':
            return 'count'
        elif question.split(" ")[0] == 'how':
            return 'how'
    elif tokens[0].pos_ == 'ADV' and tokens[1].pos_ == 'AUX':
        return 'how'

    elif tokens[0].pos_ == 'VERB' or question.split(" ")[0] == 'name' and tokens[1].pos_ == 'DET':
        return 'x_y_list'

    elif tokens[0].pos_ == 'ADP' and tokens[1].pos_ == 'DET':
        return 'x_y piep piper'

    elif tokens[0].pos_ == 'PRON' and tokens[1].pos_ == 'AUX':
        if 'ADP' not in [i.pos_ for i in tokens]:
            return 'description'
        else:
            return 'x_y'

    else:
        return 'other'

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
        line = line.split("\t")
        q_id = line[0]
        question = line[1].lower().strip()
        if question[-1] == '.':
            question = question.replace('.', '')
        questiont = questiontype(question)
        if questiont == 'binary':
            binary_questions(question, q_id)
        elif questiont == 'x_y':
            get_questions_other(question, q_id)
        elif questiont == 'x_y_list':
            get_questions_other(question, q_id)
        elif questiont == 'count':
            count_questions(question, q_id)
        elif questiont == 'description':
            description(question, q_id)
        elif questiont == 'x_y piep piper':
            get_questions_other(question, q_id)
        elif questiont == 'when':
            get_questions_other(question, q_id)
        elif questiont == 'how':
            get_questions_other(question, q_id)
        elif questiont == 'where':
            get_questions_other(question, q_id)
        else:
            get_questions_other(question, q_id)


if __name__ == "__main__":
    main(sys.argv)
