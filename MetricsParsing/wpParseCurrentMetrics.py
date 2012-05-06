import sys, os, codecs, string, datetime, random, MySQLdb, re
from xml.sax import saxutils, make_parser, handler
from xml.sax.handler import feature_namespaces, ContentHandler
from wpdbsettings import *
# from wikiTextParsers import *
table= "ArticleOct"


# from wikiTextParsers import *

#
# To add a metric the following steps are required:
#
# 1. add the database field name to the "metrics" list in parseWikiFile
# 2. add the lambda function to self.metricDict component of class wikiHandler
# 3. create any regular expressions or other variable initialisation here
# 4. create any functions needed here 
#


#note: optimize Re's by limiting number of characters looked for

elementRe=re.compile(r'<.+?>(.+)</.+?>')
textEndRe=re.compile(r'(.+?)</text>')


#number of images
imageRe= re.compile(ur'\.(png)|(jif)|(jpe?g)|(svg)',re.IGNORECASE)

#number of wikilinks
wikilinkRe=re.compile(ur'\[\[([^\[]{1,100}?)(\|[^\[]+?)?\]\]')

#number of weblinks
weblinkRe=re.compile(ur'\*\s*\[http://.+?\]')

#number of tables
tableRe=re.compile(ur'{\|')

#number of interwikis
interwikiRe=re.compile(ur'(\[\[)(.{2,12}?):(.+?)(\]\])')

#number of categories
categoryRe=re.compile(ur'\[\[(.{1,40}?):.+?(\|.+?)?\]\]')

# number of sections
sectionRe  = re.compile(ur'(\n|^)==([^=]{1,100}?)==\s*\n')

# number of standard appendices
stdAppRe  = re.compile(ur'[\n^]==([^=]{1,100}?)==\s*\n')

# section depth
sectionDepthRe=re.compile(ur'(\n|^)(=+?)[^=]{1,100}?(=+)\s*\n')

#number of references
refRe=re.compile(ur'<ref[^a-zA-Z]')

#number of galleries
galleryRe=re.compile(ur'<gallery|{{gallery|{{image gallery',re.IGNORECASE)

#number of infoboxes
infoboxRe=re.compile(ur'({{|class=\")\s*([^\s}\|]{1,80})\s*([^\s}\|]{1,80})*\s*([^\s}\|]{1,80})*\s*([^\s}\|]{1,80})*\s*([^\s}\|]{1,80})*\s*([^\s}\|]{1,80})*\s*([^\s}\|]{1,80})*\s*([^\s}\|]{1,80})*\s*([^\s}\|]{1,80})*\s*([^\s}\|]{1,80})*\s*')

#number of navboxes
navboxRe=re.compile(ur'({{|class=\")\s*([^\s}\|]{1,80})\s*([^\s}\|]{1,80})*\s*([^\s}\|]{1,80})*\s*([^\s}\|]{1,80})*\s*([^\s}\|]{1,80})*\s*([^\s}\|]{1,80})*\s*([^\s}\|]{1,80})*\s*([^\s}\|]{1,80})*\s*([^\s}\|]{1,80})*\s*([^\s}\|]{1,80})*\s*')

#number of inline clean up tags
cleanupRe1=re.compile(ur'{{(.{1,80}?)}}')
cleanupRe2=re.compile(ur'{{(.{1,80}?)\|')

#number of portals
portalRe=re.compile(ur'{{([^\s]{5,20}?)\s')

#article grade
gradeRe1=re.compile(ur'{{(.{1,80}?)}}')
gradeRe2=re.compile(ur'{{(.{1,80}?)\|')

#ISBN/ISSN/PMID/doi
serialRe=re.compile(ur'(ISBN(\s|-)\d)|({{ISSN)|(PMID\s\d)|(\[\[doi)|({{doi)|({{cite.{1,15}?doi)',re.IGNORECASE)

# number of stub tags
stubtagCountRe = re.compile(ur'{{([^}]*-stub|\s*[Ss]tub)\s*}}')  
stubtagCountReLang = re.compile("String which never matches")

titleRe=re.compile(ur'<title>.*?</title>')
 
openBracketRe=re.compile(r'{{')
closeBracketRe=re.compile(r'}}')
navboxTemplates={}

#internationalisation dictionaries
gradeDict={}
categoriesDict={}
cleanupTagsDict={}
cleanupBannersDict={}
portalDict={}
infoboxDict={}
navboxDict={}
#stdAppsDict={}
interwikiDict=set([])

#article inlink counter
inLinks={}
idNameMap={}
gradeMap={'unrated':0,'stub':1,'start':2,'c':3,'b':4,'good':5,'a':6,'featured':7}
langs=['en','fr','fa','sw','he','arz','ar']

