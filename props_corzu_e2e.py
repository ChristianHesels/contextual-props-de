import os, sys, codecs, time, datetime
import fileinput
import os.path
import stanza
from io import StringIO
from subprocess import call
import urllib.request
import urllib.parse

import codecs, os, sys
from propsde.dependency_tree.tree_readers import *
from propsde.dependency_tree.german_parser import ParserDE
from propsde.graph_representation.graph_wrapper import GraphWrapper
from propsde.graph_representation.convert import convert
from docopt import docopt
from propsde.graph_representation import proposition
from propsde.applications.viz_tree import DepTreeVisualizer
import os
import nltk
import tensorflow as tf
nltk.download("punkt")
from nltk.tokenize import sent_tokenize, word_tokenize

import sys
import collections
import operator

sys.path.append('ext/e2e')
import coref_model as cm
import util
from neo4j_con import merge_graphs_and_write_to_neo4j
if len(sys.argv) > 1:
    coref_parser = sys.argv[1]
else: 
    print("Choose Coreference Parser (corzu or e2e).")
    exit(1)
parser = None

def parse_conll_with_props(file):
    global parser
    parser = ParserDE(False)

    # read and process output
    graphs = read_dep_graphs(None, file)
    
    ret = []
    i = 0
    for graph in graphs:  
        g = convert(graph)
        print("\n")
        print("------------------------------")
        print("-------PropsDE Results-------:")
        print("------------------------------")
        for props in g.getPropositions('pdf'):
            print(props)
            print("\n")
        ret.append((g,g.tree_str))
        i += 1

    if not graphs:#Berkley bug?
        ret.append((GraphWrapper("",""),""))

        
    return ret

if sys.version_info[0] >= 3:
    unicode = str



def parse_dependencies_to_conll_file(text, path):
    params = {
        "text": text,
        "format": "conll"
    }
    args = urllib.parse.urlencode(params).encode("utf-8")
    req = "http://localhost:5003/parse/?"+args.decode("utf-8")
    try:
        f = urllib.request.urlopen(req)
        if path:
            file = open(path,'w')
            file.write(f.read().decode('utf-8'))
        else:
            print(f.read().decode('utf-8'))
        return 0
    except Exception as ex:
        print(ex)
        return 1
    

def umlaut(word):
    tempVar = word.lower()
    tempVar = tempVar.replace('ä', 'ae')
    tempVar = tempVar.replace('ö', 'oe')
    tempVar = tempVar.replace('ü', 'ue')
    tempVar = tempVar.replace('Ä', 'Ae')
    tempVar = tempVar.replace('Ö', 'Oe')
    tempVar = tempVar.replace('Ü', 'Ue')
    tempVar = tempVar.replace('ß', 'ss')
    return tempVar

def create_example(text):
  raw_sentences = sent_tokenize(text)
  sentences = [word_tokenize(s) for s in raw_sentences]
  speakers = [["" for _ in sentence] for sentence in sentences]
  return {
    "doc_key": 0,
    "clusters": [],
    "sentences": sentences,
    "speakers": speakers,
  }

def make_predictions(text, model):
  example = create_example(text)
  tensorized_example = model.tensorize_example(example, is_training=False)
  feed_dict = {i:t for i,t in zip(model.input_tensors, tensorized_example)}
  candidate_starts, candidate_ends, candidate_mention_scores, top_span_starts, top_span_ends, top_antecedents, top_antecedent_scores = session.run(model.predictions, feed_dict=feed_dict)
  predicted_antecedents = model.get_predicted_antecedents(top_antecedents, top_antecedent_scores)
  predicted_clusters, mention_to_predicted = model.get_predicted_clusters(top_span_starts, top_span_ends, predicted_antecedents)
    
  return {"p": predicted_clusters}

def print_predictions(example):
  words = util.flatten(example["sentences"])
  for cluster in example["predicted_clusters"]:
    print(u"Predicted cluster: {}".format([" ".join(words[m[0]:m[1]+1]) for m in cluster]))
    

    
    
