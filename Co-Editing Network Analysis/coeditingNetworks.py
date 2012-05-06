import glob,linecache,sys, os, codecs, string, datetime, random, re
from xml.sax import saxutils, make_parser, handler
from xml.sax.handler import feature_namespaces, ContentHandler
from datetime import datetime,time,date
import copy
import cPickle as pickle
import itertools
import csv, glob, cPickle as pickle, datetime
from igraph import *
import networkx as nx
import community
from wpdbsettings import *
import MySQLdb
import random
import math
import numpy
from scipy.stats.stats import pearsonr
articleDict,countryDict,nodeSizeDict=pickle.load(open("Networks/PKLs/attributeDicts.pkl",'r'))
langs=['en','fr','ar','fa','he','sw','arz']
articleDist={}
countryDist={}

global Type
global weightFlag

nodeDict={'igraph':lambda G,node,name,nodeType: G.addNodeIgraph(node,name,nodeType),'networkx':lambda G,node,name,nodeType: G.addNodeNetworkx(node,name,nodeType)}
edgeDict={'igraph':lambda G,edgeList:G.addEdgesIgraph(edgeList),'networkx':lambda G,edgeList: G.addEdgesNetworkx(edgeList)}
communityDict={'igraph':lambda G:G.communityIgraph() ,'networkx':lambda G:G.Louvain()}
componentDict={'igraph':lambda G:G.getLargestComponentIgraph() ,'networkx':lambda G:G.getLargestComponentNetworkx()}

def closeDB(con,cur):
	cur.close()
	con.commit()
	con.close()


class myDendo:
	def __init__ (self):
		self.byCom={}
		self.byNode={}
		self.modularity=None
		self.communityGraph=None
		self.originalDendo=None
		
	def loadFromNetworkX(self,lastState):
		self.byNode,self.originalDendo,self.communityGraph,self.modularity=lastState
		self.byCom={}
		for i in self.byNode:
			value=self.byNode[i]
			if value not in self.byCom:
				self.byCom[value]=set([])
			self.byCom[value].add(i)	

	def loadFromIgraph(self,communities):
		self.modularity=communities.modularity
		members=communities.membership
		for i in range(len(members)):
			self.byNode[i]=members[i]
			if members[i] not in self.byCom:
				self.byCom[members[i]]=set([])
			self.byCom[members[i]].add(i)
		del members