def loadInterwikiDict(Path):
     Dict=set([])
     fileIn=codecs.open(Path,mode='r',encoding='utf-8')
     line=fileIn.readline()
     while line:
          match=re.search(interwikiRe,line)
          if match!=None:
               Dict.add(match.group(2))
          line=fileIn.readline()
     return Dict

#This function loads dictionaries of different metrics
def loadDict(Path):
     Dict={}
     fileIN = codecs.open(Path,mode='r',encoding='utf-8')
     line=fileIN.readline()
     while line:
          terms=string.split(line)
          if len(terms)<2:
                  break
          clang=terms[0]
          nLines=int(terms[1])
          temp={}
          while line:
               line=fileIN.readline()
               terms=string.split(line)
               if len(terms)<2 or terms[0] in langs:
                  break
               terms[0]=terms[0].replace(':','').replace('}','').replace('|','')
               index=string.find(terms[0],'/')
               if index>=0:
                    terms[0]=terms[0][0:index]
               end=len(terms[0])
               if terms[0][end-2:end]==u'\u202a\u202c':
                    terms[0]=terms[0][0:end-2]
                    print terms[0]
               temp[terms[0]]=terms[1].strip()
          Dict[clang]=temp

     #for lang in langs:
      #  if lang!='en':
       #     Dict[lang].update(Dict['en'])
     Dict['arz'].update(Dict['ar'])
     return Dict

# counting matches of a particular metric from a sample of candidate lines in an article
def countMatches(pMatches,Dict,lang):

     count=0
     for match in pMatches:
          word=match.group(1) 
          if word in Dict[lang]:
               count+=1
     return count
    
    
# counting matches of a particular metric from a sample of candidate lines in an article
def getGrade(pMatches,pMatches2,Dict,lang):

     grade=''
     for match in pMatches:
          word=match.group(1) 
          if word in Dict[lang]:
               print word
               return Dict[lang][word]
     for match in pMatches2:
          word=match.group(1) 
          if word in Dict[lang]:
               print word
               return Dict[lang][word]
     return grade


# counting matches of a particular metric from a sample of candidate lines in an article
def countMatchesCleanup(pMatches,pMatches2,Dict,lang):

     count=0

     for match in pMatches:

          word=match.group(1)
  
          if word in Dict[lang]:
               count+=1
             #  print "First:"+match.group(1)
               
     for match in pMatches2:
 
          word=match.group(1)
          if word in Dict[lang]:
              # print "Second:"+match.group(1)
               count+=1
     return count
    
def getBoxes(pMatches,Dict,lang,name):
     count=0
 
     for match in pMatches:
          candidate=""
          for i in range(2,len(match.groups())+1):#modify this
            if match.group(i)==None:
                break
            
            word=match.group(i)
            candidate=candidate+word
        
            if(candidate in Dict[lang]):
                print name+" MatchFound:"+candidate
                count+=1
                break
     return count
    
# calculating maxdepth by counting the number of = signs in section expressions
def getMaxDepth(Matches):
     maxDepth=0
     for match in Matches:
	  if len(match.group(2))==len(match.group(3)):
	       if len(match.group(2))-1>maxDepth:
		    maxDepth=len(match.group(2))-1
     return maxDepth

def getInterwikis(Matches):
     count=0
     for match in Matches:
	  if (match.group(2) in interwikiDict) or (len(match.group(2))<3):
               count+=1
     return count


##################
#
# End of metrics
#
##################
# Based on code from wikiXray by Felipe Ortega and 
# PyXML tutorial by Dave Kuhlman

