import MySQLdb
import glob,linecache,sys, os, codecs, string, datetime, random, re
from xml.sax import saxutils, make_parser, handler
from xml.sax.handler import feature_namespaces, ContentHandler
from datetime import datetime,time,date
import copy
from wpdbsettings import *

ampRe=re.compile(ur'&amp;')
quotRe=re.compile(ur'(&quot;)')
infoboxRegex=re.compile(r'({{Infobox)|({{Geobox)',re.IGNORECASE)
interwikiRegex=re.compile(r'(\[\[)(en|fa|fr|he|sw|ar|arz):(.+?)(\]\])')
newArticleRegex=re.compile(r'<title>(.+?)</title>')
numberRegex=re.compile(r'(-?\d+\.*\d*)')
rangeElement=re.compile(ur'u\00E0|to',re.IGNORECASE)
directionElement=re.compile(ur'\s*[\|\\/\u00B0\u2032\u2033\u0027\u00A0\u0022]\s*(N|S|W|E|East|West|North|South|O|Ouest|Sud|Nord|Est)[\u00A0\s\\\|/}\n\t]')
trailingCh=re.compile(r'(\s*[=\|])')

#generic regular expression for all representations
#specific one for french
#\u00B0 is degree, \u2032 is prime, \u2033 is double prime, u\0027 is apostrophe,\u00A0 non breaking space,\u0022 quotation mark
formatAll=re.compile(ur'(\s*[^\s]\s*((-?\d+\.?\d*)|N|S|W|E|East|West|North|South))[\s\\\|/}\n\t,\u00A0\u00B0\u0027\u2032\u2033\u0022]')
formatFr=re.compile(ur'(\s*[^\s]\s*((-?\d+\.?\d*)|N|S|W|E|Nord|Sud|O|Ouest|Est))[\s\\\|/}\n\t,\u00A0\u00B0\u2032\u2033\u0027u\00E0\u0022]')


geoArticles=set([])
formatLang={}
names={}
coordType={}
prefixList={}
coordTable={}
interwikiTable={}
articleSet={}
skipTable={}
Rejected={}
directionMap={'South':-1,'West':-1,'S':-1,'W':-1,'O':-1,'Ouest':-1,'Sud':-1,'N':1,'E':1,'North':1,'East':1,'Est':1,'Nord':1}

#lambda dictionary for calling functions to calculate values of different lat/long representations
normalizeEntry={
         'lat':(lambda z:z),'long':(lambda z:z),
         'latitude':(lambda z:z),'longitude':(lambda z:z),
         'latd':(lambda z:z),'latm':(lambda z:(limit(z,60))),'lats':(lambda z:(limit(z,3600))),
         'longd':(lambda z:z),'longm':(lambda z:(limit(z,60))), 'longs':(lambda z:(limit(z,3600))),
         'latSign':(lambda z: sign(z)),'longSign':(lambda z: sign(z))
         }

