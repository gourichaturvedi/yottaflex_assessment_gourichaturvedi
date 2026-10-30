import json
from pathlib import Path
from datetime import datetime
from .services import Settings,validate_route_stops

def decide_scenarios(inputs_path="data/scenarios/edge_case_inputs.json"):
    # Business decisions use fixture facts only. Ground-truth labels are evaluated later.
    fixtures=json.loads(Path(inputs_path).read_text(encoding="utf-8"))["scenarios"]; results=[]
    for item in fixtures:
        sid=item["scenario_id"]; f=item["fixture"]
        if sid=="SCN-CAPACITY": detected=f["occupancy"]+f["candidate_seats"]>f["capacity"]; issue="CAPACITY_EXCEEDED"; action="REJECT" if detected else "ACCEPT"
        elif sid=="SCN-ACCESSIBILITY": detected=f["accessibility_required"] and (not f["bus_accessible"] or not f["stop_accessible"]); issue="ACCESSIBILITY_MISMATCH"; action="REJECT" if detected else "ACCEPT"
        elif sid=="SCN-TRAVEL": detected=datetime.strptime(f["next_arrival"],"%H:%M")<datetime.strptime(f["previous_departure"],"%H:%M")+__import__('datetime').timedelta(minutes=f["travel_minutes"]); issue="IMPOSSIBLE_TRAVEL_TIME"; action="MARK_INFEASIBLE" if detected else "KEEP_FEASIBLE"
        elif sid=="SCN-CONTACT": detected=not(f["active"] and f["verified"] and f["consent"] and f["email"].endswith("@example.invalid")); issue="INVALID_GUARDIAN_CONTACT"; action="SUPPRESS" if detected else "SIMULATED_SEND"
        else: detected=not f["approved"]; issue="UNAPPROVED_ADDRESS_EXPOSURE"; action="REDACT_AND_AUDIT" if detected else "ALLOW_APPROVED_VIEW"
        results.append({"scenario_id":sid,"issue_type":issue,"affected_entity_ids":[sid],"detected":detected,"observed_action":action,"evidence_references":["data/scenarios/edge_case_inputs.json#"+sid]})
    return results

def evaluate_scenarios(inputs_path="data/scenarios/edge_case_inputs.json",truth_path="data/ground_truth/edge_case_ground_truth.json"):
    results=decide_scenarios(inputs_path); truth=json.loads(Path(truth_path).read_text(encoding="utf-8"))
    for item in results:
        expected=truth[item["scenario_id"]]; item["expected_action"]=expected["expected_action"]; item["pass"]=item["issue_type"]==expected["issue_type"] and item["observed_action"]==expected["expected_action"] and item["detected"]
    return results
