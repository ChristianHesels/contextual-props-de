from neo4j import GraphDatabase
from pygraph.classes.digraph import digraph
from collections import defaultdict
import re
coreference_map = defaultdict(list)

coreference_head = {}

coreference_id_list = []


def _create_node(tx, uid, label, coreference):
    tx.run("CREATE (e:Node {label: $label, uid: $uid, coreference: $coreference}) RETURN e", label=label, uid=uid, coreference=coreference)
    
def _create_edge(tx, src, dst, label):
    tx.run("MATCH (src:Node), (dst:Node) WHERE src.uid = $src AND dst.uid = $dst MERGE (src)-[r:edge {label: $label}]->(dst)", src=src, dst=dst, label=label)
    
def _delete_all(tx):
    tx.run("MATCH (n) DETACH DELETE n")

def create_node(driver, uid, label, coreference=None):
    with driver.session() as session:
        session.write_transaction(_create_node, uid, label, coreference)
            
def create_edge(driver, src, dst, label):
    with driver.session() as session:
        session.write_transaction(_create_edge, src, dst, label)
    
def delete_all(driver):
    with driver.session() as session:
        session.write_transaction(_delete_all)

def _is_head_node(node):
    if node.pos() == "NN"or node.pos() == "NE":
        return True
    else:
        return False

def _add_coreference_heads_for_graph(graph, coreference_heads):
    coreference_nodes = []
    coref_ids = []

    for node in graph:
        if node.coreference:
            coreference_nodes.append(node)
    for node in coreference_nodes:
        coref_id = int(re.findall(r'\d+', node.coreference)[0])
        
        if coref_id not in coref_ids:
            if _is_head_node(node):
                coref_ids.append(coref_id)
                coreference_heads[coref_id] = node.uid
                
def _is_part_of_initial_coreference(nodes, uid, coreference_map):
    current_node = nodes[uid]
    if current_node.coreference:
        coref_id = int(re.findall(r'\d+', current_node.coreference)[0])

        if coref_id not in coreference_map:
            coreference_map[coref_id].append(current_node.coreference)
            return True
        else:
            is_finished = False
            for coref in coreference_map[coref_id]:
                if coref[-1] == ")":
                    is_finished = True
            if not is_finished:
                if current_node.coreference:
                    coreference_map[coref_id].append(current_node.coreference)
                return True
            else:
                return False

def merge_graphs_and_write_to_neo4j(graphs, username, password):
    uri = "bolt://localhost:7687"
    driver = GraphDatabase.driver(uri, auth=(username, password))
    delete_all(driver)
    coreference_heads = {}
    added_coreference_nodes = []
    coreference_map = defaultdict(list)
    id_count = 0
    for graph, tree in graphs:
        nodes = graph.nodesMap
        _add_coreference_heads_for_graph(graph, coreference_heads)

        for uid in nodes:
            node = nodes[uid]
            # NODE
            label = str(node.text[0])
            
            if node.coreference and _is_part_of_initial_coreference(nodes, uid, coreference_map):
                create_node(driver, uid, label, node.coreference)   
                added_coreference_nodes.append(uid)
            elif not node.coreference:
                create_node(driver, uid, label, node.coreference)
            
        # EDGE
        for (src, dst) in digraph.edges(graph):
            label = str(graph.edge_label((src, dst)))
            if label:
                coref_id = None
                if nodes[src].coreference and dst not in added_coreference_nodes:
                    coref_id = int(re.findall(r'\d+', nodes[src].coreference)[0])
                    create_edge(driver, coreference_heads.get(coref_id, src), dst, label) 
                elif nodes[dst].coreference and src not in added_coreference_nodes:
                    coref_id = int(re.findall(r'\d+', nodes[dst].coreference)[0])
                    create_edge(driver, src, coreference_heads.get(coref_id, dst), label) 
                else:
                    create_edge(driver, src, dst, label)