# -*- coding: utf-8 -*-
from subprocess import call
import pygraph.readwrite
from functools import reduce
from pygraph.classes.digraph import digraph
from propsde.graph_representation.newNode import Node, isDefinite, getCopular, \
    getPossesive, EXISTENSIAL
from pygraph.algorithms.accessibility import accessibility
from propsde.graph_representation.graph_utils import get_min_max_span, find_nodes, \
    find_edges, merge_nodes, multi_get, duplicateEdge, accessibility_wo_self, \
    subgraph_to_string, replace_head, find_marker_idx
from propsde.graph_representation.word import Word
from propsde.dependency_tree.definitions import *
import pygraph.readwrite.dot


from itertools import product
from propsde.graph_representation.proposition import Proposition
from copy import copy, deepcopy
import re, cgi, time, subprocess, math

from itertools import product
from propsde.graph_representation.proposition import Proposition
from copy import copy, deepcopy
from propsde.graph_representation import newNode
# from ctypes.wintypes import WORD

from propsde.utils.utils import encode_german_characters, encode_german_chars
import propsde.graph_representation.raising_subj_verbs as raising_subj_verbs
import sys
if sys.version_info[0] >= 3:
    unicode = str

FIRST_ENTITY_LABEL = "sameAs_arg"  # "first_entity"
SECOND_ENTITY_LABEL = "sameAs_arg"  # "second_entity"
POSSESSOR_LABEL = "possessor"
POSSESSED_LABEL = "possessed"
COMP_LABEL = "comp"
DISCOURSE_LABEL = "discourse"

CONDITION_LABEL = "condition"
REASON_LABEL = "reason"
OUTCOME_LABEL = "outcome"
EVENT_LABEL = "event"
ADV_LABEL = "adverb"
SORUCE_LABEL = "source"


TOPNODE_COLOR = "red"
PREDICATE_COLOR = "purple"

#join_labels = ["mwe", "nn", "num", "number", "possessive", "prt", "predet", "npadvmod"]
join_labels = [ ("PNC","ALL"), ("NMC","ALL"), ("NK","CARD"), ("SVP","ALL"), ("AMS","ALL"), ("PM","ALL"), 
                ("ADC","ALL"), ("AVC","ALL"), ("UC","ALL") ]

ignore_labels = [] #["det", "neg", "aux", "auxpass", "punct"]
ignore_nodes = [ ("--","$,"), ("--","$."), ("--","$("), ("NG","ALL"), ("NK","ART"), ("JU","ALL") ]

#the labels we unify:
inverse_labels = {"subj":["SB","possessor"], #["xsubj","nsubj","nsubjpass","csubj","csubjpass","possessor"],
                    "comp": ["CP"], #["xcomp","ccomp","acomp"]
                    "source":[], #["acomp"],
                    "mod": ["MO","NK","MNR","CC"], #["amod","advcl","rcmod","advmod","quantmod","vmod"],
                    "dobj":["OC","OA","OA2","OG","possessed"], #["possessed"]
                    "iobj": ["DA"], # new for DE
                    "poss": ["AG","PG"], # new for DE
                     } 
normalize_labels_dic = {}

for k in inverse_labels:
    for v in inverse_labels[k]:
        normalize_labels_dic[v] = k
        
def star(f):
    return lambda args: f(*args)


class GraphWrapper(digraph):
    """
    save nodes by uid, to make it possible to have different nodes with same str value
    
    @type nodes: dict
    @var  nodes: a mapping from a node uid to its Node object
    """
    def __init__(self, originalSentence, HOME_DIR):
        """
        Initialize the nodes dictionary as well as the inner digraph
        """
        if not originalSentence:
            originalSentence = "<empty>"
        self.originalSentence = encode_german_characters(originalSentence)
        self.originalSentence_original = originalSentence
        self.HOME_DIR = HOME_DIR
        self.nodesMap = {}
        self.modalVerbs = raising_subj_verbs.verbs
        digraph.__init__(self)
        
    def set_original_sentence(self,s):
        self.originalSentence = encode_german_characters(s)
        
    def nodes(self):
        """
        overrides the nodes() function of digraph, to maintain the nodes mapping

        @rtype  list(Node)
        @return the Node objects stored in this graph
        """
        return [self.nodesMap[curId] for curId in digraph.nodes(self)]
    
    def edges(self):
        """
        overrides the edges() function of digraph, to maintain the nodes mapping
    
        @rtype  list(edge)
        @return the edges stored in this graph
        """
        return [(self.nodesMap[u_v[0]], self.nodesMap[u_v[1]]) for u_v in digraph.edges(self)]

    def is_edge_exists(self, n1, n2):
        """
        overrides the edges() function of digraph, to maintain the nodes mapping

        @rtype  list(Edge)
        @return the Edge objects stored in this graph
        """
        return (n1, n2) in self.edges()

    def get_components(self):
        graph_components = accessibility(self)
        return {self.nodesMap[key.uid]:[self.nodesMap[v.uid] for v in value] for key, value in graph_components.iteritems() }

    def add_node(self, node):
        """
        overrides the add_node of digraph, to maintain the nodes mapping
            
        @type  node: Node
        @param node: the node to be added to the graph
        """
        self.nodesMap[node.uid] = node
        digraph.add_node(self, node.uid)
        
    def del_node(self, node):
        """
        overrides the del_node of digraph, to maintain the nodes mapping
            
        @type  node: Node
        @param node: the node to be removed
        """
        del(self.nodesMap[node.uid])
        # remove this node from any future propagation
        for curNode in self.nodesMap.values():
            if node in curNode.propagateTo:
                curNode.propagateTo.remove(node)
        digraph.del_node(self, node.uid)
        
    def del_nodes(self, nodes):
        """
        delete a set of nodes
        """
        for node in nodes:
            self.del_node(node)
        

    def del_edge(self, edge):
        """
        overrides the del_edge of digraph, to maintain the nodes mapping
            
        @type  edge: tuple [node]
        @param edge: the edge to be removed
        """

        u, v = edge
        if v not in self.neighbors(u):
            print("1")
        if isinstance(u, Node):
            digraph.del_edge(self, edge=(u.uid, v.uid))
        else:
            digraph.del_edge(self, edge=edge)
            
    def del_edges(self, edges):
        for edge in edges:
            self.del_edge(edge)
    
    def neighbors(self, node):
        """
        overrides the neighbors function of digraph, to maintain the nodes mapping
        
        @type  node: Node
        @param node: the nodes of the neighbors
        """
        if isinstance(node, Node):
            return [self.nodesMap[uid] for uid in digraph.neighbors(self, node.uid)]
        else:
            return digraph.neighbors(self, node)
    
    def incidents(self, node):
        """
        overrides the incidents function of digraph, to maintain the nodes mapping
        
        @type  node: Node
        @param node: the nodes of the neighbors
        """
        if isinstance(node, Node):
            return [self.nodesMap[uid] for uid in digraph.incidents(self, node.uid)]
        else:
            return digraph.incidents(self, node)
    
    def add_edge(self, edge, label=''):
        """
        overrides the add_edge function of digraph, to maintain the nodes mapping
        
        @type  edge: (node1,node2)
        
        @type  node1: Node
        @param node2: origin of new edge
        
        @type  node2: Node
        @param node2: destination of new edge
        """
        node1, node2 = edge
        basicEdge = (node1.uid, node2.uid)
        ret = digraph.add_edge(self, edge=basicEdge, label=label)
