import json
from pathlib import Path
from transport_ops.services import generate

def test_seeded_content_checksums_repeat(tmp_path):
    one=tmp_path/"one"/"ops.sqlite"; two=tmp_path/"two"/"ops.sqlite"
    generate(str(one),"starter",20261022); generate(str(two),"starter",20261022)
    a=json.loads((one.parent/"manifest.json").read_text()); b=json.loads((two.parent/"manifest.json").read_text())
    assert a["row_counts"]==b["row_counts"]
    assert a["content_checksums"]==b["content_checksums"]
    assert a["seed"]==20261022

def test_different_seed_changes_generated_content(tmp_path):
    one=tmp_path/"one"/"ops.sqlite"; two=tmp_path/"two"/"ops.sqlite"
    generate(str(one),"starter",101); generate(str(two),"starter",102)
    a=json.loads((one.parent/"manifest.json").read_text()); b=json.loads((two.parent/"manifest.json").read_text())
    assert a["row_counts"]==b["row_counts"]
    assert a["content_checksums"]!=b["content_checksums"]
