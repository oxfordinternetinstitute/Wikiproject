#This is the code for parsing user pages for locations 
import sys, glob,os, codecs, string, datetime, random, MySQLdb, re
from xml.sax import saxutils, make_parser, handler
from xml.sax.handler import feature_namespaces, ContentHandler
from wpdbsettings import *
import cPickle as pickle

symbols=[':','{','}','[',']','*',"\\",'/',';','\n','#','!','=','&quot','.']
spacers=['[[','{{',']]','}}',',',"\"",'_','|','(',')']
langName={'en':'english','fr':'french','fa':'farsi','he':'hebrew','ar':'arabic','arz':'egyptian_arabic','sw':'swahili'}
languages=set(['eng','ara','fra','fas','heb'])
langConversion={'ar':'ara','arz':'ar','fr':'fra','he':'heb','fa':'fas','en':'eng'}

userData={}
countryMap={}
stopDict=set([])
demonymics={}
postfixes={}
prefixes={}
relationLabels={}
relationTypes=['lives','works','born']
relations={}


placeFound={'D':lambda x,Dict,lang,cur:fetchDB(x,lang,cur),'P':lambda x,Dict,lang,cur:fetchPICKLE(x,Dict)}
Modify={'D':lambda x:x.replace("'","\\'").lower().split(' '),'P':lambda x:x.lower().split(' ')}
reverseModify={'D':lambda x:x.replace("\\'","'"),'P':lambda x:x}

def loadCountries():
        isoMap=pickle.load(open("Authors/fips2iso.pkl",'r'))
        for i in isoMap:
            countryMap[isoMap[i][1].lower().strip()]=(i)

def loadDemonymics(Path):
        inFile=codecs.open(Path,'r','utf-8')
    
        count=0
        for line in inFile:
            
            terms=line.strip().split('\t')
            original=None
            names=terms[0].split(' or')
            persons=terms[1].split(' or')
            adjes=terms[2].split(' or')
            
            
            for name in names:
                name=name.strip().lower()
                if name in countryMap:
                    original=name
    
            if original==None:
                continue
            count+=1

            for name in names:
                name=name.strip().lower()
                if name!=original:
                    countryMap[name]=countryMap[original]
                
            if terms[1]!='None':
                for person in persons:
                    demonymics[person.lower().strip()]=original
                    
            if terms[2]!='None':
                for adj in adjes:
                    demonymics[adj.lower().strip()]=original

def loadDict(Dict,Path):
        print Path
        inFile=codecs.open(Path,'r','utf-8')
        for line in inFile:
            terms=line.strip().split('\t')
            print terms[0]+'\t'+terms[1]
            Dict[terms[0].strip()]=terms[1].strip()
            

def startDB():
	try:
		connection = MySQLdb.connect(HOSTNAME, 
		USERNAME, PASSWORD, DATABASE, charset='utf8')

	except MySQLdb.Error, e:
		print "Error %d: %s" % (e.args[0], e.args[1])
		sys.exit()
	cursor = connection.cursor()

	return (connection,cursor)


def closeDB(con,cur):
	cur.close()
	con.commit()
	con.close()

def loadStopDict(Path):
        
        inFile=codecs.open(Path,'r','utf-8')
        for line in inFile:
            terms=line.split('\t')
            stopDict.add(terms[0])
            
def loadCountryNames(cur):
        isoMap={}
        query="select fips,iso,name_0 from National"
        cur.execute(query)
        results=cur.fetchall()
        for row in results:
            if row[0]!=None and len(row[0])>0:
                isoMap[row[0]]=(row[1],unicode(row[2],'utf-8'))
        pickle.dump(isoMap,open("Authors/fips2iso.pkl",'w'))
        return isoMap

