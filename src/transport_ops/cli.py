import argparse,json,tempfile
from pathlib import Path
from datetime import date
from .services import generate,export,simulate_history
from .validation import validate_database
from .scenarios import evaluate_scenarios

def main():
    p=argparse.ArgumentParser(prog="transport-ops"); sub=p.add_subparsers(dest="command",required=True)
    g=sub.add_parser("generate"); g.add_argument("--scale",choices=["starter","full"],default="starter"); g.add_argument("--seed",type=int,default=20261022); g.add_argument("--database"); g.add_argument("--start-date",default="2026-01-05")
    v=sub.add_parser("validate"); v.add_argument("--database",required=True)
    sc=sub.add_parser("scenarios"); sc.add_argument("--database")
    rp=sub.add_parser("reproduce"); rp.add_argument("--scale",choices=["starter","full"],default="starter"); rp.add_argument("--seed",type=int,default=20261022)
    ex=sub.add_parser("export"); ex.add_argument("--database",required=True); ex.add_argument("--output")
    sim=sub.add_parser("simulate"); sim.add_argument("--database",required=True); sim.add_argument("--days",type=int,default=1); sim.add_argument("--seed",type=int,default=20261022)
    a=p.parse_args()
    if a.command=="generate":
        path=a.database or f"data/generated/run_{a.seed}_{a.scale}/transport_ops.sqlite"; print(json.dumps({"database":path,**generate(path,a.scale,a.seed,start=date.fromisoformat(a.start_date))},indent=2))
    elif a.command=="validate": print(json.dumps(validate_database(a.database),indent=2))
    elif a.command=="scenarios": print(json.dumps(evaluate_scenarios(),indent=2))
    elif a.command=="export": print(json.dumps(export(a.database,a.output or str(Path(a.database).parent)),indent=2))
    elif a.command=="simulate": print(json.dumps(simulate_history(a.database,a.days,a.seed),indent=2))
    elif a.command=="reproduce":
        root=Path("data/generated/reproducibility"); root.mkdir(parents=True,exist_ok=True)
        one=root/"first"/"transport_ops.sqlite"; two=root/"second"/"transport_ops.sqlite"
        generate(str(one),a.scale,a.seed); generate(str(two),a.scale,a.seed)
        ma=json.loads((one.parent/"manifest.json").read_text()); mb=json.loads((two.parent/"manifest.json").read_text())
        report={"seed":a.seed,"scale":a.scale,"row_counts_equal":ma["row_counts"]==mb["row_counts"],"checksums_equal":ma["content_checksums"]==mb["content_checksums"],"first_checksums":ma["content_checksums"],"second_checksums":mb["content_checksums"]}
        report["equal"]=report["row_counts_equal"] and report["checksums_equal"]; (root/"reproducibility_report.json").write_text(json.dumps(report,indent=2)); print(json.dumps(report,indent=2))

if __name__=="__main__": main()