class wikiGraph:
	def __init__ (self,graphType):
		
		self.Type=graphType
		if self.Type=='igraph':
			self.graph = Graph(0)
			self.vertexlist = {'author':{},'article':{}}
		else:
			self.graph=nx.Graph()
		
		self.communities=None
		self.largestCommunity=None
		self.largestComponent=None
		self.cardinality=None
		self.proportionV=None
		self.proportionE=None
		self.spreads={}
		self.comDist={}
		self.comCount={}
		self.attDists={}
		self.correlationDict={}
		self.blockModel=None
		
	def nEdges(self):
		if self.Type=='igraph':
			return self.graph.ecount()
		return nx.number_of_edges(self.graph)
	
	def nVertices(self):
		if self.Type=='igraph':
			return self.graph.vcount()
		return nx.number_of_nodes(self.graph)
			
	def addNode(self,node,Name,nodeType=False):
		return nodeDict[self.Type](self,node,Name,nodeType)
	
	def addNodeNetworkx(self,node,nodeName,nodeType=False):
		G=self.graph
		if node not in G.node:
			if nodeType:
				G.add_node(node,name=nodeName,type=nodeType)	
			else:
				G.add_node(node,name=nodeName)
		return node
		
	def addNodeIgraph(self,node,Name,nodeType):
	
		G = self.graph
	
		if node in self.vertexlist[nodeType]:
			return self.vertexlist[nodeType][node]
		else:
			index = G.vcount()
			G.add_vertices(1)
			self.vertexlist[nodeType][node] = index
			G.vs[index]["Id"] = node
			G.vs[index]["Name"] = Name
			#G.vs[index]["Type"] = Type	
			return index
		
	def addEdges(self,edgeList):
		edgeDict[self.Type](self,edgeList)
	
	def addEdgesNetworkx(self,edgeList):
		if len(edgeList[0])==3:	
			self.graph.add_weighted_edges_from(edgeList)
		else:
			self.graph.add_edges_from(edgeList)
			
	def addEdgesIgraph(self,edgeList):
		self.graph.add_edges(edgeList)
		
	def areConnectedIgraph(self,node1,node2):
		return self.graph.are_connected(node1,node2)
	
	def areConnectedNetworkx(self,node1,node2):
		return node1 in self.graph.edge[node2]
	
	def getCommunities(self):
		self.communities=communityDict[self.Type](self)
		self.getMaxCommunity()
		self.computeCommunityDistribution()
		self.computeCommunityCardinality()
		
	def Louvain(self):
		lastState=community.best_partition(self.graph)
		dendo=myDendo()
		dendo.loadFromNetworkX(lastState)
		return dendo
		
	def communityIgraph(self):
		tempCommunity=self.graph.community_fastgreedy()
		dendo=myDendo()
		dendo.loadFromIgraph(tempCommunity)
		return dendo
	
	
	def getSuperCom(self):
		graph=self.communities.communityGraph
		graph=self.reformat2Igraph(graph)
		dendogram=graph.community_edge_betweenness()
		print dendogram.merges
		print dendogram.summary()
		self.communities.mergeSizeDict=self.extractMergeTable(dendogram.merges,nx.number_of_nodes(self.communities.communityGraph))
		
	def extractMergeTable(self,merges,nodes):
		Sets={}
		mergeSizeDict={}
		for i in range(nodes):
			Sets[i]=set([i])
		n=nodes
	
		for i in merges:
			a=i[0]
			b=i[1]
			Sets[n]=(Sets[a].union(Sets[b]))
			n+=1
		print Sets
		for i in range(nodes,len(Sets)):
			for pair in itertools.combinations(Sets[i],2):
				if pair not in mergeSizeDict:
					mergeSizeDict[pair]=len(Sets[i])
		print ''
		print mergeSizeDict
		return mergeSizeDict
		
		
	def reformat2Igraph(self,graph):
		print nx.number_of_nodes(graph)
		print nx.number_of_edges(graph)
		G=Graph(0)
		for i in range(nx.number_of_nodes(graph)):
			G.add_vertices(1)
		for i in graph.edge:
			for j in graph.edge[i]:
				if i<=j:
					G.add_edges([(i,j)])
		return G
	
	def getModularity(self):
		return self.communities.modularity
		
	def getMaxCommunity(self):
		comDict=self.communities.byCom
		max=0
		for i in comDict:                        
			if len(comDict[i])>max:
				max=len(comDict[i])
		self.largestCommunity=max,i	
		
	def computeCommunityDistribution(self):
		comDict=self.communities.byCom
		sum=float(0)
		self.comCount={}
		self.comDist={}
		for i in comDict:
			self.comCount[i]=float(0)
			for j in comDict[i]:
				
				if j in nodeSizeDict:
					value=float(nodeSizeDict[j])
					self.comCount[i]+=value
					sum+=value	
	
		for i in self.comCount:
			self.comDist[i]=self.comCount[i]/sum
	
	def computeCommunityCardinality(self):
		largestComponent=nx.connected_component_subgraphs(self.graph)[0]
		self.proportionV=nx.number_of_nodes(largestComponent)/float(self.nVertices())
		self.proportionE=nx.number_of_edges(largestComponent)/float(self.nEdges())
		count=0
		comDict=self.communities.byCom
		for com in comDict:
			for i in comDict[com]:
				if i in largestComponent.node:
					count+=1
				else:
					print "Isolated com:"+str(com)
				
				break
				
		self.cardinality=count
		print "proportionV:"+str(self.proportionV)
		print "proportionE:"+str(self.proportionE)
		del largestComponent
		
		
	def computeAttributeDistributions(self,name,attributeDict):#for all values in an attribute dictionary
		nodeComDict=self.communities.byNode
		self.attDists[name]={}
	
		for i in attributeDict:#(i being country or article value)
			self.attDists[name][i]={}
			sum=float(0)
		
			for j in attributeDict[i]:#j being  node having attribute
				if j not in nodeComDict:
					continue
				value=attributeDict[i][j]#count of attribute in node
				jCom=nodeComDict[j]
				if jCom not in self.attDists[name][i]:
					self.attDists[name][i][jCom]=float(0)
				self.attDists[name][i][jCom]+=float(value)
				sum+=value
		
			if sum>0:
				for k in self.communities.byCom:
					if k not in self.attDists[name][i]:
						self.attDists[name][i][k]=float(0)
					self.attDists[name][i][k]/=sum
			else:
				del self.attDists[name][i]
		
	def computeSpreads(self,Dicts,lang):
		for i in Dicts:
				self.computeSpreads4Dict(i,Dicts[i],lang)
				print i+'\tspreads:'+str(len(self.spreads[i]))
				
	def computeSpreads4Dict(self,name,attributeDict,lang):
		self.spreads[name]={}
		self.computeAttributeDistributions(name,attributeDict)
		#self.getBlockModel()
		for i in self.attDists[name]:
				self.spreads[name][i]=vectorSpread(self.attDists[name][i],self.comDist)
				
		
	def getBlockModel(self):
		G=nx.Graph()
		for i in self.attDists:
			for j in self.attDists:
				if i<j:
					G.add_edges_from([(i,j,vectorSpread(self.attDists[i],self.attDists[j]))])


	def computeSpreadCorrelation(self,prevSpreads,prevDist,type):
		
		if prevSpreads==False:
			return
		listA=[]
		listB=[]
		if type=='article':
			self.spreadDist={}
		factor=40
		
		self.spreadDist[type],sum=self.getSpreadDistribution(factor)
		prevDist[type],sum=self.getDistribution(prevSpreads[type],factor)
		for i in prevDist[type]:
			prevDist[type][i]/=float(sum)
		values=prevDist[type].values()
		keys=prevDist[type].keys()
		for i in self.spreads[type]:
			if i in prevSpreads[type]:
				listA.append(self.spreads[type][i])
				listB.append(prevSpreads[type][i])
			else:
				listA.append(self.spreads[type][i])
	
				sampled=self.sample(values)
				for i in range(len(sampled[0])):
					if sampled[0][i]==1:
						sIndex=i
			 	listB.append(keys[sIndex]+numpy.random.uniform(0,(1/float(factor))))
				
		self.correlationDict[type]=pearsonr(listA,listB)
		print self.correlationDict[type][0]
		return self.correlationDict[type][0]
	
	def getSpreadDistribution(self,factor,type):
		counts={}
		sum=0
		
		for i in self.spreads[type]:
		
			pos=int(self.spreads[type][i]*factor)
			fl=float(pos)*(1/float(factor))
			fl+=1/float(2*factor)
			fl=round(fl,4)
			if fl not in counts:
				counts[fl]=0
			counts[fl]+=1
			sum+=1
		keys=sorted(counts,key=lambda x:x)
		i=0.0
		#for key in keys:
		#	print str(key)+':\t'+str(counts[key])
		
		for c in range(0,factor):
			
			i=round(c*(1/float(factor))+(1/float(2*factor)),4)
		
			if i not in counts:
				counts[i]=0
		#	print i
		keys=sorted(counts,key=lambda x:x)
		for key in keys:
			counts[key]/=float(sum)
			print str(key)+':\t'+str(counts[key])
		self.spreadDist[type]=counts
		return counts,sum
		
	def sample(self,distribution):	
		return numpy.random.multinomial(1,distribution,1)#multinomial sampling
		
	def computeCorrelations(self,prevCommunities,type,type2=False):
		if prevCommunities:
			name=type
			if type2=='hierarchical':
				name=type2+'_'+type
			self.correlationDict[name]=compareEfficient(prevCommunities,self.communities,type,type2)
			print "LatestEdges:"+str(self.nedges)+"\tLatestNodes:"+str(self.nvertices)+'\t'+"BiCorrelation "+name+":"+str(self.correlationDict[name][0])+'\t'+"ForwardCorr:"+str(self.correlationDict[name][1])+'\t'+"BackwardCorr:"+str(self.correlationDict[name][2])
			
	def optimizeCountOrder(self,currentCounts,optimalDist):
		# This is done to get maximumum distribution /needs fixing
		optCounts={}
		keysOptimal=sorted(optimalDist,key=lambda x:optimalDist[x]*-1)#ordered by  desc distribution
		keysCounts=sorted(currentCounts,key=lambda x:currentCounts[x]*-1)#ordered by desc counts
		
		for i in range(len(keysOptimal)):
			keyOpt=keysOptimal[i]
			keyCount=keysCounts[i]
			optCounts[keyOpt]=currentCounts[keyCount]
		
		return optCounts
		
	def computeMultinomial(self,currentCounts,optCounts,optimalDist):
		upDict={}
		downDict={}
		print "currentCounts:"+str(currentCounts)
		print "OptCounts:"+str(optCounts)
		print "OptimalDist:"+str(optimalDist)
		for i in optCounts:
			count=int(optCounts[i])
			for j in range(1,count+1):
				if j not in upDict:
					upDict[j]=0
				upDict[j]+=1
		
		for i in currentCounts:
			count=int(currentCounts[i])
			for j in range(1,count+1):
				if j not in downDict:
					downDict[j]=0
				downDict[j]+=1	
		probCounts={}	
		for i in optimalDist:
			prob=optimalDist[i]
			if prob not in probCounts:
				probCounts[prob]=0
			probCounts[prob]+=int(currentCounts[i]-optCounts[i])

		for i in probCounts:
			v=probCounts[i]
			if v<0:
				downDict[i]=abs(v)
			else:
				upDict[i]=v
	        
		return self.listMultiplication(upDict,downDict)
	
	def listMultiplication(self,up,down):
		upKeys=up.keys()
		downKeys=down.keys()
		upList=[]
		downList=[]
		print "Up"+str(up)
		print ""
		for i in upKeys:
			if i in down:
				upT=up[i]
				downT=down[i]
				down[i]-=min(upT,downT)
				up[i]-=min(upT,downT)
				for index in range(down[i]):
					downList.append(i)
				for index in range(up[i]):
					upList.append(i)
			else:
				for index in range(up[i]):
					upList.append(i)
		for i in downKeys:
			if i not in up:
				for index in range(down[i]):
					downList.append(i)
			
		remUplist=[]
		remDownlist=[]	
		upList=sorted(upList)
		downList=sorted(downList)		
		if len(upList)>len(downList):
			remUplist=upList[len(downList):]
			upList=upList[:len(downList)]
		elif len(downList)>len(upList):
			remDownlist=downList[len(upList):]
			downList=downList[:len(upList)]
			print "REM:"+str(remDownlist)

		result=float(1)
	
		for i in range(len(upList)):
			result*=(float(upList[i])/float(downList[i]))
		for i in remUplist:
			result*=i
		for i in remDownlist:
			result/=i
		return result