# this is the main function which runs the coordinate search process
def scan(lang,langxml,con,cur):

         fileIN = codecs.open( "../xml/"+langxml,'r','UTF-8')
         
         bracketMatch=0
         articleName=None
         RevId=None 
         skipArticle=False
         parseFlag='None'
         label='other'
         bracketCount=0
         count=1
         skipInterwiki=False
         cases=0
         while True:
                  previousFlag=parseFlag
                  line=fileIN.readline()
                  if len(line)==0:
                           break
                        
                   #check for a new article
                  nextArticle=newarticleCheck(line)
                  if True in nextArticle:
                           skipInterwiki=False
                           validateCoords(RevId)
                           articleName=nextArticle[True]
                           RevId=getId(fileIN)
                           articleSet[lang].append({articleName:RevId})
                           bracketCount=0
                           label='other'
                           parseFlag='None'
                           previousFlag='None'
                           
                           if re.search(ampRe,articleName)!=None:
                                    articleName=string.replace(articleName,'amp;','')
                           if re.search(quotRe,articleName)!=None:
                                    articleName=string.replace(articleName,'&quot;','\"')
                                    
                           if Tagged(lang+'_'+RevId):
                                    skipInterwiki=True
                           elif skipCheck(RevId,lang,articleName):
                                    skipArticle=True
                                    parseFlag='complete'
                           else:
                                    skipArticle=False
                           continue
                  
                  if skipInterwiki:
                           continue

                  #check for infobox if outside one otherwise update bracket count to detect an exit form an infobox
                
                  if label=='other':
                           if infoboxCheck(line):
                                    label='infobox'
                                    bracketCount+=incrementBracketCount(line)
                                    continue
                           
                  elif label=='infobox':
                           bracketCount+=incrementBracketCount(line)
                           if bracketCount==0:
                                    label='after'
                                     
                  if skipArticle:
                       
                           if parseFlag!='complete':
                                    parseFlag=parseLine(line,lang,label,RevId,articleName,'complete')
                                    if parseFlag=='complete' and validateCoords(RevId):
                                             updateTable(RevId,lang,articleName)
                                             print 'problematic case:'+str(cases)
                                             printArticleGeo(RevId,count)
                                             updateDB(RevId,con,cur)
                                             cases+=1
                           continue
                        
                           
                  #parse line for coordinates
                  parseFlag=parseLine(line,lang,label,RevId,articleName,'any')
                  
                  # add first parsed article coordinates to table, or reinitialise coordinates if the parsed ones are invalid
                  if (parseFlag=='complete' or (parseFlag=='None' and previousFlag=='coordFound')): # which means that coordinates have been read once
                           if validateCoords(RevId)==False:
                                    parseFlag='None'
                           else:
                                    updateTable(RevId,lang,articleName)
                                    printArticleGeo(RevId,count)
                                    updateDB(RevId,con,cur)
                                    count=count+1
                                    skipArticle=True

#checks if an article should be skipped if its designated as an ignorable article or if its coordinates have already been parsed
def skipCheck(Id,lang,name):
         link=lang+'_'+name
        
         if string.find(name,'crater)')!=-1:
                  skipTable[link]=''
         if Id in coordTable or (link in skipTable):
                  return True
         return False

def Tagged(Id):
         if Id in geoArticles:
                  return True
         return False

#info box flag to distinguish coordinates inside infoboxes(potentially more credible than those outside)
def infoboxCheck(line):
         if re.search(infoboxRegex,line)!=None:
                  return True
         return False 
                           
# looks for new article lines
def newarticleCheck(line):
         if string.find(line,'<titl')==-1:
                  return {False:False}
         article=re.search(newArticleRegex,line)
         if article!=None:
                  return {True:article.group(1)}
         return {False:False}

# checks if an article as coordinates or not and if so whether they are valid
def validateCoords(Id):
    
         if Id==None:
                  return False
                
         if Id in coordTable:
                  table=coordTable[Id]
                  if illegalCoords(table):
                           Rejected[Id]=dict(coordTable[Id])
                           del coordTable[Id]
                           return False
                  elif Id in Rejected:
                           del Rejected[Id]
                  return True
         else:
                  return False

# checks if the calculated coordinates are erroneous in cases like having only a latitude or a longitude entry
# or having an out of range coordinate
def illegalCoords(table):
    
         if ('latitude' not in table) or ('longitude' not in table) or (table['latitude']==0 and table['longitude']==0):
                  return True

         if (abs(table['latitude'])>90) or (abs(table['longitude'])>180):
                  return True
         return False
 
