import os, sys, codecs, time, datetime
import fileinput
import os.path
import stanza
from io import StringIO
from subprocess import call
import urllib.request
import urllib.parse

from docopt import docopt
from propsde.applications.viz_tree import DepTreeVisualizer
import propsde.applications.run as run
import sys
sys.path.insert(1, 'neo4j')
from neo4j_con import write_graphs_to_neo4j
output = "corzu_export"
conll = "parsed.conll"
markables = "markables"

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
    
import os

text = input("Enter example text: ")

print("Parsing example text to conll file")
err = parse_dependencies_to_conll_file(text, conll)

if err == 0:
    cmd = "python ext/CorZu_v2.0/extract_mables_from_parzu.py " + conll + " > " + markables
    err = os.system(cmd)
    print("Error:", err)
    
print("Using CorZu for Coreference Resolution")
cmd = "python ext/CorZu_v2.0/corzu.py " + markables + " " + conll + " " + output    
err = os.system(cmd)
print("Error:", err)

gs = run.parseSentences(text)

print("Write results to neo4j")
write_graphs_to_neo4j(gs, "neo4j", "852963")