def output_conll(input_file, output_file, predictions):
  prediction_map = {}
  for doc_key, clusters in predictions.items():
    start_map = collections.defaultdict(list)
    end_map = collections.defaultdict(list)
    word_map = collections.defaultdict(list)
    for cluster_id, mentions in enumerate(clusters):
      for start, end in mentions:
        if start == end:
          word_map[start].append(cluster_id)
        else:
          start_map[start].append((cluster_id, end))
          end_map[end].append((cluster_id, start))
    for k,v in start_map.items():
      start_map[k] = [cluster_id for cluster_id, end in sorted(v, key=operator.itemgetter(1), reverse=True)]
    for k,v in end_map.items():
      end_map[k] = [cluster_id for cluster_id, start in sorted(v, key=operator.itemgetter(1), reverse=True)]
    prediction_map[doc_key] = (start_map, end_map, word_map)

  word_index = 0
  for line in input_file.readlines():
    row = line.split()
    if len(row) == 0:
      output_file.write("\n")
    else:
      coref_list = []
      if word_index in end_map:
        for cluster_id in end_map[word_index]:
          coref_list.append("{})".format(cluster_id))
      if word_index in word_map:
        for cluster_id in word_map[word_index]:
          coref_list.append("({})".format(cluster_id))
      if word_index in start_map:
        for cluster_id in start_map[word_index]:
          coref_list.append("({}".format(cluster_id))

      if len(coref_list) == 0:
        row[-1] = "-"
      else:
        row[-1] = "|".join(coref_list)

      output_file.write("\t".join(row))
      output_file.write("\n")
      word_index += 1

if coref_parser == "e2e":
    sys.argv[1] = "props"
    config = util.initialize_from_env()
    model = cm.CorefModel(config)
    
if coref_parser == "corzu":
    output = "corzu_export"
    conll = "corzu.conll"
    markables = "markables"
    print("Using", coref_parser + ".")
    while True:
        text = input("Enter example text: ")
        print("Parsing example text to conll file")
        err = parse_dependencies_to_conll_file(text, conll)
        print("Error:", err)
        if err == 0:
            print("Extract mables from ParZu")
            cmd = "python ext/CorZu_v2.0/extract_mables_from_parzu.py " + conll + " > " + markables
            err = os.system(cmd)
            print("Error:", err)
        
        print("Using CorZu for Coreference Resolution ")
        cmd = "python ext/CorZu_v2.0/corzu.py " + markables + " " + conll + " " + output    
        err = os.system(cmd)
        print("Error:", err)
        print("Using Props DE to parse Output")

        gs = parse_conll_with_props(output)
        
        print("\n")
        print("------------------------------")
        print("--------CorZu Results--------:")
        print("------------------------------")
        with open(output, "r") as output_file:
            for line in output_file.readlines():
                print(line.rstrip('\n'))
        print("\n")
        print("Write results to neo4j")
        merge_graphs_and_write_to_neo4j(gs, "neo4j", "852963")

elif coref_parser == "e2e":
    print("Using", coref_parser + ".")
    conll = "e2e.conll"
    output = "e2e_export"
    
    with tf.Session() as session:
        model.restore(session)
        while True:
            text = input("Enter example text: ")
            print("Parsing example text to conll file")
            err = parse_dependencies_to_conll_file(text, conll)
            print("Error:", err)
            if err == 0:
                text = umlaut(text)	
                example = create_example(text)
                predictions = make_predictions(text, model)
                
                with open(output, "w") as output_file:
                    with open(conll, "r") as input_file:
                        output_conll(input_file, output_file, predictions)
                    print("Using Props DE to parse Output")
                gs = parse_conll_with_props(output)
                print("\n")
                print("------------------------------")
                print("------E2E-German Results-----:")
                print("------------------------------")
                with open(output, "r") as output_file:
                    for line in output_file.readlines():
                        print(line.rstrip('\n'))
                print("\n")
                print("Write results to neo4j")
                merge_graphs_and_write_to_neo4j(gs, "neo4j", "852963")                   
else:
    print("Choose a parser (either corzu, e2e)")