#update the coordinate table with a coordinate entry
def updateTable(Id,lang,articleName):
         
         if  Id in coordTable:
                  if coordTable[Id]['latSign']!=0:
                           coordTable[Id]['latitude']*=coordTable[Id]['latSign']
                  if coordTable[Id]['longSign']!=0:
                           coordTable[Id]['longitude']*=coordTable[Id]['longSign']   
         else:
                  interKey=lang+'_'+articleName
                  coordTable[Id]=dict(interwikiTable[interKey])
                  coordTable[Id]['Name']=articleName
                  coordTable[Id]['Lang']=lang


def printArticleGeo(Id,count):
         cDetail=coordTable[Id]
         print str(count)+'\t'+Id+'\t'+cDetail['extractedFrom']+'\t'+cDetail['Name']+'\t'+str(cDetail['latitude'])+'\t'+str(cDetail['longitude'])

#retrieves an articles revision id
def getId(fileIN):
         
         line = fileIN.readline()
         while re.search(r'<id>(.+?)</id>',line)==None:
                 line=fileIN.readline()
                
         while True:
                 line=fileIN.readline()
                 Id=re.search(r'<id>(.+?)</id>',line)
                 if Id!=None:
                         break
         return Id.group(1)

def incrementBracketCount(line):
         return len(re.findall("{{",line))-len(re.findall("}}",line))


#this function parses lines looking for coordinate name prefixes like lat,long and coor for english
# and calls the cooridnate search function to check whether any found prefixes are an actual match
# this allows increased code efficiency by only further analysing lines which have a potential prefix match rather than analysing all lines for coordinates
def parseLine(line,lang,label,Id,articleName,config):

         Result={}
         parseFlag='None'

         for prefix in prefixList[lang]:
                  pos=string.find(line,prefix)
                  if pos!=-1 and re.match(r'[a-zA-Z]',line[pos-1])==None:
                    
                           Result=coordinateSearch(line,prefix,lang)
                           if Result['flag']!='None':
                                    parseFlag=Result['flag']
                           del Result['flag']
                          
                           if len(Result)>0:
                                    if config=='complete' and parseFlag!=config:
                                             return parseFlag
                                    if Id not in coordTable or parseFlag=='complete':
                                             coordTable[Id]={'Name':articleName,'Lang':lang,'sourceLang':lang,'sourceId':Id,'extractedFrom':label,'latSign':0,'longSign':0}
                                  
                                    for i in Result:
                                             if i!='latSign' and i!='longSign' and i in coordTable[Id]:
                                                 coordTable[Id][i]+=Result[i]
                                             else:
                                                 coordTable[Id][i]=Result[i]
         return parseFlag

# function that processes a line with a candidate coordinate prefix
# checks whether the line actually contains a coordinate expression then calls the extractElements
# function to fetch the actual coordinates
def coordinateSearch(line,prefix,lang):

         Result={'flag':'None'}
         List=re.findall(prefix+r'[^\s]*?\s*[=\|]',line)
        
         for element in List:
                  word=re.search(trailingCh,element)
                 
                  element=string.replace(element,word.group(1),'')
    
                  if element in names[lang]:
   
                           pos=string.find(line,element)+len(element)
                           curResult=extractElements(line[pos:],element,lang)
                           Result['flag']=''

                           if curResult['flag']=='complete': #{{Coord template
                                    return curResult
                           
                           for i in curResult:
                                    if i in Result:
                                             Result[i]+=curResult[i]
                                    else:
                                             Result[i]=curResult[i]
                                    
         return Result

#functions that tunnels a coordinate line to extract a single element or a full geocode
def extractElements(line,coordElement,lang):
         
         Result={'flag':'coordFound'}
         Coords=retrieveCoordArray(line,lang)
         if len(Coords)==0:
                  return Result
         
         if coordType[coordElement]!='coordinatesTemplate':
                  Result=extractSingleElement(Coords,coordElement,line,lang)
                  
         else:
        
                  Result=extractFullGeo(Coords,line)
                  
         return Result


