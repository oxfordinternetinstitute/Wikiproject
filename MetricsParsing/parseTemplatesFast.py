#This code parses template pages for compiling common templates for infoboxes,navboxes...etc..it is fast because it does so by directly 
#processing a cache of template pages instead of processing the whole dump

import sys, os, codecs, string, datetime, random, MySQLdb, re
from xml.sax import saxutils, make_parser, handler
from xml.sax.handler import feature_namespaces, ContentHandler
from wpdbsettings import *
from copy import deepcopy
# from wikiTextParsers import *
table= "ArticleOct"
elementRe=re.compile(r'<.+?>(.+)</.+?>')
textEndRe=re.compile(r'(.+?)</text>')

templateWords=set([])
filteredNames={}
template={}
Dict={}
originalDict={}
edges=["{{","class=\""]
metrics=['stubTagCount','stdAppsDict','categoriesDict','portalDict','infoboxDict','navboxDict','gradeDict','cleanupTagsDict','cleanupBannersDict']
langs=['en','fr','fa','ar','arz','he','sw']
specialRe=re.compile(ur'(.+):(.+)')
bracketRe=re.compile(ur'.+?({{|\[\[|class=\")')

   
def updateDicts(page,currentLang):

        text=page['text']
        match=re.match(specialRe,page['title'])
        if match!=None:
            pageName=string.lower(match.group(2)).replace(' ','')
            if pageName not in templateWords:

                text=string.lower(text).replace(' ','')
            
                for metric in originalDict:
                    for lang in langs:
                        for name in originalDict[metric][lang]:
                            
                    	    index=text.find(":"+template[lang]+":"+filteredNames[name]+"]]")
			    if index >=0 :
                                    print 'templateExtraction'
                                    print name+'\t'+pageName+'\t'+Dict[metric][lang][name]
                                    print page['title']
                                    print text
                                    print ''
                                    Dict[metric][currentLang][pageName]=Dict[metric][lang][name]
                                    return
                                    
                            index=text.find(name)
                            if index>=0:
                                if text.find(name)>=0:
                                    if name=='infobox':
                                        if text.find('infoboxrequested')>=0:
                                             continue
                                    elif name=='navbox':
                                        if text.find('navboxes')>=0:
                                             continue
                                    for edge in edges:
                                        if text.find(edge+name)>=0:
                                             print 'textExtraction'
                                             print edge+name
                                             print name+'\t'+pageName+'\t'+Dict[metric][lang][name]
                                             print page['title']
                                             print text
                                             print ''
                                             Dict[metric][currentLang][pageName]=Dict[metric][lang][name]
                                             break
  
            
def extractDetails(inFile):
       
        details={}
        
        details['revisionId']=re.match(elementRe,inFile.readline()).group(1)
        details['pageId']=re.match(elementRe,inFile.readline()).group(1)
        details['title']=re.match(elementRe,inFile.readline()).group(1)
        details['text']=""
        #print details['revisionId']
        #print details['pageId']
        #print details['title']
        line=inFile.readline().strip()
     
        line=string.replace(line,'<text>','')
        while re.search(textEndRe,line)==None:
            details['text']+=line
            line=inFile.readline()
        details['text']+=re.match(textEndRe,line).group(1)
        
        line=inFile.readline()
        return details

def parseWikiFile(inFileName,lang):

	inFile=codecs.open("Templates/"+lang+"FullTemplates.txt",'r','UTF-8')
	for edge in edges:
            print edge
	line=inFile.readline()
	while line:
		if line.strip()!='<page>':
		    print "erroneous input"
		templateDetails=extractDetails(inFile)
		updateDicts(templateDetails,lang)
                line=inFile.readline()
	inFile.close()
        
def printDict(metricDict,fileName):
        outFile=codecs.open("dictionaries/"+fileName+".txt",'w','UTF-8')
        for lang in langs:
            outFile.write(lang+'\t'+str(len(metricDict[lang]))+'\n')
            for word in metricDict[lang]:
                outFile.write(word+'\t'+metricDict[lang][word]+'\n')
        outFile.close()
        
#This function loads dictionaries of different metrics
def loadDict(metric):
        temp={}
        fileIN = codecs.open("dictionaries/"+metric+".txt",'r','UTF-8')
        line=fileIN.readline()
        print metric
        while line:
            terms=string.split(line,'\t')
            clang=terms[0]
            nLines=int(terms[1].strip())
            temp[clang]={}
            print clang
            for i in range(0,nLines):
                terms=string.split(fileIN.readline(),'\t')
                temp[clang][terms[0].replace(' ','').lower()]=terms[1].strip().replace(' ','').lower()
                Name=terms[0].replace(' ','').lower()
                alphaName=terms[0].replace(' ','').lower().replace('|','').replace('}','').replace(':','')
                filteredNames[Name]=alphaName
                templateWords.add(alphaName)
		print terms[0].replace(' ','')+'\t'+terms[1].strip().replace(' ','')
            line=fileIN.readline()
            
        fileIN.close()
    
        return temp
   
def loadMetrics():
        for metric in metrics:
            Dict[metric]=loadDict(metric)
            originalDict[metric]=loadDict(metric)

        
def loadTemplates():
        inFile=codecs.open("dictionaries/templateNames.txt",'r','UTF-8')
        line=inFile.readline()
        while line:
            terms=string.split(line)
            template[terms[0].lower()]=terms[1].lower()
	    print terms[0].lower()
	    print terms[1].lower()
            line=inFile.readline()

if __name__ == '__main__':
	start=datetime.datetime.now()
	PATH = "../xml/"
        dumpIn=codecs.open("geoExtract/dumpLinks.txt",'r')
        loadMetrics()
        loadTemplates()
        line=dumpIn.readline()
        while line:
             terms=string.split(line)
             parseWikiFile(PATH+terms[1],terms[0])
             elapsed=datetime.datetime.now() - start
             print elapsed
             line=dumpIn.readline()
        
        for metric in metrics:
             printDict(Dict[metric],metric)