def loadGazeteers():
        sGaz={}
        nGaz={}
        FileInfo={}
        listInfo=open("Authors/gazeteers/lists.def",'r')
        lines=listInfo.readlines()
        for line in lines:
            print line
            terms=line.strip().split(' ')
            name=terms[0].split(':')[0]
            region=terms[1].split(':')[1]
            lang=terms[2].split(':')[1].lower()
            if lang=='unk':
                lang='eng'
            print name+'\t'+region+'\t'+lang
            print ''

            FileInfo[name]={}
            FileInfo[name]['lang']=lang
            FileInfo[name]['region']=region
        
        print ''
        print ''
        count=0
        names=0
        userList = glob.glob("Authors/gazeteers/*.txt")
        print len(userList)
        for filePath in userList:
            fileName=filePath.split('/')[-1]
            lang=FileInfo[fileName]['lang']
            region=FileInfo[fileName]['region']
            
            if lang not in languages:
                continue
            inFile=codecs.open(filePath,'r','utf-8')
            count+=1
            print "Counts:"+str(count)+'\t'+str(len(userList))
            print "Processed Places:"+str(names)
            for line in inFile:
                names+=1
                placeName=line.strip().lower()
                if lang not in sGaz:
                    sGaz[lang]={}
                if placeName not in sGaz[lang]:
                    sGaz[lang][placeName]=set([])
                sGaz[lang][placeName].add(region)
        pickle.dump(sGaz,open("Authors/subGazeteer2.pkl",'w'))
        return sGaz,nGaz

def fetchDB(x,lang,cur):
        if x in countryMap:
            return True,'',countryMap[x]
        query="select regions,countries from Gazeteer_%s where placeName='%s'"%(langConversion[lang],x)
        cur.execute(query)
        results=cur.fetchall()
        if len(results)>0:
            return True,results[0][0],results[0][1]
        return False,'',''
    

def fetchPICKLE(x,Dict):
        if x in countryMap:
            return True,'',countryMap[x]
        if x in Dict:
            return True,regionsString(Dict[x]),countryString(Dict[x])
        return False,'',''

def regionString(regionSet):                 
        rString=''
        count=0
        for r in regionSet:
            if count!=0:
                rString+=","
            rString+=r
            count+=1
        return rString
    
def countryString(regionSet):
        nations=set([])
        for r in regionSet:
            nations.add(str(r[0:2]))

        count=0
        countryString=''

        for n in nations:
            if count!=0:
                countryString+=","
            countryString+=n
            count+=1
                        
        return countryString   

def extractText(Path,fetchType):
        inFile=codecs.open(Path,'r','UTF-8')
        text=''
        Fulltext=''
        lines=inFile.readlines()
        for line in lines:
            text+=line
            Fulltext+=line
        #print text
        
        for spacer in spacers:
            text=text.replace(spacer,' ')
        for symbol in symbols:
            text=text.replace(symbol,' / ')

        #print "Before:"
        #print text.lower().strip()
        #print ''
        words=Modify[fetchType](text)
        
        limit=0
        wordChunks=[]
        wordChunks.append([])
      
        #print "After:"
        for i in range(0,len(words)):
            words[i]=words[i].strip()
            if len(words[i])!=0:
                if words[i]=='/':
                    if len(wordChunks[-1])!=0:
                        wordChunks.append([])
                    continue
                wordChunks[-1].append(words[i])
        if len(wordChunks[-1])==0:
            wordChunks.pop()
        #print wordChunks
        return wordChunks,Fulltext
        
def processUsers(lang,sGaz,isoMap,userList,cur,fetchType):
    

        userData[lang]={}
        relations[lang]={}
        print len(userList)
        count=0
        ParsedTags=loadParsedTags(cur)
        for filePath in userList:
                
                count+=1
                print "Count:"+str(count)
                print filePath
                fileName=filePath.split('/')[-1]
                authorName=fileName.split('_')[-1][:-4]
                ID=fileName.split('_')[0]+'_'+fileName.split('_')[1]
                print authorName+'\t'+ID
                if ID in ParsedTags:
                    continue

                relations[lang][ID]={}
  
                wordChunks,Fulltext=extractText(filePath,fetchType)
                userData[lang][ID]=countPlaces(wordChunks,lang,sGaz['eng'],cur,fetchType)
                printUserData(userData[lang][ID])
                for i in range(0,5):
                    print ''
                relations[lang][ID],isTagged=getVerdict(userData[lang][ID])
                exportVerdict(cur,ID,relations[lang][ID],isTagged)

                #x=raw_input("Waiting for next user")
                for i in range(0,30):
                    print ''
                if count<500 and isTagged==1:
                    printSample(relations[lang][ID],userData[lang][ID],authorName,Fulltext)

        
        