#function that caculates either latitude or longitude
# it take into account varying representations of each like lat=-10.5 or lat=10/30/N or lat = 10,30 N etc
def extractSingleElement(Coords,coordElement,line,lang):
    
         
         Result={'flag':'coordFound'}
         direction={'latitude':'latSign','latSign':'latSign','longitude':'longSign','longSign':'longSign'}
         
         coordName=names[lang][coordElement]
         cType=coordType[coordElement]
         
         for j in range (0,len(Coords)):
                  if Coords[j]['Type']!='number':
                           Result[ direction[cType] ]=normalizeEntry[ direction[cType] ](Coords[j]['Value'])
                  else:
                           if cType in Result:
                                    Result[cType]+=normalizeEntry[coordName](Coords[j]['Value'])/(60**j)
                           else:
                                    Result[cType]=normalizeEntry[coordName](Coords[j]['Value'])/(60**j)
   
         return Result

# function that calculates lat and long for coordinates provided in a format like this {coords|10|20|N|40|40|W}
def extractFullGeo(Coords,line):
    
         i=0
         power=0
         shift=0
         dim={1:'latitude',2:'longitude'}
         direction={1:'latSign',2:'longSign'}
         Result={'flag':'complete','latitude':0,'longitude':0,'latSign':0,'longSign':0}
         
         if len(Coords)%2==1:
                  return Result
                
         if len(Coords)==2:
                  if Coords[0]['Type']=='number' and Coords[1]['Type']=='number':
                           Result['latitude']+=Coords[0]['Value']
                           Result['longitude']+=Coords[1]['Value']
                  return Result
         
         for i in range(1,3):
                  for j in range(0,len(Coords)/2):
                           if Coords[j+shift]['Type']!='number':
                                    Result[direction[i]]=normalizeEntry[direction[i]](Coords[j+shift]['Value'])
                           else:
                                    Result[dim[i]]+=limit(Coords[j+shift]['Value'],60**(j))
                  shift+=len(Coords)/2
                  
         return Result

# parses a line of coordinates and  returns an array of magnitudes and directions of coordinates for the degree, minute and second levels
def retrieveCoordArray(line,lang):
    
         Coords=[]
         index=0
     
         line=string.replace(line,'&quot;','|')
         line=string.replace(line,'&amp;nbsp;','|')
         line=' '.join(string.split(line))+' '
      
         while True:
                  Match=re.match(formatLang[lang],line[index:])
                
                  if Match!=None:
                           element=Match.group(2)
                           if re.search(numberRegex,element)!=None:
                                    Coords.append({'Type':'number','Value':float(element)})
                           else:
                                    Coords.append({'Type':'direction','Value':str(element)})
                  else:
                           checkRangeCoordinates(line[index:],Coords)
                           break
                  if len(Coords)==8:
                           break
                  index+=len(Match.group(1))  
         
         return Coords
       
# this is done to collect coordinate sign expressions in certain misformatting cases like this latitude= 10 to 20 N rather tahn 10 N to 20 N
def checkRangeCoordinates(line,Coords):
         if re.match(rangeElement,line)!=None and len(Coords)>0:
                  if Coords[-1]['Type']!='direction':
                           direction=re.search(directionElement,line)
                           if direction!=None:
                                    Coords.append({'Type':'direction','Value':str(direction.group(1))})

# loading coordinate sign based on coordinate direction
def sign(direction):
         direction=str(direction)
         if direction in directionMap:
                  return directionMap[direction]
         return 1

# this function makes sure no coordinates are out of the lat/long degree ranges
def limit(number,scale):
         number=float(number)
         if scale==1:
                  return number
         if number > 60:
                  while number >1:
                         number/=10
                  return number
         return number/scale               

