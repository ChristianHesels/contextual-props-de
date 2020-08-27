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

        
def _add_coreference_heads_for_graph(graph, coreference_heads):
    for u_v in graph.edges():
        no_coreference = False
        for edge in u_v:
            if not edge.coreference:
                no_coreference = True
            elif no_coreference:
                if edge.coreference:
                    coref_id = int(re.findall(r'\d+', edge.coreference)[0])
                    if coref_id not in coreference_heads:
                        coreference_heads[coref_id] = edge.uid
                    elif edge.uid < coreference_heads[coref_id]:
                        coreference_heads[coref_id] = edge.uid
    return coreference_heads
    

def _is_part_of_initial_coreference(nodes, uid):
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

def write_graphs_to_neo4j(graphs, username, password):
    uri = "bolt://localhost:7687"
    driver = GraphDatabase.driver(uri, auth=(username, password))
    delete_all(driver)
    coreference_heads = {}
    added_coreference_nodes = []
    for graph, tree in graphs:
        nodes = graph.nodesMap
        _add_coreference_heads_for_graph(graph, coreference_heads)
        for uid in nodes:
            node = nodes[uid]
            # NODE
            label = str(node.text[0])
            if node.isPredicate:
                # is predicate
                pass
            if node.features.get("top", False):
                # is top
                pass
            
            # Remove Punctuation Marks
            if len(label) > 0:
                if node.coreference and _is_part_of_initial_coreference(nodes, uid):
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
    driver.close()
                    
