# -*- coding: utf-8 -*-

__version__ = 0.1

import sys, os, codecs, string, datetime, random, MySQLdb
from wpdbsettings import *


def getDB():
	try:
		connection = MySQLdb.connect(HOSTNAME, USERNAME, PASSWORD,	DATABASE, charset='utf8')
		print HOSTNAME
		print USERNAME
		print PASSWORD

	except MySQLdb.Error, e:
		print "Error %d: %s" % (e.args[0], e.args[1])
		sys.exit()
	cursor = connection.cursor()

	return (connection,cursor)
	

conn, cur = getDB()
conn.query("SHOW COLUMNS FROM wikiproject.ArticleOct")

fieldList = []
x = conn.store_result()
rows = x.fetch_row(0)
for i in rows: 
	fieldList.append(i[0])
	print i[0]

# print fieldList
cur.execute("SET NAMES utf8")
 
try:
	filein = codecs.open(sys.argv[1],'r','utf-8')
except:
        print "Can't open file %s" * sys.argv[1]

headers = None
 
start = datetime.datetime.now()	
counter = 0
  
count=0
for c,i in enumerate(filein.readlines()):
	data  = i.strip().split("\t")
        
        if len(data)==1:
                break
	if c == 0:
		headers = data
		print headers
		
		try:
			keyIndex  = headers.index("keyArticle")
                        talkIndex = headers.index("idTalk")

		except ValueError:
			continue
 			
	
	else:
		query = u"UPDATE ArticleOct  SET  idTalk='%s' "% (data[talkIndex])
		if len(headers) != len(data):
			continue
			
		for i in range(len(headers)):
			if i!=keyIndex and i!=talkIndex:
				data[i] = data[i].replace("'","\\'")
				query += ", %s='%s'" % (headers[i],data[i])
                query+=" where keyArticle='%s'"%(data[keyIndex])
		count+=1		
		if (count%10000==0):
			print 'added '+str(count)
		cur.execute(query)
		

finish = datetime.datetime.now()
print finish-start
print counter
cur.close()
conn.commit()
conn.close()