#this function loads the different coordinate name variations for each language from a text file
def populatecoordNamemap():
         fileIN = codecs.open('geoExtract/coordinateNames.txt','r','UTF-8')
         j=0
         line=fileIN.readline()
         while line:
                  lang=string.split(line)[0]
                  names[lang]={}
                  names[lang]=dict(names['en'])
                  for j in range (1,6):
                           TypeInfo=string.split(fileIN.readline())
                           Type=TypeInfo[0]
                           nVariations=int(TypeInfo[1])
                           for k in range(1,nVariations+1):
                                    Pair=string.split(fileIN.readline(),'\t')
                                    names[lang][Pair[0]]=Pair[1]
                                    coordType[Pair[0]]=Type
                  line=fileIN.readline()

def populatePrefixMap():
          # file which points from geoelement to keywords representing it(includes different languages)
         fileIN = codecs.open('geoExtract/prefixMap.txt','r','UTF-8')
         line=fileIN.readline()
         while line:
                  lang=string.split(line)[0]
                  prefixArray=string.split(fileIN.readline(),'\t')
                  prefixList[lang]=[]
                  for i in range(0,len(prefixArray)-1):
                           prefixList[lang].append(prefixArray[i])
                  line=fileIN.readline()
             

def getDB():
	try:
		connection = MySQLdb.connect(HOSTNAME, 
		USERNAME, PASSWORD, DATABASE, charset='utf8')

	except MySQLdb.Error, e:
		print "Error %d: %s" % (e.args[0], e.args[1])
		sys.exit()
        cursor=connection.cursor()
	return (connection,cursor)
        
def loadGeoArticles(con,cur):
         selectquery="select keyArticle from wikiproject.ArticleOct"
         cur.execute(selectquery)
         results = cur.fetchall()
         print str(len(results))
         for row in results:
                  geoArticles.add(str(row[0]))

def updateDB(Id,con,cur):
         
         
         lang=coordTable[Id]['Lang']
         lat=coordTable[Id]['latitude']
         longi=coordTable[Id]['longitude']
         source=coordTable[Id]['sourceLang']
         sourceId=coordTable[Id]['sourceId']
         key=lang+'_'+Id
         articleName=coordTable[Id]['Name'].replace("'","\\'")
                  
         query = u"INSERT ignore into wikiproject.ArticleOct set keyArticle='%s' ," % (key)
	 query+=" latitude='%s'" %  str(lat)
         query+=", longitude='%s'" % str(longi)
         query+=", language='%s'" %  lang
         query+=", geoSource='%s'" % source
         query+=", sourceIdRevision='%s'" % sourceId
         query+=", idRevision='%s'" % Id
         query+=", articleName='%s'" % articleName
         
	 cur.execute(query)

#updating table with coordinates obtained from left over articles through interwikis
def mergeInterwiki(con,cur):

         # articleSet[lang][article] contains article's RevId
         for lang in articleSet:
                  for article in articleSet[lang]:
                           name=article.keys()[0]
                           if (lang+'_'+name) in interwikiTable and (article[name] not in coordTable) and (lang+'_'+article[name] not in geoArticles):
                                    updateTable(article[name],lang,name)
                                    updateDB(article[name],con,cur)
         
def parseFiles():
         
         fileIN = codecs.open('geoExtract/dumpLinks.txt', 'r','UTF-8')
         populatecoordNamemap()
         populatePrefixMap()
         line = fileIN.readline()
         langs=['en','fr','sw','fa','ar','arz','he']
       
         con,cur=getDB()
         loadGeoArticles(con,cur)
         while line:
          
                  print line
                  word=string.split(line)
                  
                  if word[0]=='fr':
                           formatLang[word[0]]=formatFr
                  else:
                           formatLang[word[0]]=formatAll
                           
                  articleSet[word[0]]=[]
                  scan(word[0],word[1],con,cur)
                  print "Total length after processing "+word[0]+" = "+str(len(coordTable))
                  line = fileIN.readline()
     
         mergeInterwiki(con,cur)
         
       


    
if __name__ == '__main__':
    start=str(datetime.now())
    parseFiles()
    print "start:"+start
    print 'end:'+str(datetime.now() )