#         if not self.is_aux_edge(basicEdge):
#             self.del_edge(edge)
#             ret = digraph.add_edge(self,edge=basicEdge,label=label,wt=100)
        return ret
        
    def __str__(self):
        ret = self.originalSentence+"\n"
        for i,node in enumerate(self.nodesMap.values()):
            ret += node.to_conll_like() + "\n"
        return ret
       
    
    def edge_label(self, edge):
        """
        overrides the edge_label function of digraph, to maintain the nodes mapping
        @type  edge: (node1,node2)
        
        @type  node1: Node
        @param node2: origin of new edge
        
        @type  node2: Node
        @param node2: destination of new edge
        """
        node1, node2 = edge
        if isinstance(node1, Node):
            return digraph.edge_label(self, edge=(node1.uid, node2.uid))
        else:
            return digraph.edge_label(self, edge)
        
    def has_edge(self, u_v):
        u, v = u_v
        return digraph.has_edge(self, (u.uid, v.uid))


    def set_edge_label(self, edge, label):
        node1, node2 = edge
        return digraph.set_edge_label(self, edge=(node1.uid, node2.uid), label=label)

    def drawToFile(self, filename, filetype):
        """ 
        Saves a graphic filename of this graph
        
        @type  filename string
        @param name of file in which to write the output, without extension
        
        @type  filetype string
        @param the type of file [png,jpg,...] - will be passed to dot 
        """
        
        if not filename:
            return self.writeToDot(filename="",
                           writeLabel=False)
            
        
        ret = self.writeToDot(filename=filename + ".dot",
                           writeLabel=(filetype == "svg"))
        
        call("dot -T{1} {0}.dot -o {0}.{1}".format(filename, filetype).split())
        
    def is_aux_edge(self, src_dst):
        """
        src and dst should be uid's of nodes!
        """
        src, dst = src_dst
        label = self.edge_label((src, dst))
        if (not self.nodesMap[src].isPredicate) or ((label not in arguments_dependencies + clausal_complements)):# and (not label.startswith("prep"))):
            return True
        return False
        

    def writeToDot(self, filename, writeLabel):
        """
        Outputs a dot file representing this graph
        
        @type  filename: string
        @param filename: the file in which to save the dot text
        """        
        dot = pygraph.readwrite.dot.pydot.Dot()
        
        if writeLabel:
            label = "\n".join([self.originalSentence.encode('utf-8')])
            dot.set_label(label)
            dot.set_labelloc("bottom")
            dot.set_labeljust("center")
        
        for uid in self.nodesMap:
            curNode = self.nodesMap[uid]
            dotNode = pygraph.readwrite.dot.pydot.Node()
            dotNode.set_shape(curNode.nodeShape)
            dotNode.set_name(unicode(uid))
            label = encode_german_chars(u"<{0}>".format(curNode))
            dotNode.set_label(label.encode('ascii', errors='ignore'))
            if curNode.isPredicate:
                dotNode.set_color(PREDICATE_COLOR)
                dotNode.set_fontcolor(PREDICATE_COLOR)
            if curNode.features.get("top", False):
                dotNode.set_color(TOPNODE_COLOR)
                dotNode.set_fontcolor(TOPNODE_COLOR)
                
            ##### for debug #####
            if curNode.features.has_key("Nominal"):
               dotNode.set_color("blue")
               dotNode.set_fontcolor("blue")
            if curNode.features.has_key("VADAS"):
               dotNode.set_color("green")
               dotNode.set_fontcolor("green")
            if curNode.features.has_key("traces"):
               dotNode.set_color("orange")
               dotNode.set_fontcolor("orange")
            if curNode.features.has_key("LV"):
               dotNode.set_color("purple")
               dotNode.set_fontcolor("purple")
            if curNode.features.has_key("heuristics"):
               dotNode.set_color("teal")
               dotNode.set_fontcolor("teal")
            if curNode.features.has_key("debug"):
                dotNode.set_color("blue")
                dotNode.set_fontcolor("blue")

            dot.add_node(dotNode)
        
        for (src, dst) in digraph.edges(self):
            curEdge = pygraph.readwrite.dot.pydot.Edge(src=src, dst=dst)
            curEdge.set_fontsize("11")
            label = self.edge_label((src, dst)).encode('utf-8')
            if label:
                if self.is_aux_edge((src, dst)):
                    curEdge.set_style("dashed")
                curEdge.set_label(label)
            dot.add_edge(curEdge)
        if not filename:
            return dot
        try:
            dot.write(filename)
        except Exception as e:
            print(e)
            
            
    def getJson(self):
        """
        @return: json representation of this graph
        """
        # format: (unique id, (isPredicate, (minIndex, maxIndex))) 
        entities = dict([(uid, {'predicate': bool(node.isPredicate), 
                                'feats': self.getFeatsDic(node),  
                                'charIndices': (0,0) if not node.text else self.nodeToCharIndices(node)})
                         for uid, node in self.nodesMap.items()])
        edges = [(src, dest, self.edge_label((src, dest))) for (src, dest) in digraph.edges(self)]
        return (entities, edges)

    
    def getFeatsDic(self, node):
        
        return {'implicit' : node.is_implicit(),
                'tense' : node.features.get('Tense', ''),
                'text' : sorted(node.text, key = lambda w: w.index),
                'passive' : 'passive' if 'Passive Voice' in node.features else '',
                'definite' : node.features.get('Definite', ''),
                'pos' : node.pos() if node.pos() else 'NN',
                'negated': 'negated' if 'Negation' in node.features else '',
                'subjunctive': node.features.get('Subjunctive', '')}
    
    
    def nodeToCharIndices(self, node):
        ''' Get the start and end char indices from a given word index in a tokenized sentence '''
        sent = self.originalSentence 
        if (not node.text):
            return (0,0)
        data = sent.split(' ')
        
        sortedText = sorted(node.text, key = lambda w: w.index)
        
        startInd = sortedText[0].index
        endInd = sortedText[-1].index
        
        if not node.is_implicit():
            startInd = startInd - 1
            endInd = endInd - 1
        
        baseIndex = sum(map(len, data[:startInd])) + startInd
        endIndex = sum(map(len, data[:endInd])) + endInd + len(data[endInd])
        return (baseIndex, endIndex)
        
    
    def draw(self):
        """
        Displays the graph output by dot with mspaint.
        It saves the dot and png file in temporary files in pwd.
        """
        dumpGraphsToTexFile(graphs=[self], appendix={}, graphsPerFile=1, lib=self.HOME_DIR, outputType="html")
        call('"C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe" ' + self.HOME_DIR + 'autogen0.html')
        
        
        
        
    # was called _aux for English, but were actually removing other relations for German here. auxiliaries are handled in the next method.
    def remove_aux(self):
        # according to dict (beginning of file)
        edges = find_edges(self, lambda u_v:self.edge_label(u_v) in [n[0] for n in ignore_nodes])

        for u, v in edges:
            if (self.edge_label((u, v)), v.pos()) in ignore_nodes or (self.edge_label((u, v)),"ALL") in ignore_nodes or ("ALL",v.pos()) in ignore_nodes:
                if v.uid in self.nodesMap:
                    u.original_text.extend(v.original_text)
                    u.surface_form.extend(v.surface_form)
                    # place children of v under u
                    child_dict = v.neighbors()
                    for child_rel in child_dict:
                        for child in child_dict[child_rel]:
                            if child != u:
                                self.add_edge((u,child), child_rel)
                    self.del_node(v)
        # dass
        edges = find_edges(self, lambda u_v:(self.edge_label(u_v) == "CP") and u_v[1].pos() in ['KOUS'] and (u_v[1].text[0].word.lower() in [u"dass",u"daß"]))
        for u, v in edges:
            if v.uid in self.nodesMap and len(v.neighbors()) == 0:
                self.del_node(v)
                    
    def remove_aux_mod_de(self):
        edges = find_edges(self, lambda u_v:self.edge_label(u_v) == 'OC' and u_v[0].pos() in VERB_POS_AUX+VERB_POS_MOD and u_v[1].pos() in VERB_POS_ALL)
        
        if edges:
            u, v = edges[0]
            replace_head(self,u,v)   
            # do recursively        
            self.remove_aux_mod_de()
        
    def do_relc_de(self):
        edges = find_edges(self, lambda u_v: self.edge_label(u_v) == 'RC')
        if edges:
            for u, v in edges:
                # find pronoun -> traverse all children
                pn = self.find_rc_pronoun(v)
                if not pn:
                    continue
                rc_pronoun_head, rc_pronoun, rel_pronoun = pn
                if rc_pronoun:
                    rc_pronoun_head.surface_form += rc_pronoun.surface_form
                    rc_pronoun_head.original_text += rc_pronoun.original_text
                    self.del_node(rc_pronoun)
                if rel_pronoun:
                    self.del_edge((u, v))
                    self.add_edge((rc_pronoun_head,u), rel_pronoun)
                    if not self.has_proper_noun(u):
                        self.add_edge((u, v), "mod")
                        rc_pronoun_head.makeTopNode()
    
    def has_proper_noun(self, node):
        visited = set()
        nodes = [node]
        while len(nodes) > 0:
            n = nodes[0]
            if n.pos() == 'NE':
                return True
            visited.add(n)
            nodes = nodes[1:]
            for rel in n.neighbors():
                for child in n.neighbors()[rel]:
                    if not child in visited:
                        nodes += [child]
        return False
        
        
    def find_rc_pronoun(self, v):
        node = [v]
        visited = set()
        while len(node) > 0:
            n = node[0]
            visited.add(n)
            node = node[1:]
            for rel in n.neighbors():
                for child in n.neighbors()[rel]:
                    if child.pos() in ['PRELS','PRELAT']:
                        return (n,child,rel)
                    else:
                        if not child in visited:
                            node += [child]
        return None
        
    def do_comp_de(self):
        edges = find_edges(self, lambda u_v: self.edge_label(u_v) == 'CM')
        if edges:
            for u, v in edges:
                # find CC
                try:
                    incidents = u.incidents()
                    if "CC" in incidents:
                        cc = incidents["CC"][0]
                        self.del_edge((u, v))
                        self.add_edge((cc,v),"tmp")
                        merge_nodes(self,cc,v)
                except:
                    pass
                        
    def _merge(self):
        # TODO: conjunction
        edges = find_edges(self, lambda u_v: ((self.edge_label(u_v),u_v[1].pos()) in join_labels or (self.edge_label(u_v),"ALL") in join_labels) or (self.edge_label(u_v)=="conj_and" and u_v[0].features.get("conjType",[""])[0]=='&'))
        for u, v in edges:
            conjType = u.features.get("conjType",False)
            if conjType:
                conjType = conjType[0] #only the words
                matching = [w for w in u.surface_form if w.word == conjType]
                if matching:
                    w = matching[0]
                else:
                    w = Word(index = u.maxIndex()+1,word=conjType)
                u.text.append(w)
            merge_nodes(self, u, v)
            return True
        # special case: CVC
        for (verb,comp) in find_edges(self, lambda u_v: self.edge_label(u_v) == "CVC"):
            components = []
            verb.features["cvc"] = True
            # collect all components
            traverse = [comp]
            while len(traverse) > 0:
                c = traverse[0]
                components += [c]
                traverse = traverse[1:] + self.neighbors(c)
            components += [verb]
            # merge
            new = merge_nodes(self,components[0],components[1])
            for i in range(2,len(components)):
                new = merge_nodes(self,new,components[i])
        return False
        
    def merge(self):
        applyClosure(self._merge)
        
    def _fix(self):
        # remove mark->that -- ignore for DE
        edges = find_edges(self, lambda u_v:self.edge_label(u_v) == "mark")
        for (u, v) in edges:
            if (len(self.neighbors(v)) == 0) and (len(v.text) == 1) and (v.text[0].word == "that"):
                self.del_node(v)
                return True
        
        # rcmod with no relation to father -- ignore for DE
        edges = find_edges(self, lambda u_v:(self.edge_label(u_v) == "rcmod") and (not self.has_edge((u_v[1], u_v[0]))))
        for u, v in edges:
            self.add_edge((v, u), label=ARG_LABEL)
            return True
        
        # prep collapse 1 - relabel collapses done with JoBim
        edges = find_edges(self, lambda u_v:(self.edge_label(u_v).startswith('MO_')))
        if edges:
            for edge in edges:
                label = self.edge_label(edge).replace('MO_','prep_')
                self.set_edge_label(edge, label)
        edges = find_edges(self, lambda u_v:(self.edge_label(u_v).startswith('CJ_')))
        if edges:
            for edge in edges:
                label = self.edge_label(edge).replace('CJ_','conj_')
                self.set_edge_label(edge, label)
                
        # prep collapse 2 - additional collapsing
        edges = find_edges(self, lambda u_v:(self.edge_label(u_v) in ["MNR","MO","OP"]) and (len(self.neighbors(u_v[1])) == 1) and u_v[1].pos() in ['APPR','APPRART'])
        if edges:
            for u, v in edges:
                pobj = next(iter(v.neighbors().values()))[0]
                if not (self.has_edge((u, pobj))):
                    w = v.text[0]
                    u.surface_form += [w]
                    self.add_edge((u, pobj), label="prep_" + w.word.lower())
                    self.del_node(v)
                    
        # fix dependency collapse bugs -- ignore for DE
        edges = find_edges(self, lambda u_v:(self.edge_label(u_v) == "pobj") and ("prep" not in u.incidents()))
        for u, v in sorted(edges,key=lambda u_v: u.minIndex()):
            neighbors = u.neighbors()
            candidates = [n for n in multi_get(neighbors, [rel for rel in neighbors if rel.startswith("prepc_")]) if len(self.neighbors(n)) == 0]
            candidates.sort(key=lambda n:n.minIndex())
            if len(candidates) > 0:
                curToDel = candidates[0]
                rel = self.edge_label((u, curToDel))
                self.del_edge(u_v)
                self.add_edge(u_v, label=rel)
                self.del_node(curToDel)
        
        # change agent edges with "prep_by" -- ignore for DE
        edges = find_edges(self, lambda edge:(self.edge_label(edge) == "agent"))
        for edge in edges:
            self.del_edge(edge)
            self.add_edge(edge,label="prep_by")
            
