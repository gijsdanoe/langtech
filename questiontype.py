#!/usr/bin/env python3

#todo
# what is x spec
# list question is handled the same as x_y

# how to solve how and when questions?
# description , x_y, count, binary, how, when, who (persoon en description)

# binary count order description

import spacy
import sys

def questiontype(question):
    """takes as input a question and returns one of the different types as specified on slide 5 of the instructions"""
    nlp = spacy.load('en_core_web_sm')
    tokens = nlp(line)
    # filter specific words related to highest/lowest/first/last questions
    superlatives = ["biggest", "highest", "longest", "hottest", "lowest", "first", "last"]
    superlative = [i for i in question.split(" ") if i in superlatives]
    if len(superlative) > 0:
        return 'superlative_' + superlative[0]

    elif tokens[0].pos_ == 'AUX':
        return 'yes_no'
    elif tokens[0].pos_ == 'PRON' and tokens[1].pos_ == 'AUX':
        return 'x_y'
    elif tokens[0].pos_ == 'VERB' and tokens[1].pos_ == 'DET':
        return 'x_y_list'
    elif question.split(" ")[0] == 'how' and question.split(" ")[1] == 'many':
        return 'count'
    elif tokens[0].pos_ =='ADV' and tokens[1].pos_ == 'ADJ':
        return 'x_y ' + tokens[1].lemma_
    elif tokens[0].pos_ == 'ADP' and tokens[1].pos_ == 'DET':
        return 'x_y piep piper'

    #who question, almost always inventor, quick solution for now
    elif questions.split(" ") == 'who':
        return 'inventor_y'
    #else:
        

# testing the function

with open(sys.argv[1], 'r') as f:
    qlist = list()
    for line in f:
        line = line.rstrip()
        qlist.append(line)

#for line in qlist:
for line in qlist:
    try:
        qtype = questiontype(line)
        print(qtype, line)
    except:
        print(None, line)



# what who is the X of Y
# List questions (name all crew members of the apollo 15 mission, what are the X of Y)
# yes/no (is atropa belladonna a poisonous plant, did newton discover penicilin)
# count questions (how many nobel prizes has marie cury won, how many member states does CERN have
# highest lowest first last questions