class wikiHandler:
	def __init__(self, metrics ,lang,articleSet,inFileName):

		# PARSER MANAGEMENT VARIABLES
		self.page_dict={}
		self.rev_dict = {}
		self.stack=[]
		self.current_text = ''
                self.compressed_text=''
		self.current_elem=None
		self.bodyText = ""
		self.pageCount = 0
		self.lang = lang
                self.inFileName=inFileName
                
		# ARTICLES OF INTEREST
		self.articleSet = articleSet

		# DATABASE CONFIGURATION
		self.hostname = HOSTNAME
		self.database = DATABASE
		self.username = USERNAME
		self.password = PASSWORD
		self.cursor = None
		self.connection = None
		self.fieldList = []

		# METRICS OF INTEREST
		self.metrics = metrics				
		self.metricDict = {
			'chars': lambda z: len(z),
			'words': lambda z: len(string.split(z)),
			'sections': lambda z: len(re.findall(sectionRe,z)),
                        'tables': lambda z: len (re.findall(tableRe,z)),
		        'images': lambda z: len (re.findall(imageRe,z)),
		        'wikilinksNum': lambda z: len (re.findall(wikilinkRe,z)),
		        'weblinksNum': lambda z: len (re.findall(weblinkRe,z)),
		        'depth':lambda z: getMaxDepth (re.finditer(sectionDepthRe,z)),
		        'inReferences':lambda z: len(re.findall(refRe,z)),
                        'interwikisNum': lambda z: getInterwikis (re.finditer(interwikiRe,z)),
                        'gradeName':lambda z:getGrade(re.finditer(gradeRe1,z),re.finditer(gradeRe2,z),self.gradeDict,self.lang),
		        'galleries':lambda z: len(re.findall(galleryRe,z)),
                        'categories': lambda z: countMatches(re.finditer(categoryRe,z),self.categoriesDict,self.lang),
		        'infoboxes':lambda z:getBoxes(re.finditer(infoboxRe,z),self.infoboxDict,self.lang,'infoboxes'),
                        'cleanupTags':lambda z:countMatchesCleanup(re.finditer(cleanupRe1,z),re.finditer(cleanupRe2,z),self.cleanupTagsDict,self.lang),
                        'cleanupBanners':lambda z:countMatchesCleanup(re.finditer(cleanupRe1,z),re.finditer(cleanupRe2,z),self.cleanupBannersDict,self.lang),
                        'navboxes':lambda z:getBoxes(re.finditer(navboxRe,z),self.navboxDict,self.lang,'navboxes'),
                        'serials':lambda z:len(re.findall(serialRe,z)),
                        'portals':lambda z:countMatches(re.finditer(portalRe,z),portalDict,self.lang),
                        'stdApps':lambda z: countMatches(re.finditer(stdAppRe,z),stdAppsDict),
                        'stubtagCount': lambda z: (len(re.findall(stubtagCountRe,z)) + len(re.findall(stubtagCountReLang,z)))
                         
		}
                self.compressed_metrics=set([])
                self.compressed_metrics.add('cleanupTags')
                self.compressed_metrics.add('cleanupBanners')
                self.compressed_metrics.add('categories')
                self.compressed_metrics.add('gradeName')
              
		self.gradeDict=loadDict("dictionaries/gradeDict.txt")
		self.cleanupTagsDict=loadDict("dictionaries/cleanupTagsDict.txt")
		self.cleanupBannersDict=loadDict("dictionaries/cleanupBannersDict.txt")
		self.categoriesDict=loadDict("dictionaries/categoryDict.txt")
                self.portalDict=loadDict("dictionaries/portalDict.txt")
                self.infoboxDict=loadDict("dictionaries/infoboxDict.txt")
                self.navboxDict=loadDict("dictionaries/navboxDict.txt")
                self.interwikiDict=loadInterwikiDict("dictionaries/interwikiDict.txt")
                #stdAppsDict=loadDict("dictionaries/stdAppsDict.txt")
                self.startDB()
                self.initializeMetrics()
        
        def startDB(self):
		try:
			self.connection = MySQLdb.connect (self.hostname,
			   self.username,
			   self.password,
			   self.database)

		except MySQLdb.Error, e:
			print "Error %d: %s" % (e.args[0], e.args[1])
			sys.exit()
		self.cursor = self.connection.cursor ()
                
		print "--------	 Document Start --------"
		# self.endDocument()
		# sys.exit()


	def initializeMetrics(self):
		# Check that metrics actually exist in the database. 
		self.connection.query("SHOW COLUMNS FROM %(database)s.%(table)s;" % {"database":self.database,"table":table})

		x = self.connection.store_result()
		rows = x.fetch_row(0)
		for i in rows: 
			self.fieldList.append(i[0])

		for i in self.metrics:
			if i not in self.fieldList:
				self.metrics.pop(self.metrics.index(i))
				print "The field %s is not included in the database. Please add this and continue." % i
			elif i not in self.metricDict.keys():
				self.metrics.pop(self.metrics.index(i))
				print "Warning: there is no method to populate the field %s" % i
        
        def parse(self):
                
                inFile=codecs.open(self.inFileName,mode='r',encoding='utf-8')
                line=inFile.readline()
                while line:
                    if line.strip()!='<page>':
                        print "erroneous input"
                        break
                    self.extractDetails(inFile)
             
                    if self.page_dict['key'] in articleSet:
                        self.cleanText(self.metrics)
                        self.updateFields()
                    
		    if self.pageCount % 10000 == 0:
				print "Parsing article #%d: %s" % (self.pageCount, self.page_dict['title'])
       
                    self.pageCount+=1
                    
                    line=inFile.readline()
                inFile.close()
                self.closeDB()

        def extractDetails(self,inFile):
    
                self.page_dict['revid']=re.match(elementRe,inFile.readline()).group(1)
                self.page_dict['id']=re.match(elementRe,inFile.readline()).group(1)
                self.page_dict['title']=re.match(elementRe,inFile.readline()).group(1)
                self.current_text=""
       
                line=inFile.readline().strip()
                line=string.replace(line,'<text>','')
                while line.find('</text>')<0:
                     self.current_text+=line
                     line=inFile.readline()
                self.current_text+=line.replace('</text>','')
                self.page_dict['key']=self.lang+'_'+self.page_dict['revid']
                
                print str(self.pageCount)+":"+self.page_dict['key']
                print self.page_dict['title']
                
                self.current_text=self.current_text.lower()
                self.compressed_text=self.current_text.replace(' ','')
                line=inFile.readline()
         

        def cleanText(self,metrics=[]):
		'''This method is called in order to process the current text for any given Wikipedia entry. 
		It is in here that one should find regular expression methods for searching and slicing and dicing the text.
		This method will loads a series of helper methods, each one designed to parse the text in a specific way.'''
		for i in metrics:
                        if self.metricDict.has_key(i):
                            
                            if i in self.compressed_metrics:
                                self.page_dict[i] = self.metricDict[i](self.compressed_text)
                            else:
				self.page_dict[i] = self.metricDict[i](self.current_text)
                #self.page_dict['wikilinksNum']-=self.page_dict['interwikisNum'] 

	def updateFields(self):
		query = "UPDATE %(database)s.%(table)s SET" % {"database":self.database,"table":table}
                query += " idArticle='%s'," % (self.page_dict['id'])
		for i in self.metrics: 
			query += " %s='%s'," % (i,self.page_dict[i])
	       # query+="%s='%s',"('articleId',self.page_dict['id'])
		query = query[:-1] + " where keyArticle = '%s'" % (self.lang + "_" + self.page_dict["revid"])
               
                try: 
   			self.cursor.execute(query)

		except	MySQLdb.Error, e:
 			print "Error %d: %s" % (e.args[0], e.args[1])
			sys.exit()
          
        def closeDB(self):
		print "--------	 Document End --------"
                
		self.cursor.close()
		self.connection.commit()
		self.connection.close()
  