#         #add xcomp inverse node
#         edges  = find_edges(self, lambda u_v:self.edge_label(u_v) == "xcomp" and u.isPredicate and v.isPredicate)
#         for u_v in edges:
#             if not self.has_edge((v, u)):
#                 self.add_edge((v,u), label=SOURCE_LABEL)
#                 self.types.add("infinitives")
#                 return True
#             if not multi_get(v.neighbors(),subject_dependencies):
#                 rcmodParentIncidents = u.incidents().get("rcmod",[]) 
#                 if len(rcmodParentIncidents)==1:
#                     subj = rcmodParentIncidents[0]
#                     if not self.has_edge((v,subj)):
#                         self.add_edge((v,subj),label=ARG_LABEL)
                    
            
        return False
        
    def fix(self):
        applyClosure(self._fix)
    
    def createPropRel(self, mod, domain):
        if not self.has_edge((mod,domain)):
            self.add_edge(edge=(mod, domain), label=domain_label)
            domain.original_text = list(set(domain.original_text) - set(mod.original_text))
            mod.isPredicate = True
    
    def calcTopNodes(self):
        all_accessible = multi_get(accessibility_wo_self(self), self.nodes())
        for topNode in [n for n in self.nodes() if n not in all_accessible]:
            topNode.makeTopNode()
        
        change = True
        while change:
            change = False
            for topNode in [n for n in self.nodes() if n.features.get("top", [])]:
                for sourceNode in topNode.incidents().get(SOURCE_LABEL, []):
                        change = sourceNode.makeTopNode()
                if topNode.isConj():
                    for n in self.neighbors(topNode):
                        change = n.makeTopNode()
    
    def getPropositions(self, outputType):
        ret = []
        for topNode in [n for n in self.nodes() if n.features.get("top", False)]:
                #print [w.word for w in topNode.text]