def countPlaces(wordChunks,lang,Dict,cur,fetchType):
    
        userData={}
        for chunk in wordChunks:
            
            chunkLabels=set([])
            weakResults=set([])
            for i in range(0, len(chunk)):
                candidates=[]
                placeFlag=False
                dynFlag=False
                
                if i<=len(chunk)-3:
                    candidates.append((chunk[i]+' '+chunk[i+1]+' '+chunk[i+2],i,i+2))
                    candidates.append((chunk[i+1]+' '+chunk[i+2],i+1,i+2))
                if i==0 and len(chunk)>1:
                    candidates.append((chunk[i]+' '+chunk[i+1],i,i+1))
                
                candidates.append((chunk[i],i,i))
               
                    
                for j in range(0,len(candidates)):
                        x=candidates[j][0]
                        low=candidates[j][1]
                        high=candidates[j][2]
                        if x in relationLabels:
                            chunkLabels.add(relationLabels[x])
                        if placeFlag:# to make sure los wont be added if los angeles was already found
                            continue
                        
                        
                        if reverseModify[fetchType](x) in stopDict:
                            continue
                        
                        if x in demonymics:
                            print x
                            x=demonymics[x]
                            dynFlag=True
                            
                        placeFlag,regions,countries= placeFound[fetchType](x,Dict,lang,cur)#needs modification to check for coutnries and demonyms as well

                        if placeFlag:
                            print str(chunk)
                            print "Gram:"+x
    
                            if x not in userData:
                                userData[x]={}
                                userData[x]['counts']=0
                                userData[x]['geoData']=(regions,countries)
                                userData[x]['weak']=set([])
                                userData[x]['strong']=set([])
                            
                            pre=[]
                            if low>1:
                                pre.append(reverseModify[fetchType](chunk[low-2]+' '+chunk[low-1]))
                            if low >0:
                        
                                pre.append(reverseModify[fetchType](chunk[low-1]))
                                print pre
                                for i in range(0,len(pre)):
                                    if pre[i] in prefixes:
                                        userData[x]['strong'].add(prefixes[pre[i]])
                                        print "Prefix:"+pre[i]
    
                            
                            if dynFlag:
                                if high<len(chunk)-1:
                                    post=chunk[high+1]
                                    if post in postfixes:
                                        print "Nationality Tag:"+x
                                        userData[x]['strong'].add(postfixes[post])
                            else:
                                weakResults.add(x) # because including demonymics in weak results is very erroneous
                            userData[x]['counts']+=1
    
            if len(weakResults)>0:
                print "ChunkLabels:"+str(chunkLabels)
                print "weakResults:"+str(weakResults)
            for i in weakResults:
                userData[i]['weak']=userData[i]['weak'].union(chunkLabels)#.difference(userData[i]['strong'])
                
        return userData

def printSample(relation,userData,authorName,Fulltext):
    
        outFile=codecs.open("Authors/SampleTags/"+authorName+"_UserPage.txt",'w','utf-8')
        outFile.write(Fulltext)
        outFile.close()
        
        relationFile=codecs.open("Authors/SampleTags/"+authorName+"_extractedRelations.txt",'w','utf-8')
        lives,lConf,works,wConf,born,bConf,VWeakGS=extractISOs(relation,1)
        
        
        printUserDataOut(userData,relationFile)
        
        for i in range(0,4):
            relationFile.write('\n')
        relationFile.write("Output"+'\n')
        relationFile.write("\tLives: "+lives+'\n')
        relationFile.write("\tLives Confidence: "+lConf+'\n')
        relationFile.write("\tWorks: "+works+'\n')
        relationFile.write("\tWorks Confidence: "+wConf+'\n')
        relationFile.write("\tBorn/Nationality: "+born+'\n')
        relationFile.write("\tBorn Confidence: "+bConf+'\n')
        relationFile.write("\tVery Weak General Guess: "+VWeakGS+'\n')
        relationFile.close()


def printUserDataOut(userData,outFile):
        outFile.write('Places\n')
        for i in userData:
            outFile.write('\n')
            outFile.write("\tPlace/Identity:"+i+'\t'+str( userData[i]['counts'])+'\n')
            outFile.write("\tstructuredRelations:"+str( userData[i]['strong'])+'\n')
            outFile.write("\tunstructuredRelations:"+str( userData[i]['weak'])+'\n')
            outFile.write("\tRegions(fips):"+ userData[i]['geoData'][0]+'\n')
            outFile.write("\tCountries(fips):"+ userData[i]['geoData'][1]+'\n')
            print ''
            
