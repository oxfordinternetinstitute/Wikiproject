#This code parses template pages for compiling common templates for infoboxes,navboxes...etc..
import sys, os, codecs, string, datetime, random, MySQLdb, re
from xml.sax import saxutils, make_parser, handler
from xml.sax.handler import feature_namespaces, ContentHandler
from wpdbsettings import *
# from wikiTextParsers import *
table= "ArticleOct"
## create dictionary files for all measures
template={}
Dict={}
metrics=['stubTagCount','stdAppsDict','gradeDict','cleanupTagsDict','cleanupBannersDict','portalDict','categoriesDict','infoboxDict','navboxDict','serialsDict','gradeDict']
	
langs=['en','fr','fa','ar','arz','he','sw']
specialRe=re.compile(ur'(.+):(.+)')
bracketRe=re.compile(ur'({{|\[\[)')
templateWords=set([])

class wikiHandler(handler.ContentHandler):
	def __init__(self, metrics = [],lang=''):

		# PARSER MANAGEMENT VARIABLES
		self.page_dict={}
		self.rev_dict = {}
		self.stack=[]
		self.current_text = ''
		self.current_elem=None
		self.bodyText = ""
		self.pageCount = 0
		self.lang = lang

		# DATABASE CONFIGURATION
		self.hostname = HOSTNAME
		self.database = DATABASE
		self.username = USERNAME
		self.password = PASSWORD
		self.cursor = None
		self.connection = None
		self.fieldList = []
		
	def startDocument(self):
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

	def endDocument(self):
		print "--------	 Document End --------"
                
		self.cursor.close()
		self.connection.commit()
		self.connection.close()

	def startElement(self, name, attrs):
	
		if name=='page':
			self.stack = [name]
		elif name=='revision' or name=='contributor':
			self.stack.append(name)
		elif name=='namespace':
			self.codens=attrs.get('key')
		elif name == "mediawiki":
			if attrs.has_key("xml:lang"):
				self.lang = attrs["xml:lang"]
			else:
				self.lang = "??"

		self.current_text=''
		self.current_elem=name
		return


	def endElement(self, name):			
	       
		if name=='namespace':
			pass
			
		elif name=='id':
			if self.stack[-1]=='contributor':
				##Detecting contributor's attributes inside a revision
				self.rev_dict['rev_user']=self.current_text
			elif self.stack[-1]=='revision':
				self.rev_dict[name]=self.current_text
			elif self.stack[-1]=='page':
				self.page_dict[name]=self.current_text
			else:
				pass

		elif name=='ip':

			self.rev_dict['rev_user']='0'
			self.rev_dict['username']=self.current_text

		elif name=='timestamp':
			##Adequate formatting of timestamps
			self.rev_dict['timestamp']=self.current_text.replace('Z','').replace('T',' ')

		elif name=='contributor' or name=='revision':
			self.stack.pop()
		
		elif name=='page':
			self.page_dict['revid'] = self.rev_dict['id']
			self.page_dict['timestamp'] = self.rev_dict['timestamp']
			self.page_dict['lang'] = self.lang
			
	
			self.stack.pop()

			if self.pageCount % 1000 == 0:
				print "Parsing article #%d: %s" % (self.pageCount, self.page_dict['title'])

			self.pageCount += 1


		else:
			if len(self.stack)>0 and (self.stack[-1]=='revision'):
				# print self.current_elem
				if self.current_elem != "text":
					self.rev_dict[self.current_elem]=self.current_text
				else:
				
                                        match=re.match(specialRe,self.page_dict['title'])
                                        if match!=None:
                                            pageType=string.lower(match.group(1))
                                            pageName=string.lower(match.group(2))
					    
                                            if pageType==template[self.lang] and (pageName not in templateWords):
						
                                                print self.page_dict['title']
                                                print self.current_text
                                                print ''
						self.current_text=string.lower(self.current_text).replace(' ','')
                                                for metric in Dict:
                                                    for name in Dict[metric][self.lang]:
                                                        index=self.current_text.find(name)
                                                        if index>1:
                                                            sub=self.current_text[index-2:index]
                                                            if re.search(bracketRe,sub)!=None:
                                                                Dict[metric][self.lang][pageName]=Dict[metric][self.lang][name]
                                                                print self.page_dict['title']
                                                                print name+'\t'+Dict[metric][self.lang][name]
                                                                print ''
                                                                self.current_elem=None
                                                                return
                        
			elif len(self.stack)>0 and self.stack[-1]=='page':
				self.page_dict[self.current_elem]=self.current_text

		self.current_elem=None
	

	def characters(self, ch):
		if self.current_elem != None:
			self.current_text = self.current_text + ch

     
def parseWikiFile(inFileName,lang):

        handler = wikiHandler(lang)

	# Create an instance of the parser.
	parser = make_parser()
	
	# # Set the document handler.
	parser.setContentHandler(handler)
        print "Opening file " + inFileName
	try:
            inFile = open(inFileName, 'r')
	except: 
	    print "failed to open " + inFileName 
			
	# # Start the parse.
        
	parser.parse(inFile)
        #updateSpecialFields()
	inFile.close()


#This function loads dictionaries of different metrics
def loadDict(metric):
        temp={}
        fileIN = codecs.open("dictionaries/"+metric+".txt",'r','UTF-8')
        line=fileIN.readline()
        while line:
            terms=string.split(line,'\t')
            clang=terms[0]
            nLines=int(terms[1].strip())
            temp[clang]={}
            for i in range(0,nLines):
                terms=string.split(fileIN.readline(),'\t')
                temp[clang][terms[0].replace(' ','')]=terms[1].strip().replace(' ','')
                templateWords.add(terms[0].replace(' ',''))
		print terms[0].replace(' ','')
		print terms[1].strip().replace(' ','')
            line=fileIN.readline()
       
        return temp
   
def loadMetrics():
        for metric in metrics:
            Dict[metric]=loadDict(metric)
            
def loadTemplates():
        inFile=codecs.open("dictionaries/templateNames.txt",'r','UTF-8')
        line=inFile.readline()
        while line:
            terms=string.split(line)
            template[terms[0].lower()]=terms[1].lower()
	    print terms[0].lower()
	    print terms[1].lower()
            line=inFile.readline()
        
def printDict(metricDict,fileName):
        outFile=codecs.open("dictionaries/"+fileName+".txt",'w','UTF-8')
        for lang in langs:
            outFile.write(lang+'\t'+str(len(metricDict[lang]))+'\n')
            for word in metricDict[lang]:
                outFile.write(word+'\t'+metricDict[lang][word]+'\n')
        outFile.close()
            
if __name__ == '__main__':
	start=datetime.datetime.now()
	PATH = "../xml/"
        dumpIn=codecs.open("geoExtract/dumpLinks2.txt",'r')
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