#             if "dups" in topNode.features:
                dups = topNode.features.get("dups", [])
                allDups = reduce(lambda x, y:list(x) + list(y), dups, [])
                rest = [n for n in self.neighbors(topNode) if n not in allDups]
                neigboursList = []
                for combination in product(*dups):
                    curNeigbourList = []
                    ls = list(combination) + rest
                    for curNode in ls:
                        curNeigbourList.append((self.edge_label((topNode, curNode)), curNode))
                    neigboursList.append(curNeigbourList)
                
                for nlist in neigboursList:
                    #print [[w.word for w in x[1].text] for x in nlist]
                    argList = []
                    all_neighbours = [n for _, n in nlist]
                    for k, curNeighbour in sorted(nlist, key=lambda k_n:get_min_max_span(self, k_n[1])[0]):
                        curExclude = [n for n in all_neighbours if n != curNeighbour] + [topNode]
                        if self.edge_label((topNode,curNeighbour)) != "dep":
                            argList.append([k, subgraph_to_string(self, curNeighbour, exclude=curExclude)])
                    if topNode.features.get("Lemma"):
                        topNodeText = encode_german_characters(topNode.features.get("Lemma"))
                    else:
                        topNodeText = topNode.get_original_text()
                    if topNode.features.get("Negation",False):
                        topNodeText = "nicht " + topNodeText
                    argList = [a for a in argList if not a[1].strip() in ["und","oder"]]
                    if not len(argList) == 0:
                        curProp = Proposition(topNodeText, argList, outputType)
                        ret.append(curProp)
                    
        return ret
    
    def normalize_labels(self):
        for edge in self.edges():
            edgeLabel = self.edge_label(edge)
            if edgeLabel in normalize_labels_dic:
                self.del_edge(edge)
                self.add_edge(edge,label = normalize_labels_dic[edgeLabel])
            # catch all
            elif re.match("[A-Z]+", edgeLabel):
                self.del_edge(edge)
                self.add_edge(edge, label = "dep")
    
    def do_vmod_relclause(self):
        # not needed for german at all in the first step
        #  but: general handling of relative clauses!
        edges = find_edges(self, lambda u_v:(self.edge_label(u_v) == "rcmod"))
        for u, v in edges:
            v.features["top"] = True
            if  u.pos() in determined_labels:
                self.del_edge(u_v)
                self.types.add("definite rcmod")
                if not self.has_edge((v, u)):
                    self.add_edge((v, u), label=ARG_LABEL)
        
        edges = find_edges(self, lambda u_v:(self.edge_label(u_v) == "vmod"))
        for u, v in edges:
            self.types.add("vmod")
            if u.pos() in determined_labels:
                self.del_edge(u_v)
                self.types.add("definite vmod")
                if not self.has_edge((v, u)):
                    self.add_edge((v, u), label=ARG_LABEL)
        
        
                                
    def do_poss(self):
        edges = find_edges(self, lambda u_v: (self.edge_label(u_v) == "NK" and u_v[1].pos() in ['PPOSAT']) or (self.edge_label(u_v) == "AG" and u_v[1].pos() in ['NE']))
        for (possessed, possessor) in edges:
            self.types.add("Possessives")
            possessiveNode = getPossesive(self, possessor.minIndex())  # TODO: refine index
            self.add_edge(edge=(possessiveNode, possessor),
                          label=POSSESSOR_LABEL)
            self.add_edge(edge=(possessiveNode, possessed),
                          label=POSSESSED_LABEL)
    
    
    def head(self, node):
        incidents = node.incidents()
        while (node.isPredicate) and ("xcomp" in incidents):
            node = incidents["xcomp"][0]
            incidents = node.incidents()
        return node
    
    def do_conj_propagation(self):
        # mark conjunctions with more than two elements as in the Stanford collapsed dependencies
        edges = find_edges(self, lambda u_v:self.edge_label(u_v).startswith("conj_"))
        for u,v in edges:
            label = self.edge_label((u, v))
            children = [(u, v)]
            incidents = u.incidents()
            while "CJ" in incidents:
                f = incidents["CJ"][0]
                children.append((f,u))
                incidents = f.incidents()
                u = f
            if len(children) > 2:
                for e in children:
                    self.del_edge(e)
                    self.add_edge((f,e[1]),label)                    
    
    def do_conj(self):
        edges = find_edges(self, lambda u_v:self.edge_label(u_v).startswith("conj_"))# and (not u.isPredicate) and (not v.isPredicate))
        nodes = set([u for (u,_) in edges])
        for conj1 in nodes:
            curStartIndex = conj1.minIndex()-1
            curNeighbours = conj1.neighbors()
            isModifier = (not bool([father for father in self.incidents(conj1) if not self.is_aux_edge((father.uid, conj1.uid))])) and bool(self.incidents(conj1)) 
            for rel in [rel for rel in curNeighbours if rel.startswith("conj_")]:
                marker = rel.split("conj_")[1]
                idx = find_marker_idx(self, conj1, rel)
                markerNode = newNode.Node(text=[Word(idx,marker)], #TODO: how to find marker's index
                                          isPredicate=True,
                                          features={"conj":True},
                                          gr=self)
                                          
                #decide how to connect it to the rest of the graph, based on its type
                if isModifier:
                    duplicate_all_incidents(gr=self, source=conj1, target=markerNode)
                else:
                    for father in self.incidents(conj1):
                        for conj2 in curNeighbours[rel]:
                            duplicateEdge(graph=self, orig=((father,conj1)), new=((father,conj2)))
                        duplicateEdge(graph=self, orig=((father,conj1)), new=((father,markerNode)))
                        
                    if conj1.isPredicate:
                        for neighbor in self.neighbors(conj1):
                            if get_min_max_span(self, neighbor)[0] < curStartIndex:
                                for conj2 in curNeighbours[rel]:
                                    if (self.edge_label((conj1,neighbor)) == SOURCE_LABEL) or (not self.is_aux_edge((conj1.uid, neighbor.uid))):
                                        duplicateEdge(graph=self, orig=(conj1,neighbor), new=(conj2,neighbor))
                                    
                # create the coordination construction, headed by the marker
                self.add_edge(edge=(markerNode,conj1),label=rel)
                for conj2 in curNeighbours[rel]:
                    self.del_edge((conj1,conj2))
                    self.add_edge(edge=(markerNode,conj2),label=rel)
                    if conj1.isPredicate:
                        conj2.isPredicate = conj1.isPredicate
                    conj1.surface_form = [w for w in conj1.surface_form if (w not in conj2.surface_form) and (w not in conj1.text) ]
                    for w in conj1.text:
                        if w not in conj1.surface_form:
                            conj1.surface_form.append(w)
                    if conj1.features.get("conjType",False):
                        conj1.text = [w for w in conj1.text if w.index not in conj1.features["conjType"][1]]
                    
            self.types.add(rel)              
         
    
    def do_acomp(self):
        edges = find_edges(self, lambda u_v:self.edge_label(u_v) == "MO" and u_v[0].isPredicate and u_v[1].pos().startswith('ADJ'))
        # doesn't work as a loop, because the merging changes nodes -> recursive
        #for predNode,acompNode in edges:
        if len(edges) > 0:
            predNode = edges[0][0]
            acompNode = edges[0][1]
            neighbors = predNode.neighbors()
            subjs = multi_get(neighbors,subject_dependencies)
            if len(subjs)!=1:
    #                 self.types.add("debug")
                pass
            else:
                if (predNode.text[0].word in self.modalVerbs) or (predNode.features.get("Lemma","") in self.modalVerbs):
                    subj = subjs[0]
                    self.del_edge((predNode,acompNode))
                    self.add_edge((acompNode,subj),label=domain_label)
                    acompNode.isPredicate=True
                    self.del_edge((predNode,subj))
                    duplicate_all_incidents(gr=self, source=predNode, target=acompNode)
                    self.add_edge((acompNode,predNode),label=SOURCE_LABEL)
                    if (len(self.neighbors(predNode))==0) and (len(predNode.text)==1) and (predNode.text[0].word in contractions):
                        self.del_node(predNode)
                    else:
                        self.types.add("acomp_as_modal")
                    self.do_acomp()
                else:
                    self.types.add("acomp_as_mwe")
                    merge_nodes(gr=self, node1=predNode, node2=acompNode)
                    self.do_acomp()
                        
                
    
    def conditional_specific(self,markNode,markFather,advclNode):
        cond_type = markNode.text[0].word.lower()
        self.types.add("conditionals-{0}".format(cond_type))
        # if cond_type in ["falls"]:
            # self.add_edge((markNode,markFather),label=CONDITION_LABEL)
            # self.add_edge((markNode,advclNode),label=OUTCOME_LABEL)
            # if cond_type == "although": # necessary
                # advclNode.makeTopNode()
                # markFather.makeTopNode()
        
        # if cond_type == "because":
            # self.add_edge((markNode,markFather),label=CONDITION_LABEL)
            # self.add_edge((markNode,advclNode),label=OUTCOME_LABEL)
            # advclNode.makeTopNode()
            # markFather.makeTopNode()
        
        # if cond_type in ["while","as","once"]:
            # self.add_edge((markNode,markFather),label=CONDITION_LABEL)
            # self.add_edge((markNode,advclNode),label=OUTCOME_LABEL)
            # if cond_type in ["while","as"]:
                # advclNode.makeTopNode()
                # markFather.makeTopNode()
                
        # default handling
        self.add_edge((markNode,markFather),label=CONDITION_LABEL)
        self.add_edge((markNode,advclNode),label=OUTCOME_LABEL)
                      
    
    def do_conditionals(self):
        applyClosure(self._do_conditionals)
    
    def _do_conditionals(self):
        # find conditionals constructions
        edges = find_edges(self, lambda u_v:(self.edge_label(u_v) == "CP") and u_v[1].pos() in ['KOUS','KOUI'] and (u_v[1].text[0].word.lower() in [u"falls",u"wenn",u"sofern",u"da",u"weil",u"obwohl",u"um",u"waehrend"]))
        for (markFather,markNode) in edges:
            neighbors = markFather.neighbors()
            incidents = markFather.incidents()
            advclNode = False
            if "MO" in incidents:
                advclNode = incidents["MO"][0]
                toDel = (advclNode,markFather)
                head = advclNode
            elif "RE" in incidents:
                reNode = incidents["RE"][0]
                node = reNode
                advclNode = None
                while not advclNode:
                    if len(node.incidents()) == 0:
                        break
                    for r in node.incidents():
                        node = node.incidents()[r][0]
                        if node.isPredicate:
                            advclNode = node
                toDel = (reNode,markFather)
                head = advclNode
            if advclNode:
                if "advcl" in advclNode.incidents(): # necessary?
                    continue
                head = self.head(head)
                self.del_edge((markFather,markNode))
                self.del_edge(toDel)
                if "rcmod" not in head.incidents(): # necessary?
                    for father in self.incidents(head):
                        duplicateEdge(graph=self, orig=(father,head), new=(father,markNode))
                        self.del_edge((father,head))
                self.conditional_specific(markNode, markFather, advclNode)
                markNode.isPredicate = True
                return True
    
    def do_existensials(self):
        edges = find_edges(self, lambda u_v:self.edge_label(u_v) == "EP" and len(self.neighbors(u_v[1])) == 0 and u_v[0].features.get("Lemma") == "geben")
        for u, v in edges:
            self.types.add("existensials")
            u.text = deepcopy(u.text)
            u.text[0].word = EXISTENSIAL
            u.removeLemma()
            u.surface_form += v.surface_form
            u.features["implicit"] = True
            nbs = u.neighbors()
            if "OA" in nbs and len(nbs["OA"]) == 1:
                self.set_edge_label((u,nbs["OA"][0]),"SB")
            self.del_node(v)
    
    def do_passives(self):
        nodes = find_nodes(self,lambda n:n.features.get("Passive Voice",False))
        for n in nodes:
            curNeighbours = n.neighbors()
            for prepBy in multi_get(curNeighbours,["SBP"]):
                agents = prepBy.neighbors()
                for agent in agents['NK']:
                    self.add_edge((n,agent),"SB")
                    agent.original_text.extend(prepBy.original_text)
                    agent.surface_form.extend(prepBy.surface_form)
                self.del_node(prepBy)
            for subjNeigbour in multi_get(curNeighbours, subject_dependencies):
                edge = (n,subjNeigbour)
                self.del_edge(edge)
                self.add_edge(edge,"obj")

            
    def extract_entities(self):
        ret = find_nodes(graph=self, filterFunc=lambda node: (not node.isPredicate) and multi_get(node.incidents(), arguments_dependencies))
        return ret
    

        
    def do_prop(self):
        # prenominal of definite 
        edges = find_edges(self, lambda u_v:self.edge_label(u_v) == "NK")
        for domain, mod in edges:
            if domain.pos() in determined_labels:  # the np by itself is definite
                self.createPropRel(domain=domain, mod=mod)
                mod.features["top"] = True
                self.del_edge((domain, mod))
            
        # copular on adjective or indefinite
        # and sameAs otherwise
        
        # find copular
        #nodes = find_nodes(self, lambda n: len(n.text) == 1 and n.text[0].word in copular_verbs and n.isPredicate)
        #for curNode in nodes:
        for curNode, obj in find_edges(self, lambda edge:self.edge_label(edge) == "PD"):
            if not curNode.uid in self.nodesMap:
                break
            curNeighbours = curNode.neighbors()
            subjs = multi_get(curNeighbours, subject_dependencies)
            #objs = multi_get(curNeighbours, clausal_complements)
            objs = [obj]
            if not objs: objs = multi_get(curNeighbours,["dep"])
            others = [n for n in self.neighbors(curNode) if n not in subjs + objs]
            if (len(objs)>0)and (len(subjs)>0): #and (not others) and (len(objs) == 1): 
                others+=objs[1:]
                if others:
                    self.types.add("complicated BE")
                obj = objs[0]
                if len(objs)>1:
                    self.types.add("debug")
                for subj in subjs:
                    if 'Lemma' in curNode.features: del(curNode.features['Lemma'])
                    if (subj in self.neighbors(obj)):
                        obj.features.update(curNode.features)
                    else:
                        if (not isDefinite(obj)) or (obj.pos() in ["ADJA","ADJD"]):
                            self.createPropRel(domain=subj, mod=obj)
                            head = obj
                            obj.surface_form += curNode.surface_form
                            
                        else:
                            self.types.add("SameAs")
                            self.del_edge((curNode, subj))
                            if self.has_edge((curNode,obj)):
                                self.del_edge((curNode, obj))
