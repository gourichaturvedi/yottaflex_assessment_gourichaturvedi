import re

PATTERNS = {
    "student": r"^STU-\d{6}$", "stop": r"^STOP-\d{6}$", "bus": r"^BUS-\d{6}$",
    "route": r"^ROUTE-2026-\d{6}$", "assignment": r"^ASN-STU-\d{6}-2026(?:-V\d{2})?$",
    "notification": r"^NOT-2026-\d{6}$", "zone": r"^ZONE-\d{6}$", "guardian": r"^GUA-\d{6}$",
    "driver": r"^DRV-\d{6}$", "route_stop": r"^RSTOP-\d{6}$", "attendance": r"^ATT-2026-\d{6}$",
    "capacity_event": r"^BCE-2026-\d{6}$", "disruption": r"^RDE-2026-\d{6}$", "audit": r"^AUD-2026-\d{6}$",
}

def make_id(kind: str, number: int, student_id: str | None = None) -> str:
    if number < 1: raise ValueError("ID sequence starts at 1")
    if kind == "assignment":
        if not student_id: raise ValueError("student_id required")
        return f"ASN-{student_id}-2026" if number == 1 else f"ASN-{student_id}-2026-V{number:02d}"
    prefixes = {"student":"STU", "stop":"STOP", "bus":"BUS", "zone":"ZONE", "guardian":"GUA", "driver":"DRV", "route_stop":"RSTOP"}
    if kind in prefixes: return f"{prefixes[kind]}-{number:06d}"
    yearly = {"route":"ROUTE", "notification":"NOT", "attendance":"ATT", "capacity_event":"BCE", "disruption":"RDE", "audit":"AUD"}
    if kind in yearly: return f"{yearly[kind]}-2026-{number:06d}"
    raise ValueError(f"Unknown ID kind: {kind}")

def valid_id(kind: str, value: str) -> bool:
    return bool(re.fullmatch(PATTERNS[kind], value))
