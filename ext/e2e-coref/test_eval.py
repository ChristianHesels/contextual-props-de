import sys

sys.path.insert(1, 'evaluate')
from arcs_immediate_antecedents import evaluate
print(evaluate("data/processed_eval_data.conll", "/tmp/tmp7fr0z_e0"))