#                             self.del_edges([(curNode, subj), (curNode, obj)])
                            copularNode = getCopular(self, curNode.text[0].index, features=curNode.features)
                            copularNode.surface_form = curNode.surface_form
                            self.add_edge((copularNode, subj),
                                          label=FIRST_ENTITY_LABEL)
                            self.add_edge((copularNode, obj),
                                          label=SECOND_ENTITY_LABEL)
                            head = copularNode
                            
                        
                        head.features.update(curNode.features)
                        
                        for curFather in self.incidents(curNode):
                            if not self.has_edge((curFather, head)):
                                duplicateEdge(graph=self, orig=(curFather, curNode), new=(curFather, head))
                                
                        for curOther in others:
                                if not self.has_edge((obj, curOther)):
                                    duplicateEdge(graph=self, orig=(curNode, curOther), new=(head, curOther))
                # erase "be" node
                self.del_node(curNode)
                    
                    
        # find appositions
        for subj, obj in find_edges(self, lambda edge:self.edge_label(edge) == "APP"):
            # duplicate relations
            for curFather in self.incidents(subj):
                curIndex = curFather.features.get("apposIndex", 0) + 1
#                 curLabel = "{0},{1}".format(curIndex,self.edge_label((curFather,subj)))
                curLabel = self.edge_label((curFather, subj))
                self.del_edge((curFather, subj))
                self.add_edge((curFather, subj), curLabel)
                self.add_edge((curFather, obj), curLabel)
                ls = curFather.features.get("dups", [])
                ls.append((subj, obj))
                curFather.features["dups"] = ls
                
                curFather.features["apposIndex"] = curIndex
            # TF: example for this scenario - acomp
            if (not isDefinite(subj) and not isDefinite(obj)) or (obj in subj.neighbors().get("acomp", [])):
                self.createPropRel(domain=subj, mod=obj)
                obj.features["top"] = True
            else:
                # add new node
                # TODO: subj here is a problem - should point to the comma or something
                self.types.add("SameAs")
                copularNode = getCopular(self, subj.text[0].index, features={})
                copularNode.surface_form = []
                self.add_edge((copularNode, subj),
                              label=FIRST_ENTITY_LABEL)
                self.add_edge((copularNode, obj),
                              label=SECOND_ENTITY_LABEL)
                
                    
            self.del_edge((subj, obj))
    
    def to_mctest_representation(self):
        ret = ""
        for node in self.nodes():
            node_text_format = " ".join([w.word for w in sorted(node.text,key=(lambda w:w.index))])
            for neighbor in self.neighbors(node):
                neighbor_text_format = " ".join([w.word for w in sorted(neighbor.text,key=(lambda w:w.index))])
                rel = self.edge_label((node,neighbor))
                ret+=" ".join([node_text_format,rel,neighbor_text_format])+" "
        return ret
    
    def to_latex(self):
        """ outputs a latex figure, uses tikz-dependency package """
        boilerplate_start =r""" \begin{enumerate}
        \setcounter{enumi}{\theenumTemp}
        \item \begin{minipage}[t]{\linewidth}
          \centering
          \adjustbox{valign=t}{%
        \begin{scalebox}{0.8}{
            \begin{dependency}[theme=simple]
        """
        boilerplate_end =r"""  \end{dependency}}
        \end{scalebox}}
        \end{minipage}
        \setcounter{enumTemp}{\theenumi}
        \end{enumerate}
        """

        words = self.originalSentence.split()
        numOfwords = len(words)
        spaces = [r'\&']*numOfwords
        
        slots = dict([(n,min([w.index for w in n.text])) for n in self.nodes()])
        
        reveresed_slots = {v-1:k for k,v in slots.items()}
        
        for i in range(numOfwords):
            if i not in reveresed_slots:
                reveresed_slots[i]=""
            else:
                reveresed_slots[i]=r"\tiny{{\emph{{{0}}}}}".format(reveresed_slots[i].features.get("Tense",""))
        
        tenses = [reveresed_slots[i] for i in range(numOfwords)]
        
        for node in self.nodes():
            ind = node.minIndex()
            for w in node.get_sorted_text()[1:]:
                spaces[w.index-2] = " "
                for n in [n for n in self.nodes() if n.minIndex() > ind]:
                    slots[n] -=1
            
        
        
        # create latex:
        ret = boilerplate_start
        ret+= r"\begin{deptext}[column sep=0.01cm]"
        spaces = [""]+spaces
        curWords = ""
        for i in range(numOfwords):
            curSpace = spaces[i]
            if (curSpace.strip()):
                if len(curWords.rstrip().lstrip().split())>1:
                    ret += r"$\underbracket{{\text{{{0}}}}}$".format(tex_escape(curWords.lstrip()))
                else:
                    ret += tex_escape(curWords)
                ret += " "+curSpace
                curWords = ""
            curWords += " "+words[i]
        if curWords:
            if len(curWords.rstrip().lstrip().split())>1:
                ret += r"$\underbracket{{\text{{{0}}}}}$".format(tex_escape(curWords.lstrip()))
            else:
                ret += tex_escape(curWords)
        ret += r"\\"
                
                
                
            
            