def vectorSpread(distA,comDist):
	squaredDistance=float(0)
	for i in distA:
		squaredDistance=math.pow(distA[i]-comDist,2)
	totalDistance=math.sqrt(squaredDistance)
	maxDistance=getMaxDistance(comDist)
	spread=1- (totalDistance/maxDistance)

def getMaxDistance(vectorDict):
	max=float(0)
	smallestDimension=getSmallestDimension(vectorDict)
	for i,value in vectorDict:
		if i==smallestDimension:
			max+=math.pow(1-value,2)
		else:
			max+=math.pow(value,2)
	math.sqrt(max)
	return math.sqrt(max)

def getSmallestDimension(vectorDict):
	keys=sorted(vectorDict,key=lambda x:vectorDict[x])
	return keys[0]


def vectorSpread(distA,distB):
	listA=[]
	listB=[]
	#print distA
	#print distB
	for i in distA:
		listA.append(distA[i])
		listB.append(distB[i])
	#listA=normalize(listA)
	#listB=normalize(listB)	
	#print listA
	#print listB
	diff=vectorDistance(listA,listB)
	#print diff
	max=getMaxDiff(listB)
	#print max
	return	1-(diff/max)
	
def vectorLength(list):
	sum=float(0)
	for i in list:
		sum+=math.pow(i,2)
	sum=math.pow(sum,0.5)
	return sum
	
