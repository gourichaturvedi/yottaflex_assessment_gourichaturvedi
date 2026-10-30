from transport_ops.services import generate
from transport_ops.metrics import metrics_snapshot

def test_metrics_derive_from_persisted_records(tmp_path):
    db=tmp_path/"ops.sqlite"; result=generate(str(db),"starter",20261022)
    m=metrics_snapshot(str(db))
    assert m["students_total"]==250
    assert m["assigned_students"]==result["assignments"]
    assert m["capacity_violations"]==0
    assert m["assignment_coverage_pct"]<=1