#         ret += " ".join([" ".join([x,y]) for x,y in zip(spaces,words)])+r"\\"
        ret += " ".join([" ".join([x,y]) for x,y in zip(spaces,tenses)])+r"\\"            
        ret += r"\end{deptext}"
        
        for u, v in self.edges():
            ret += "\\depedge{{{0}}}{{{1}}}{{{2}}}\n".format(slots[u],slots[v],tex_escape(self.edge_label((u, v))))
    
        
        ret += boilerplate_end
        return ret

            
def applyClosure(func):
    ret = True
    while ret:
        ret = func()
    
    
def dumpGraphsToTexFile(graphs, appendix, graphsPerFile, lib, outputType='pdf'):
    """
    Write graphs to pdf files, possibly containing some appendix

    @type  graphs: list of GraphWrapper
    @param graphs: the graphs to be written to file

    @type  appendix: a dictionary from String to list of ints
    @param appendix: a mapping between a type (for instance "apposition") and graph indices within the list graphs

    @type  graphsPerFile: int
    @param graphsPerFile: how many graphs to write to each file

    @type  lib: String
    @param lib: target library in which pdf files will be written
    """

    imageType = {"html":"svg",
                "pdf":"png"}[outputType]


    PDF = (outputType == "pdf")
    HTML = (outputType == "html")


    BOILER_START = """
    \\documentclass[11pt,letterpaper]{article}
    \\usepackage{xcolor}
    \\usepackage{hyperref}
    \\usepackage[all]{hypcap}
    \\usepackage[pdftex]{graphicx}
    \\hypersetup{colorlinks=false,linkbordercolor=blue,linkcolor=green,pdfborderstyle={/S/U/W 1}}
    \\begin{document}
    \\title{TBD Representation}
    \\section{TOC}\\label{toc}
    """

    if HTML:
        BOILER_START = """
        <html>
        <title>TBD Representation</title>
        <p align="right">Last updated on {0}</p>
        <A name="TOC"><h1>TOC</h1></A>
        """.format(time.strftime("%d/%m/%y %H:%M"))


    FIGURE = """
    \\begin{{figure}}
    \\label{{fig:{0}}}
    \\centering
    \\includegraphics[width=15cm,height=10cm,keepaspectratio]{{{0}.""" + imageType + """}}
    \\caption{{{1}}}
    \\end{{figure}}
    \\hyperref[toc]{{Back to TOC}}
    """

    if HTML:
        FIGURE = """
        <figure>
        <img src='{0}.svg' alt='missing' />
        </figure>
        """

    BOILER_END = """
    \\end{document}
    """

    if HTML:
        BOILER_END = """
        <br><br><br>
        </html>
        """


    print("dumping to file...")
    numOfGraphs = len(graphs)
    iterCount = int(math.ceil(numOfGraphs / float(graphsPerFile)))
    for r in range(iterCount):
        curRange = range(graphsPerFile * r, min(graphsPerFile * (r + 1), numOfGraphs))
        filename = "autogen" + unicode(r) + ".tex"
        if HTML:
            filename = "autogen" + unicode(r) + ".html"
        fout = open(lib + filename, 'w')
        fout.write(BOILER_START)

        # write TOC:
        for key in sorted(appendix):
            if PDF:
                fout.write("\\subsection{{{0}}}\n".format(key))
            elif HTML:
                fout.write("<h2>{0}</h2>\n".format(key))

            for indind, curInd in enumerate(filter(lambda x:x in curRange, appendix[key])):
                if PDF:
                    fout.write("\\hyperref[fig:{0}]{{{1}}}$\\;$\n".format(curInd,
                                                               tex_escape(graphs[curInd].gTag.tree.report())))
                elif HTML:
                    fout.write("<A href={0}.svg>{1}</A>        ".format(curInd,
                                                              indind + 1))

        if PDF:
            fout.write("\\newpage")
        if HTML:
            fout.write("<br><br><br>")
        for i, g in enumerate(graphs[graphsPerFile * r:min(graphsPerFile * (r + 1), numOfGraphs)]):
            curPicInd = (graphsPerFile * r) + i
            g.drawToFile(filename=lib + unicode(curPicInd),
                         filetype=imageType)

            if PDF:
                fout.write(FIGURE.format(unicode(curPicInd),
                                     tex_escape(g.originalSentence)))
            if HTML:
                fin = open(lib + unicode(curPicInd) + ".svg")
                fout.write(fin.read() + "<br>")
                fin.close()
                fout.write('<font size="5">')
                fout.write('<br>'.join([unicode(prop) for prop in graphs[curPicInd].getPropositions(outputType)]))
                fout.write("</font><br><br>")



            if PDF:
                fout.write("\\clearpage")

        print ("finished " + unicode(r))
        fout.write(BOILER_END)
        fout.close()
        if PDF:
            subprocess.Popen([lib + "..\\compile.bat", filename])


def html_escape(text):
    return cgi.escape(text).encode('ascii', 'xmlcharrefreplace')

def tex_escape(text):
    """
        :param text: a plain text message
        :return: the message escaped to appear correctly in LaTeX
    """
    conv = {
        '&': r'\&',
        '%': r'\%',
        '$': r'\$',
        '#': r'\#',
        '_': r'\_',
        '{': r'\{',
        '}': r'\}',
        '~': r'\textasciitilde{}',
        '^': r'\^{}',
        '\\': r'\textbackslash{}',
        '<': r'\textless',
        '>': r'\textgreater',
    }
    regex = re.compile('|'.join(re.escape(unicode(key)) for key in sorted(conv.keys(), key=lambda item:-len(item))))
    return regex.sub(lambda match: conv[match.group()], text)
    

def duplicate_all_incidents(gr,source,target):
    """
    move all source's incidents to point to targe
    """
    
    for curFather in gr.incidents(source):
        if not gr.has_edge((curFather,target)):
            duplicateEdge(graph=gr, orig=(curFather,source), new=(curFather,target))
            gr.del_edge((curFather,source))