def vectorDistance(listA,listB):
	dist=float(0)
	for i in range(len(listA)):
		dist+=math.pow(listA[i]-listB[i],2)
	return math.pow(dist,0.5)

def getMinPos(list):
	min=10
	for i in range(len(list)):
		if list[i]<min:
			min=list[i]
			minPos=i
	return minPos
		
def getMaxDiff(list):
	max=float(0)
	minPos=getMinPos(list)
	for i in range(len(list)):
		if i==minPos:
			max+=math.pow(1-list[i],2)
		else:
			max+=math.pow(list[i],2)
	max=math.pow(max,0.5)
	return max
			
def normalize(list):
	length=vectorLength(list)
	factor=1/length
	for i in range(len(list)):
		list[i]*=factor
	return list

		
				
def createBasicNetwork(con,cur,lang):
	
	authorDict={}
	articleDict={}
        authorNames={}
	weightDict={}
        if Type=='with':
            selectquery="select keyArticle,idAuthor,articleName,authorName,revisionCount from AuthorList where language='%s' and isBot=0"%(lang)
        else:
            selectquery="select keyArticle,idAuthor,articleName,authorName,revisionCount from AuthorList where language='%s' and locate('_0',idAuthor)=0 and isBot=0"%(lang)
        cur.execute(selectquery)
        results=cur.fetchall()
        
        for row in results:
		idRevision=str(row[0])
		idAuthor=str(row[1])
		revisionCount=float(row[4])
		if idAuthor not in authorDict:
		    authorDict[idAuthor]=set([])
		    weightDict[idAuthor]={}
                    authorNames[idAuthor]=unicode(row[3],"utf-8")
		authorDict[idAuthor].add(idRevision)
                weightDict[idAuthor][idRevision]=revisionCount
		if idRevision not in articleDict:
		    articleDict[idRevision]=set([])
		articleDict[idRevision].add(idAuthor)
	hashNetwork=authorDict,articleDict,weightDict
	return hashNetwork,authorNames

def generateUniModal(lang,hashNetwork):
        print "Generating UniModal"
        authorDict,articleDict,weightDict=hashNetwork
        Path="Networks/Sorting/"+lang+"_"+Type+"_AllEdges"
        outFile=open(Path,'w')
	counts={}
        counter=0

	for au in authorDict:
	
		processedAuthors=set([])
		articles=authorDict[au]
		for ar in articles:
			adj_authors=articleDict[ar]
			for aj in adj_authors:
				if au<aj and aj not in processedAuthors:
					processedAuthors.add(aj)
					aj_articles=authorDict[aj]
					sum=float(0)
					overlap=articles.intersection(aj_articles)
					for i in overlap:
						n=len(articleDict[i])
						sum+=((weightDict[au][i])/(n-1))
						sum+=((weightDict[aj][i])/(n-1))
				
					weight=round(sum,3)
					outFile.write(str(au)+'\t'+str(aj)+'\t'+str(weight)+'\n')
                        
                                        if weight not in counts:
                                            counts[weight]=0
                                        counts[weight]+=1
                                        if counter%100000==0:
                                            print "EdgesSaved:"+str(counter)
                                            print str(au)+'\t'+str(aj)+'\t'+str(weight)
                                        counter+=1

        keys=sorted(counts,key=lambda x:x*-1)
        for i in keys:
            print str(i)+'\t'+str(counts[i])
        outFile.close()	

def printPart(edgeDict,count,size,Path):
	pCounts=0
        keys=sorted(edgeDict,key=lambda x:edgeDict[x]*-1)
        partPath=Path+"_P"+str(count/size)
        outFile=open(partPath,'w')
	print str(count/size)
        for key in keys:
	    if pCounts<5:
		pCounts+=1
		print key[0]+'\t'+key[1]+'\t'+str(edgeDict[key])
            outFile.write(key[0]+'\t'+key[1]+'\t'+str(edgeDict[key])+'\n')
        outFile.close()
	print ''
	return partPath

