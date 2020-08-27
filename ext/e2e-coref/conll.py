from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import re
import os
import sys
sys.path.insert(1, 'evaluate')
from arcs_inferred_antecedents import evaluate
import json
import tempfile
import subprocess
import operator
import collections

BEGIN_DOCUMENT_REGEX = re.compile(r"#begin document \((.*)\); part (\d+)")
BEGIN_TUEBADZ_DOCUMENT_REGEX = re.compile(r"#begin document")
COREF_RESULTS_REGEX = re.compile(r".*Coreference: Recall: \([0-9.]+ / [0-9.]+\) ([0-9.]+)%\tPrecision: \([0-9.]+ / [0-9.]+\) ([0-9.]+)%\tF1: ([0-9.]+)%.*", re.DOTALL)

def get_doc_key(doc_id, part):
  return "{}_{}".format(doc_id, int(part))

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
    elif row[0].startswith("#"):
      if line.startswith("#begin"):
        doc_key = line[16:].replace("\n", "")
        start_map, end_map, word_map = prediction_map[doc_key]
        word_index = 0
      output_file.write(line)
      if not line.startswith("#begin") and not line.startswith("#end"):    
          output_file.write("\n")
    else:
      if row[0] != doc_key:
        print(row, doc_key)
        assert row[0] == doc_key
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

      output_file.write("   ".join(row))
      output_file.write("\n")
      word_index += 1

def official_conll_eval(gold_path, predicted_path, metric, official_stdout=False):
    
  cmd = ["conll-2012/scorer/v8.01/scorer.pl", metric, gold_path, predicted_path, "none"]
  process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
  stdout, stderr = process.communicate()
  process.wait()

  stdout = stdout.decode("utf-8")
  if stderr is not None:
    print(stderr)

  if official_stdout:
    print("Official result for {}".format(metric))
    print(stdout)

  coref_results_match = re.match(COREF_RESULTS_REGEX, stdout)
  print(coref_results_match)

  recall = float(coref_results_match.group(1))
  precision = float(coref_results_match.group(2))
  f1 = float(coref_results_match.group(3))
  return { "r": recall, "p": precision, "f": f1 }

def evaluate_conll(gold_path, predictions, official_stdout=False):
  with tempfile.NamedTemporaryFile(delete=False, mode="w") as prediction_file:
    with open(gold_path, "r") as gold_file:
      output_conll(gold_file, prediction_file, predictions)
          
    print("Predicted conll file: {}".format(prediction_file.name))
  return { m: official_conll_eval(gold_file.name, prediction_file.name, m, official_stdout) for m in ("muc", "bcub", "ceafe") }

def evaluate_conll_arcs(gold_path, predictions):
  with tempfile.NamedTemporaryFile(delete=False, mode="w") as prediction_file:
    with open(gold_path, "r") as gold_file:
      output_conll(gold_file, prediction_file, predictions)
          
  print("Predicted conll file: {}".format(prediction_file.name))
  return arcs_eval(gold_path, prediction_file.name)

def arcs_eval(gold_path, predicted_path):
    r, p, f1 = evaluate(gold_path, predicted_path)
    return r, p, f1
