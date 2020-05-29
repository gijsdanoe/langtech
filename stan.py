#!/usr/bin/env python3
import socket
import sys
from lxml import etree
from SPARQLWrapper import SPARQLWrapper, JSON

def main():
	questionlist = ["Wat is het gewicht van Michael Phelps?",
			"Wat was de locatie van de Olympische Spelen van 2012?",
			"Wat is de trainer van Usain Bolt?",
			"Wat is het gewicht van Usain Bolt?",
			"Wat is de bijnaam van Michael Phelps?",
			"Wat is de geboortedatum van Ireen Wust?",
			"Wat is de geboortestad van Sven Kramer?",
			"Op welke plek werden de Olympische Winterspelen van 2010 gehouden?",
			"Bij welke ploeg schaatst Ireen Wust?",
			"Wat is de alias van Sven Kramer?"]
	for question in questionlist:
		print(question)
	for line in sys.stdin:
		line = line.rstrip()
		runquery(line)

def alpino_parse(sent, host='zardoz.service.rug.nl', port=42424):
	s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
	s.connect((host,port))
	sent = sent + "\n\n"
	sentbytes= sent.encode('utf-8')
	s.sendall(sentbytes)
	bytes_received= b''
	while True:
		byte = s.recv(8192)
		if not byte:
			break
		bytes_received += byte
	xml = etree.fromstring(bytes_received)
	return xml

def getpropname(questionproperty):
	if questionproperty == 'lengte' or questionproperty == 'grootte':
		prop = "prop-nl:lengte"
	elif questionproperty == 'gewicht' or questionproperty == "zwaarte":
		prop = "prop-nl:gewicht"
	elif questionproperty == 'leeftijd' or questionproperty == "oudheid":
		prop = "prop-nl:leeftijd"
	elif questionproperty == 'trainer' or questionproperty == 'coach':
		prop = "prop-nl:coach"
	elif questionproperty == "plaats" or questionproperty == "stad" or questionproperty == "locatie":
        	prop = "prop-nl:plaats"
	elif questionproperty == "bijnaam" or questionproperty == "nickname" or questionproperty == "alias":
		prop = "prop-nl:bijnaam"
	elif questionproperty == "geboortedatum" or questionproperty == "geboortedag":
		prop = "prop-nl:geboortedatum"
	elif questionproperty == "geboorteplaats" or questionproperty == "geboortestad":
		prop = "prop-nl:geboortestad"
	elif questionproperty == "ploeg" or questionproperty == "team":
		prop = "prop-nl:ploeg"
	else:
		print('Helaas kan het antwoord op deze vraag niet gevonden worden.')
		prop = []
	return prop
	
def runquery(question):
	xml = alpino_parse(question)
	properties = xml.xpath('//node[../@cat="np" and @rel="hd"]')
	subjects = xml.xpath('//node[../@rel="obj1"]')
	propertylist = []
	subjectlist = []

	for name in properties:
		if name == 'de' or name == 'het':
			continue
		else:
			try:
				propertylist.append(name.attrib['word'])
			except KeyError:
				break
	questionproperty = ' '.join(propertylist)

	#Helaas heb ik het niet voor elkaar gekregen om het onderwerp van de zin te vinden via Alpino, hieronder nog wel een stukje code waarmee ik een poging heb gewaagd.
	#for name in subjects:
	#	try:
	#		subjectlist.append(name.attrib['sense'])
	#	except KeyError:
	#		continue
	#for name in subjects:
	#	try:
	#		subjectlist.append(name.attrib['mwu_sense'])
	#	except KeyError:
	#		continue
			
	question = question.rstrip("?")
	questionlist = question.split()
	if questionlist[5] == "de" or questionlist[5] == "het":
		questionobject = questionlist[6:]
	else:
		questionobject = questionlist[5:]
	File = open('pairCounts')
	maxlist = []
	objectstring = ' '.join(questionobject)
	print('Het object is',objectstring,', de property is',questionproperty,'.')
	for line in File:
		things = line.split("\t")
		if objectstring == things[0]:
			maxlist.append([things[0],things[1],things[2].rstrip("\n")])
	maxlist.sort(key=lambda x: int(x[2]), reverse=True)
	if maxlist == []:
		print('Er kan helaas geen antwoord op deze vraag gevonden worden')
	else:
		uri = maxlist[0][1]
		prop = getpropname(questionproperty)
		if prop != []: 
			print(uri,prop)
			query = 	""" select ?antwoord
            				WHERE {
            				<""" + uri + """>""" + prop +""" ?antwoord
            				}"""
	
			sparql = SPARQLWrapper("http://nl.dbpedia.org/sparql")
			sparql.setQuery(query)
	
			sparql.setReturnFormat(JSON)
			results = sparql.query().convert()
			testlist = []
			for result in results["results"]["bindings"]:
				for arg in result :
					answer = arg + " : " + result[arg]["value"]
					print(answer)

if __name__ == "__main__":
	main()