def sortFile(fullPath,Path):
        print fullPath
        inFile=open(fullPath,'r')
        pathList=[]
        count=0
        edgeDict={}
  	size=1000000
	
        for line in inFile:
            terms=line.strip().split('\t')
            a1=terms[0]
            a2=terms[1]
            edgeDict[(a1,a2)]=float(terms[2])
            count+=1
            if count%size==0:
		pathList.append(printPart(edgeDict,count,size,Path))
		edgeDict={}
	print count
	if count%size!=0:
		pathList.append(printPart(edgeDict,count+size,size,Path))
	
        return pathList

def union(A,B):
	C=[]
	for i in A:
		C.append(i)
	for i in B:
		C.append(i)
	return C
	
def mergeRecursive(pathList):
	
	if len(pathList)==0:
	    return
        if len(pathList)==1:
            return pathList
        if len(pathList)==2:
            return mergeSub(pathList[0],pathList[1])
        else:
            m=len(pathList)/2
            return mergeRecursive(union(mergeRecursive(pathList[0:m]),mergeRecursive(pathList[m:])))
            
def mergeSub(pathA,pathB):
    	
        inFileA=open(pathA,'r')
        inFileB=open(pathB,'r')
	A=pathA
	B=pathB.split('_')[-1]
	
        lambdaDict={'A':inFileA,'B':inFileB}
        outFile=open(A+B,'w')
        xA,yA,valueA=inFileA.readline().strip().split('\t')
        xB,yB,valueB=inFileB.readline().strip().split('\t')
	valueA=float(valueA)
	valueB=float(valueB)
	print pathA
	print pathB
	print ''
        while True:
            if valueA>valueB:
                outFile.write(xA+'\t'+yA+'\t'+str(valueA)+'\n')
		#print "A:"+xA+'\t'+yA+'\t'+str(valueA)
                line=inFileA.readline()
                if len(line)==0:
                    rem,File=([xB,yB,valueB],inFileB)
                    break
                xA,yA,valueA=line.strip().split('\t')
		valueA=float(valueA)
                
            else:
                outFile.write(xB+'\t'+yB+'\t'+str(valueB)+'\n')
		#print "B:"+xB+'\t'+yB+'\t'+str(valueB)
                line=inFileB.readline()
                if len(line)==0:
                    rem,File=([xA,yA,valueA],inFileA)
                    break
                xB,yB,valueB=line.strip().split('\t')
		valueB=float(valueB)
        
        outFile.write(rem[0]+'\t'+rem[1]+'\t'+str(rem[2])+'\n')
        
        for line in File:
	    if len(line)>0:
		#print line
            	outFile.write(line)
        outFile.close()
        inFileA.close()
        inFileB.close()
        return [A+B]

	
	
def compareCom(comDictA,comB,type,type2):
	diff=0
	total=0
	splits=50
	
	
	for com in comDictA:
		members=comDictA[com]
		memberList=[]
		for i in members:
			if i in comB.byNode:
				memberList.append(i)
		n=len(memberList)
		if n<2:
			continue
		
		splits=20	
		if n>1000:
			splits=100
		if n>5000:
			splits=1000

		if n>400 and type=='randomized':
			cases=int((math.pow(n,2)-float(n))/2)
			samples=cases/splits
			factor=float(cases)/samples
			diffR=float(0)
			totalR=float(0)
			
			for i in range(samples):
				node1=0
				node2=0
				while node1==node2:
					node1=random.choice(memberList)
					node2=random.choice(memberList)
				diffValue=1
				if comB.byNode[node1]!=comB.byNode[node2]:
					if type2=='hierarchical':
						diffValue=getHierarchicalDiff(comB.byNode[node1],comB.byNode[node2],comB.mergeSizeDict)
					diffR+=diffValue
					totalR+=(1-diffValue)
				else:
					totalR+=1
			diff+=int(diffR*factor)
			total+=int(totalR*factor)
		else:

			for pair in itertools.combinations(memberList,2):
				node1=pair[0]
				node2=pair[1]
				diffValue=1
				if comB.byNode[node1]!=comB.byNode[node2]:
					if type2=='hierarchical':
						diffValue=getHierarchicalDiff(comB.byNode[node1],comB.byNode[node2],comB.mergeSizeDict)
					diff+=diffValue
					total+=(1-diffValue)
				else:
					total+=1
		
			
	return diff,total

def getHierarchicalDiff(node1,node2,mergeSizeDict):
	a=min(node1,node2)
	b=max(node1,node2)
	diffValue=1
	if (a,b) in mergeSizeDict:
		diffValue=1-(1/float(mergeSizeDict[(a,b)]) )
	return diffValue
	
def compareEfficient(comA,comB,type,type2):
	#print len(comA.byNode)
	#print len(comB.byNode)
	
	diff=0
	diffA,totalA=compareCom(comA.byCom,comB,type,type2)
	diffB,totalB=compareCom(comB.byCom,comA,type,type2)

	#print "DiffA:"+str(diffA)
	#print "totalA:"+str(totalA)
	#print "DiffB:"+str(diffB)
	#print "totalB:"+str(totalB)
	diff=diffA+diffB
	totalAv=(totalA+totalB)/2	
	return float(totalAv)/(totalAv+diff),float(totalA)/(totalA+diffA),float(totalB)/(totalB+diffB)


