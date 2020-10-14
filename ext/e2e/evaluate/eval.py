from arcs_inferred_antecedents import evaluate
r, p, f1 = evaluate("../data/test_data", "../data/final_test_results.conll")
print("r:", r, "p:", p, "f1:", f1)