def printUserData(userData):
        for i in userData:
            
            print "Place:"+i+'\t'+str( userData[i]['counts'])
            print "strongRelations:"+str( userData[i]['strong'])
            print "weakRelations:"+str( userData[i]['weak'])
            print "Regions:"+ userData[i]['geoData'][0]
            print "Countries:"+ userData[i]['geoData'][1]
            print ''
    
def getVerdict(userData):
        
        isTagged=0
        relation={}
        weight={'strong':{},'weak':{},'general':{}}
        for r in relationTypes:
            weight['strong'][r]={}
            weight['weak'][r]={}
            countStrong=0
            countWeak=0
            TieWeak=False
            TieStrong=False
            for place in userData:
                countries=userData[place]['geoData'][1].strip().split(',')
                strongFlag=False
                weakFlag=False
                TieFlag=False
                if r in userData[place]['strong']:
                    strongFlag=True
                if r in userData[place]['weak']:
                    weakFlag=True
                    
                
                for c in countries:
                    if c not in weight['strong'][r]:
                        weight['strong'][r][c]=0
                        weight['weak'][r][c]=0
                        weight['general'][c]=0

                    if strongFlag:
                        countStrong+=1
                        weight['strong'][r][c]+=userData[place]['counts']#
                    if weakFlag:
                        countWeak+=1
                        weight['weak'][r][c]+=userData[place]['counts']#make this a weighted sum
                   
                    weight['general'][c]+=userData[place]['counts']
                
     
            if countStrong>0:
                print r+'\t'+"StrongTest"
                maxStrong,TieStrong=getMax(weight['strong'][r])
                if TieStrong:
                    print "StrongTie"
                    maxStrong,TieStrong=breakTie(weight['weak'][r],maxStrong)
                    if TieStrong:
                        print "AnotherStrongTie"
                        maxStrong,TieStrong=breakTie(weight['general'],maxStrong)
                relation[r]=(maxStrong,'Strong')
                isTagged=1
            elif countWeak>0:
                print r+'\t'+"WeakTest"
                maxWeak,TieWeak=getMax(weight['weak'][r])
                if TieWeak:
                        print "WeakTie"
                        maxWeak,TieWeak=breakTie(weight['general'],maxWeak)
                relation[r]=(maxWeak,'Weak')
                isTagged=1
        
        if len(relation)==0:
            print "VeryWeak"
            matches,Flag=getMax(weight['general'])
            relation['general']=(matches,'')
            if len(matches)>0:
                isTagged=1

        else:
            relation['general']=(set([]),'')
        for r in relationTypes:
            if r not in relation:
                relation[r]=(set([]),'')
        for r in relation:
            print r+'\t'+str(relation[r][0])+'\t'+str(relation[r][1])
        return relation,isTagged
    

def extractISOs(relation,index):
        string={}
        for r in relation:
            string[r]=""
            for c in relation[r][0]:
                if c in isoMap:
                    string[r]+=","+isoMap[c][index]
            if len(string[r])>0:
                string[r]=string[r][1:]
                string[r]=string[r].replace("'","\\'")
        
        lives,lConf=string['lives'],relation['lives'][1]
        works,wConf=string['works'],relation['works'][1]
        born,bConf=string['born'],relation['born'][1]
        VWeakGS=string['general']
        return lives,lConf,works,wConf,born,bConf,VWeakGS
    
def exportVerdict(cur,ID,relation,isTagged):
    
    
        lives,lConf,works,wConf,born,bConf,VWeakGS=extractISOs(relation,0)
        query="UPDATE AuthorAggregates set lives='%s',works='%s',bornnat='%s',liveConf='%s',workConf='%s',bornConf='%s',VWeakGS='%s',parsed=1,isTagged=%s " %(lives,works,born,lConf,wConf,bConf,VWeakGS,isTagged)
        query+="where idAuthor='%s'"%(ID)
        cur.execute(query)

def loadParsedTags(cur):
        tagsParsed=set([])
        query="select idAuthor from AuthorAggregates where parsed=1"
        cur.execute(query)
        results=cur.fetchall()
        for row in results:
            tagsParsed.add(row[0])
        return tagsParsed