def breakCondition(coefList):
        if coef[-1]>0.98 and coef[-1]>0.98:
            return True
        return False

def skipLines(inFile,skips):
	for i in range(skips):
		inFile.readline()
	return inFile

def plot(lang):
	index=pickle.load(open("Networks/Communities/"+lang+"/"+Type+"_count.pkl",'r'))
	outFile=open("Networks/edgeCurves_"+lang+".csv",'w')
	outFile.write('Edges,Nodes,nCommunities,largestCommunity,Modularity,largestComponent,Bicorrelation,ForwardCorrelation,BackwardCorrelation,CorrHierarchy,ForCorrHierarchy,BackCorrHierarchy,articleSpreadCorr,CountrySpreadCorr\n')
	prevCommunities=pickle.load(open("Networks/Communities/"+lang+"/"+Type+"_condensednetwork_"+str(1)+".pkl",'r')).communities
	for i in range(2,index+1):
		currentNet=pickle.load(open("Networks/Communities/"+lang+"/"+Type+"_condensednetwork_"+str(i)+".pkl",'r'))
		print "lang\t"+lang+"\tEdges:"+str(currentNet.nedges)
		outFile.write(str(currentNet.nedges)+','+str(currentNet.nvertices)+','+str(currentNet.cardinality)+','+str(currentNet.largestCommunity[0])+','+str(currentNet.communities.modularity)+','+str(currentNet.proportionV)+','+str(currentNet.correlationDict['randomized'][0])+','+str(currentNet.correlationDict['randomized'][1])+','+str(currentNet.correlationDict['randomized'][2]))
		outFile.write(','+str(currentNet.correlationDict['hierarchical_randomized'][0])+','+str(currentNet.correlationDict['hierarchical_randomized'][1])+','+str(currentNet.correlationDict['hierarchical_randomized'][2]))
		outFile.write(','+str(currentNet.correlationDict['article'][0])+','+str(currentNet.correlationDict['country'][0])+'\n')
		prevCommunities=currentNet.communities
	outFile.close()
	
def createAuthorNet(lang,Path,authorNames,graphType,initial,factor,Dicts,reload=False):
        currentNet=wikiGraph(graphType)
	prevCommunities=None
	edgeCount=initial
	correlations=[]
	fileEnd=False
	loop=0
	
	if reload:
		loop=pickle.load(open("Networks/Communities/"+lang+"/"+Type+"_count.pkl",'r'))
		print "LoadingNet:"+str(loop)
		currentNet=pickle.load(open("Networks/Communities/"+lang+"/"+Type+"_condensednetwork_"+str(loop)+".pkl",'r'))
		prevCommunities=currentNet.communities
		print 'Modularity:'+str(currentNet.getModularity())
		print "LargestCommunity:"+str(currentNet.largestCommunity[0])
		print "CommunityCardinality:"+str(currentNet.cardinality)
		print "Vertices:"+str(currentNet.nVertices())
		print "Edges:"+str(currentNet.nEdges())
		edgeCount=int(round(float(currentNet.nedges)*factor,0))+currentNet.nedges
		currentNet=wikiGraph(graphType)

	
	while fileEnd==False:
		inFile=open(Path,'r')
		print 'this is it'
		print ''
		print ''
		print 'Lang='+str(lang)
		print 'Edges:'+str(currentNet.nEdges())
		print 'newEdgeCount:'+str(edgeCount)
		loop+=1

		currentNet,inFile,fileEnd=loadNetworkRangePortion(currentNet,inFile,edgeCount,authorNames)
		print 'Community Started'
		start=datetime.datetime.now()
		currentNet.getCommunities()
		print 'Community ProcessingTime:'+'\tTime:'+str(datetime.datetime.now()-start)
		start=datetime.datetime.now()
		print 'Modularity:'+str(currentNet.getModularity())
		print "LargestCommunity:"+str(currentNet.largestCommunity[0])
		print "CommunityCardinality:"+str(currentNet.cardinality)
		print "Vertices:"+str(currentNet.nVertices())
		print "Edges:"+str(currentNet.nEdges())
		currentNet.nedges=currentNet.nEdges()
		currentNet.nvertices=currentNet.nVertices()
		currentNet.computeCorrelations(prevCommunities,'randomized','')
		currentNet.computeSpreads(Dicts,lang)
		currentNet.graph=nx.Graph()
		print "Loop:"+str(loop)
		pickle.dump(currentNet,open("Networks/Communities/"+lang+"/"+Type+"_condensednetwork_"+str(loop)+".pkl",'w'))
		pickle.dump(loop,open("Networks/Communities/"+lang+"/"+Type+"_count.pkl",'w'))
		print 'Comparison Processing:'+'\t'+"Time:"+str(datetime.datetime.now()-start)	
                prevCommunities=currentNet.communities
		edgeCount=int(round(float(currentNet.nedges)*factor,0))+currentNet.nedges
	
		inFile.close()
		
	correlations=sorted(correlations, key=lambda x: x[1])
	for MIN,corr1,corr2,corr3 in correlations:
		print "LatestEdges:"+str(MIN)+'\t'+"Corr1:"+str(corr1)+'\t'+"Corr2:"+str(corr2)+'\t'+"Corr3:"+str(corr3)
		
