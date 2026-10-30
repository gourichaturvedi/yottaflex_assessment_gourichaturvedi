from transport_ops.services import generate
from transport_ops.validation import validate_database
from transport_ops.scenarios import evaluate_scenarios,decide_scenarios

def test_all_isolated_scenarios_match_ground_truth():
    results=evaluate_scenarios()
    assert len(results)==5 and all(x["pass"] for x in results)
    assert all("expected_action" not in x for x in decide_scenarios())

def test_generated_baseline_is_valid(tmp_path):
    db=tmp_path/"ops.sqlite"; generate(str(db),"starter",20261022)
    report=validate_database(str(db))
    assert report["valid"],report