def getMax(matches):
        
        keys=sorted(matches,key=lambda match:matches[match]*-1)
        Maxes=set([])
        TieFlag=False
        maxVal=0
        count=0
        for key in keys:
            val=matches[key]
            if count==0:
                maxVal=val
            if val==maxVal:
                Maxes.add(key)
            print key+'\t'+str(val)
            count+=1
        if len(Maxes)>1:
            TieFlag=True
        return Maxes,TieFlag
    
def breakTie(matches,Ties):
        
        keys=matches.keys()
        for i in keys:
            if i not in Ties:
                matches.pop(i)
        return getMax(matches)
        
def import2DB(sGaz,cur):
        
        for lang in sGaz:
                for NAME in sGaz[lang]:
                    tempName=NAME.replace("'","\\'")
                    query="INSERT into Gazeteer_%s set placeName='%s',subNational=1"%(lang,tempName)
                   
                    regionString=''
                    nations=set([])
                    count=0
                    for r in sGaz[lang][NAME]:
                        nations.add(str(r[0:2]))
                        if count!=0:
                            regionString+=","
                        regionString+=r
                        count+=1
                    
                    count=0
                    countryString=''

                    for n in nations:
                        if count!=0:
                            countryString+=","
                        countryString+=n
                        count+=1
                        
                    query+=",regions='%s',countries='%s'"%(regionString,countryString)
                    cur.execute(query)
                    
  
  
def tagUsers(userData):# for dumping verdicts
        verdicts={}
        for lang in userData:
            verdicts[lang]={}
            for ID in userData[lang]:
                printUserData(userData[lang][ID])
                verdicts[lang][ID]=getVerdict(userData[lang][ID])
            
        return verdicts                  
def printLocations(infoDict):# modify this to print without using grams as they were removed from dictionary
        names={}
        for gram in infoDict['en']:
            names[gram]={}
            
            for name in infoDict['en'][gram][ID]:
                    if name not in names[gram]:
                        names[gram][name]=0
                    names[gram][name]+=1
            outFile=codecs.open("Authors/matching_english_"+str(gram)+"_gram.txt",'w','utf-8')
            keys=sorted(names[gram],key=lambda x:names[gram][x]*-1)
            for name in keys:
                outFile.write(name+'\t'+str(names[gram][name])+'\n')
            outFile.close()

                    
if __name__ == '__main__':
        sGaz={}
        sGaz['eng']={}
	start=datetime.datetime.now()
        con,cur=startDB()
        userList={}
        if len(sys.argv)>2:
            if sys.argv[2]=='L':
                isoMap=loadCountryNames(cur)
                sGaz,nGaz=loadGazeteers()
            elif sys.argv[2]=='I':
                #sGaz=pickle.load(open("Authors/subGazeteer.pkl",'r'))
                #nGaz=pickle.load(open("Authors/nationalGazeteer.pkl",'r'))
                #import2DB(sGaz,cur)
                elapsed=datetime.datetime.now()-start
                print elapsed
            elif sys.argv[2]=='U':
                for lang in langName:
                    userList[lang] = glob.glob("Authors/"+langName[lang]+"2/*.txt")
                pickle.dump(userList,open("Authors/userList.pkl",'w'))
            else:
                userList=pickle.load(open("Authors/userList.pkl",'r'))
        else:
            userList=pickle.load(open("Authors/userList.pkl",'r'))
        fetchType=sys.argv[1]
        
        loadStopDict("Authors/stopDict.txt")
        loadCountries()
        loadDemonymics("Authors/demonymics.txt")
        loadDict(postfixes,"Authors/postfixes.txt")
        loadDict(prefixes,"Authors/prefixes.txt")
        loadDict(relationLabels,"Authors/placeRelations.txt")
        
        isoMap=pickle.load(open("Authors/fips2iso.pkl",'r'))
        
        if sys.argv[1]=='V':
            userData=pickle.load(open("Authors/locationData.pkl",'r'))
            relations=tagUsers(userData)
            pickle.dump(relations,open("Authors/finalTags.pkl",'w'))
        else:
            for lang in langName:
                if lang =='en':
                    processUsers(lang,sGaz,isoMap,userList[lang],cur,fetchType)
  
            pickle.dump(userData,open("Authors/locationData.pkl",'w'))
            pickle.dump(relations,open("Authors/finalTags.pkl",'w'))
  
        
        
        