def loadNetworkRangeCutoff(G,inFile,line,MAX,MIN,authorNames):
	#for i in range(6):
	#	print ''
	#print "Connecting Line:"
	#print line.strip()
	
	edgeList=[]
	if line!='':
		A1,A2,Count=line.strip().split('\t')
		Count=int(Count)
		A1=G.addNode(A1,authorNames[A1],'author')
            	A2=G.addNode(A2,authorNames[A2],'author')
            	edgeList.append((A1,A2))

	lastLine=''
        for line in inFile:
	    if len(line)==0:
		continue
	    lastLine=line
            A1,A2,Count=line.strip().split('\t')
	    Count=int(Count)
            if Count>=MAX:
                continue
            if Count<MIN:
                break
	    #print line.strip()
            A1=G.addNode(A1,authorNames[A1],'author')
            A2=G.addNode(A2,authorNames[A2],'author')
	 
	  
            edgeList.append((A1,A2))
        G.graph.add_edges(edgeList)
	print G.graph.ecount()
	print G.graph.vcount()
        return G,inFile,lastLine
	
def loadNetworkRangePortion(G,inFile,edgeCount,authorNames):

        edgeList=[]
        processed=0
        endFlag=True
	print 'Trying to read'
        for line in inFile:
	    processed+=1
	    if len(line)==0:
		continue
	    #print line.strip()
            A1,A2,Count=line.strip().split('\t')
	    Count=float(Count)
	    
            A1=G.addNode(A1,authorNames[A1])
            A2=G.addNode(A2,authorNames[A2])

	    if weightFlag:
            	edgeList.append((A1,A2,Count))
	    else:
		edgeList.append((A1,A2))
		
            if processed==edgeCount:
		endFlag=False
		break
	if len(edgeList)!=0:
        	G.addEdges(edgeList)
        return G,inFile,endFlag


def initializeRandFiles(size,Type):
	randFiles=[]
	for i in range(size):
		  Path='Networks/Randomizer/'+str(i)
		  outFile=open(Path,Type)
		  randFiles.append((Path,outFile))
	return randFiles
	
def loadEdges(inFile):
	edges=[]

	for lineN in inFile:
		line=lineN.strip()
		if line=='':
			continue
		edges.append(lineN)
	return edges

def randomizedOutput(List,ultimateOut):
	print len(List)
	count=0
	counter=0
	random.shuffle(List)

	for i in List:
		ultimateOut.write(i)
		count+=1
	
def printOut(randFiles,ultimateOut):
	outRandFiles=[]
	for i in range(len(randFiles)):
		  randFiles[i][1].close()
		  outRandFiles.append((randFiles[i][0],open(randFiles[i][0],'r')))
		
        for i in range(len(outRandFiles)):
		  edgeList=loadEdges(outRandFiles[i][1])
		  randomizedOutput(edgeList,ultimateOut)
			
			
def randBuckets(edge,randFiles):
	size=len(randFiles)
	i=random.randint(0,size-1)

	randFiles[i][1].write(edge)
		
					
def randomizer(Path):
	
	ultimateOut=open(Path+'new','w')
	inFile=open(Path,'r')
	prevCount='start'
	randFiles=initializeRandFiles(20,'w')
	for lineN in inFile:
		line=lineN.strip()
		if line=='':
			continue
		Count=line.split('\t')[-1]
		if Count!=prevCount and prevCount!='start':
			print Path+'\t'+Count
			printOut(randFiles,ultimateOut)
			randFiles=initializeRandFiles(20,'w')
		randBuckets(lineN,randFiles)
		prevCount=Count
	printOut(randFiles,ultimateOut)
	ultimateOut.close()
	return Path+'new'	
	
def condenseNetwork(lang):

	instances=pickle.load(open("Networks/Communities/"+lang+"/"+Type+"_count.pkl",'r'))
	instances=95
	for i in range(1,instances+1):
		print lang+'\t'+str(i)
		currentNet=pickle.load(open("Networks/Communities/"+lang+"/"+Type+"_network_"+str(i)+".pkl",'r'))
		currentNet.nedges=currentNet.nEdges()
		currentNet.nvertices=currentNet.nVertices()
		currentNet.graph=nx.Graph()
		pickle.dump(currentNet,open("Networks/Communities/"+lang+"/"+Type+"_condensednetwork_"+str(i)+".pkl",'w'))
		