def startDB():
	try:
		connection = MySQLdb.connect(HOSTNAME, USERNAME, PASSWORD, DATABASE, charset='utf8')

	except MySQLdb.Error, e:
		print "Error %d: %s" % (e.args[0], e.args[1])
		sys.exit()

	cursor = connection.cursor()
	return (connection,cursor)

def closeDB(con,cur):
	cur.close()
	con.commit()
	con.close()
        
          
def getArticleSet(key="keyArticle"):
	con,cur = startDB()
        con.query("SELECT %(key)s FROM wikiproject.%(table)s"% {"table":table,"key":key})
        articleSet,templist=getIds(con)
        
        print len(articleSet)
	closeDB(con,cur)
	return articleSet

def getIds(con):
        articleSet = set([])
        articleList=[]
	x = con.store_result()
	rows = x.fetch_row(0)
	for i in rows: 
		articleSet.add(str(i[0]))
                articleList.append(str(i[0]))
        return articleSet,articleList
     
def parseWikiFile(inFileName,lang,articleSet):

	# Create an instance of the Handler.

	# THIS IS THE MOST IMPORTANT METHOD. It is where we define what data will be inserted. 
	# The metric will not be imported if the follow conditions are the case:
	# 1. The element is not a column name in the wikiproject.Article table. 
	# 2. the element is not in the self.metricsDict object in the parser class. 
	# 3. self.metricsDict calls a method that does not yet exist. 
	
	metrics = [ "chars",
	            "words",
	            "sections",
	            "images",
	            "wikilinksNum",
	            "weblinksNum",
	            "tables",
	            "depth",
	            "inReferences",
                    "interwikisNum",
                    "gradeName",
                    "galleries",
                    "categories",
	            "infoboxes",
                    "cleanupTags",
                    "cleanupBanners",
                    "navboxes",
                    "serials",
                    "portals",
                    "stubtagCount",
                    "stdApps",
                    
	        ]
     
        # init the metrics - should be in the wikiHandler constructor or the intialiseMetrics method, but for now just invoke them one at a time.
	#stubtagCountReLang =initStubtagCount(lang)

        handler = wikiHandler(metrics,lang,articleSet,inFileName)
	handler.parse()
        
if __name__ == '__main__':
	start=datetime.datetime.now()
	PATH = "../xml/"
        dumpIn=codecs.open("geoExtract/dumpLinks.txt",mode='r',encoding='utf-8')
        articleSet = getArticleSet()
        line=dumpIn.readline()
   
        while line:
             terms=string.split(line)
             if terms[0]=='en':
                line=dumpIn.readline()
                continue
             parseWikiFile("Articles/"+terms[0]+"FullArticles.txt",terms[0],articleSet)
             elapsed=datetime.datetime.now() - start
             print elapsed
             line=dumpIn.readline()