def getSuperCommunities(lang,typeI,spreads):
	print lang
	instances=pickle.load(open("Networks/Communities/"+lang+"/"+Type+"_count.pkl",'r'))
	prevCom=None
	
	for i in range(instances,instances+1):
		print lang+'\tGGG'+str(i)
		currentNet=pickle.load(open("Networks/Communities/"+lang+"/"+Type+"_condensednetwork_"+str(i)+".pkl",'r'))
		print len(currentNet.spreads['article'])
		for article in currentNet.spreads['article']:
			spreads[article]=currentNet.spreads['article'][article]
		continue
		if typeI==1:
			currentNet.getSuperCom()

			if prevCom:
				currentNet.computeCorrelations(prevCom,'randomized','')
				currentNet.computeCorrelations(prevCom,'randomized','hierarchical')
				currentNet.computeSpreadCorrelation(prevSpreads,'article')
				currentNet.computeSpreadCorrelation(prevSpreads,'country')
			prevCom=currentNet.communities
			prevSpreads=currentNet.spreads
			#pickle.dump(currentNet,open("Networks/Communities/"+lang+"/"+Type+"_condensednetwork_"+str(i)+".pkl",'w'))
		else:
			currentNet.getSpreadDistribution(20,'article')
			currentNet.getSpreadDistribution(20,'country')
			articleDist[lang]=currentNet.spreadDist['article']
			countryDist[lang]=currentNet.spreadDist['country']
	return spreads

		
		
def plotSDists():
	outFile=codecs.open("Networks/spreadDistributions.csv",'w')
	outFile.write('spreadValue(xAxis),spreadDistArticle_en,spreadDistCountry_en,spreadDistArticle_fr,spreadDistCountry_fr,spreadDistArticle_ar,spreadDistCountry_ar,spreadDistArticle_fa,spreadDistCountry_fa,')
	outFile.write('spreadDistArticle_he,spreadDistCountry_he,spreadDistArticle_sw,spreadDistCountry_sw,spreadDistArticle_arz,spreadDistCountry_arz\n')
	
	keys=sorted(articleDist['en'],key=lambda x:x)	
	for i in keys:
		outFile.write(str(i))
		for lang in langs:
			print lang
			aD=articleDist[lang][i]
			cD=countryDist[lang][i]
			outFile.write(','+str(aD)+','+str(cD))
		outFile.write('\n')
	outFile.close()


def startDB():
	connection = MySQLdb.connect(HOSTNAME, 
	USERNAME, PASSWORD, DATABASE, charset='utf8')
	cursor = connection.cursor()
	return (connection,cursor)

def add2DB(cur,spreads):
	for article in spreads:
		value=spreads[article]
		query="UPDATE ArticleOct set spread=%s where keyArticle='%s'"%(str(value),article)
		cur.execute(query)
	
if __name__ == '__main__':
	start=datetime.datetime.now()
     
 
        Type=sys.argv[1]
        edgeFiles={}
	graphType='networkx'
	weightFlag=False
	
	con,cur=startDB()
	if 'c' in sys.argv:
		for lang in langs:
			condenseNetwork(lang)
	
	if 'w' in sys.argv or 'weighted' in sys.argv:
		weightFlag=True
		
	if 'igraph' in sys.argv:
		graphType='igraph'
	if 'p' in sys.argv:
		for lang in langs:
			plot(lang)
	if 'g' in sys.argv:#get the densest network
		for lang in langs:
			hashNetwork,authorNames=createBasicNetwork(con,cur,lang)
			pickle.dump(hashNetwork,open("Networks/PKLs/"+lang+"_"+Type+"_HashBipartite.pkl",'w'))
                        pickle.dump(authorNames,open("Networks/PKLs/"+lang+"_"+Type+"_authorNames.pkl",'w'))
			generateUniModal(lang,hashNetwork)
			
        if 's' in sys.argv:
                for lang in langs:
                        pathList=sortFile("Networks/Sorting/"+lang+"_"+Type+"_AllEdges","Networks/Sorting/SortDump/"+lang+"/"+Type+"_AllEdges")
                        edgeFiles[lang]=mergeRecursive(pathList)[0]
			
		pickle.dump(edgeFiles,open("Networks/PKLs/"+Type+"_edgeFilePaths.pkl",'w'))
		
        if 'r' in sys.argv:
		edgeFiles=pickle.load(open("Networks/PKLs/"+Type+"_edgeFilePaths.pkl",'r'))
	        for lang in langs:
				edgeFiles[lang]=randomizer(edgeFiles[lang])
		pickle.dump(edgeFiles,open("Networks/PKLs/"+Type+"_edgeFilePaths.pkl",'w'))
		
	if 'o' in sys.argv:# get the optimized network
                edgeFiles=pickle.load(open("Networks/PKLs/"+Type+"_edgeFilePaths.pkl",'r'))
		for lang in langs:
			Dicts={}
			Dicts['article']=articleDict[lang]
			Dicts['country']=countryDict[lang]
                        authorNames=pickle.load(open("Networks/PKLs/"+lang+"_"+Type+"_authorNames.pkl",'r'))
			createAuthorNet(lang,edgeFiles[lang],authorNames,graphType,100,0.12,Dicts)
		
	if 'com' in sys.argv:
		spreads={}
		for lang in langs:
			spreads=getSuperCommunities(lang,2,spreads)	
		pickle.dump(spreads,open("Networks/PKLs/"+Type+"_spreads.pkl",'w'))
		
	if 'db' in sys.argv:
		spreads=pickle.load(open("Networks/PKLs/"+Type+"_spreads.pkl",'r'))
		add2DB(cur,spreads)
		#plotSDists()
		
			
	     
