from __future__ import annotations
import hashlib, json, math, random
from datetime import date, datetime, time, timedelta
from pathlib import Path
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from .config import Settings, STARTER, FULL
from .ids import make_id
from .models import *

FIRST=("Avery","Blake","Casey","Devon","Emery","Finley","Gray","Harper","Indigo","Jordan","Kai","Logan")
LAST=("Arden","Bennett","Carter","Dawson","Ellis","Franklin","Gale","Hayes","Irving","Jensen","Kim","Lane")

def service_dates(start: date, count: int) -> list[date]:
    days=[]; d=start
    while len(days)<count:
        if d.weekday()<5: days.append(d)
        d+=timedelta(days=1)
    return days

def distance_km(x1,y1,x2,y2): return math.hypot(x1-x2,y1-y2)
def travel_minutes(distance: float, settings: Settings) -> int:
    return math.ceil(distance*settings.road_distance_factor/settings.average_speed_kmh*60)

def validate_route_stops(stops: list[RouteStop], settings: Settings):
    ordered=sorted(stops,key=lambda x:x.sequence_no); errors=[]
    if [x.sequence_no for x in ordered]!=list(range(1,len(ordered)+1)): errors.append("INVALID_SEQUENCE")
    for i,item in enumerate(ordered):
        arr=datetime.strptime(item.planned_arrival_time,"%H:%M"); dep=datetime.strptime(item.planned_departure_time,"%H:%M")
        if arr>dep: errors.append(f"ARRIVAL_AFTER_DEPARTURE:{item.route_stop_id}")
        if item.travel_minutes_from_previous<0: errors.append(f"NEGATIVE_TRAVEL:{item.route_stop_id}")
        if i and arr < datetime.strptime(ordered[i-1].planned_departure_time,"%H:%M")+timedelta(minutes=item.travel_minutes_from_previous): errors.append(f"IMPOSSIBLE_TRAVEL_TIME:{item.route_stop_id}")
    if ordered:
        first=datetime.strptime(ordered[0].planned_arrival_time,"%H:%M"); last=datetime.strptime(ordered[-1].planned_departure_time,"%H:%M")
        if (last-first).total_seconds()/60>settings.max_route_duration_minutes: errors.append("MAX_DURATION_EXCEEDED")
    return errors

def build_routes(session: Session, settings: Settings):
    buses=session.scalars(select(Bus).order_by(Bus.bus_id)).all(); drivers=session.scalars(select(Driver).where(Driver.active==True).order_by(Driver.driver_id)).all()
    stops=session.scalars(select(Stop).where(Stop.approved==True,Stop.status=="ACTIVE").order_by(Stop.stop_id)).all()
    dates=service_dates(settings.start_date,1); day=dates[0].isoformat()
    route_stops=[]; routes=[]
    groups=[stops[i*len(stops)//len(buses):(i+1)*len(stops)//len(buses)] for i in range(len(buses))]
    target_links=max(len(stops),min(300,len(buses)*3))
    extras=max(0,target_links-len(stops))
    for recipient in range(len(groups)):
        if extras<=0: break
        if len(groups[recipient])>=math.ceil(len(stops)/len(groups)): continue
        for donor in range(len(groups)):
            candidate=next((x for x in groups[donor] if donor!=recipient and x not in groups[recipient]),None)
            if candidate is not None:
                groups[recipient].append(candidate); extras-=1; break
    for i,bus in enumerate(buses):
        driver=drivers[i]
        group=groups[i]
        rx=((i%5)-2)*2.5; ry=((i//5)-1)*2.0
        route=Route(route_id=make_id("route",i+1),route_name=f"Synthetic Route {i+1:03d}",bus_id=bus.bus_id,driver_id=driver.driver_id,depot_x_km=rx,depot_y_km=ry,planned_start_time="07:00",max_duration_minutes=settings.max_route_duration_minutes,effective_from=day,effective_to=None,status="FEASIBLE")
        routes.append(route); clock=420; px,py=rx,ry
        for j,stop in enumerate(group,1):
            mins=travel_minutes(distance_km(px,py,stop.x_km,stop.y_km),settings); clock+=mins
            arr=time(clock//60,clock%60).strftime("%H:%M"); clock+=settings.stop_dwell_minutes
            dep=time(clock//60,clock%60).strftime("%H:%M")
            route_stops.append(RouteStop(route_stop_id=make_id("route_stop",len(route_stops)+1),route_id=route.route_id,stop_id=stop.stop_id,sequence_no=j,planned_arrival_time=arr,planned_departure_time=dep,travel_minutes_from_previous=mins,status="ACTIVE")); px,py=stop.x_km,stop.y_km
        if clock-420>route.max_duration_minutes: route.status="INFEASIBLE"
    session.add_all(routes); session.flush(); session.add_all(route_stops); session.flush()
    return routes,route_stops

def _populate(session: Session, params: dict, seed: int, start: date):
    rng=random.Random(seed); n,b,s,school_days=(params[k] for k in ("students","buses","stops","school_days")); zones=max(2,round(s/3)); zones=min(zones,max(2,s))
    calendar=service_dates(start,school_days)
    session.add_all([ServiceDate(service_date=d.isoformat(),day_number=i+1,is_school_day=True,calendar_name="SYNTHETIC_SERVICE_CALENDAR") for i,d in enumerate(calendar)])
    zone_rows=[AddressZone(address_zone_id=make_id("zone",i+1),zone_name=f"Synthetic Zone {i+1:03d}",center_x_km=((i%7)-3)*3.0,center_y_km=((i//7)-2)*3.0,status="ACTIVE") for i in range(zones)]
    session.add_all(zone_rows); session.flush()
    buses=[Bus(bus_id=make_id("bus",i+1),capacity=max(40,math.ceil(n/b)*2),accessible=i%4==0,status="ACTIVE") for i in range(b)]
    drivers=[Driver(driver_id=make_id("driver",i+1),driver_name=f"Synthetic Driver {i+1:04d}",active=True,duty_limit_minutes=300) for i in range(b)]
    session.add_all(buses+drivers); session.flush()
    stops=[]
    for i in range(s):
        z=zone_rows[i%zones]; approved=i%20!=19
        stops.append(Stop(stop_id=make_id("stop",i+1),stop_name=f"Synthetic Stop {i+1:04d}",address_zone_id=z.address_zone_id,x_km=z.center_x_km+rng.uniform(-1,1),y_km=z.center_y_km+rng.uniform(-1,1),pickup_window_start="06:30",pickup_window_end="09:30",accessible=i%5!=4,approved=approved,status="ACTIVE" if approved else "PENDING_APPROVAL"))
    session.add_all(stops); session.flush()
    students=[]; contacts=[]
    active_stops=[x for x in stops if x.approved]
    for i in range(n):
        z=zone_rows[i%zones]; near=active_stops[i%len(active_stops)]; approved=i%50!=49; sid=make_id("student",i+1)
        students.append(Student(student_id=sid,first_name=FIRST[i%len(FIRST)],last_name=LAST[(i//len(FIRST))%len(LAST)],grade=1+i%12,address_line=f"{100+i} Synthetic Lane",address_zone_id=z.address_zone_id,x_km=near.x_km+rng.uniform(-.5,.5),y_km=near.y_km+rng.uniform(-.5,.5),accessibility_required=i%30==0,pickup_window_start="06:30",pickup_window_end="09:30",address_approved=approved,status="ACTIVE" if i%100 else "INACTIVE",created_at="2026-01-01T00:00:00"))
        contacts.append(GuardianContact(guardian_contact_id=make_id("guardian",i+1),student_id=sid,relationship="PARENT",synthetic_email=f"guardian-{i+1:06d}@example.invalid",synthetic_phone=f"000-555-{i+1:04d}",preferred_channel="EMAIL",is_primary=True,is_verified=i%25!=0,consent_to_notify=i%20!=0,effective_from=start.isoformat(),effective_to=None,status="ACTIVE"))
    session.add_all(students); session.flush()
    session.add_all(contacts); session.flush()
    settings=Settings(seed=seed,start_date=start)
    routes,rstops=build_routes(session,settings)
    stop_by={x.stop_id:x for x in stops}; rstop_by_stop={x.stop_id:x for x in rstops}; routes_by={r.route_id:r for r in routes}; bus_by={x.bus_id:x for x in buses}
    route_stop_counts={r.route_id:sum(1 for rs in rstops if rs.route_id==r.route_id) for r in routes}
    loads={r.route_id:0 for r in routes}; assignments=[]
    for i,st in enumerate(students):
        if st.status!="ACTIVE" or not st.address_approved:
            continue
        candidates=[]
        for rs in rstops:
            stop=stop_by[rs.stop_id]; route=routes_by[rs.route_id]; d=distance_km(st.x_km,st.y_km,stop.x_km,stop.y_km); bus=bus_by[route.bus_id]
            if d>settings.service_radius_km or not stop.approved or route.status!="FEASIBLE": continue
            if not (st.pickup_window_start<=rs.planned_arrival_time<=st.pickup_window_end): continue
            if st.accessibility_required and (not bus.accessible or not stop.accessible): continue
            if loads[route.route_id]>=bus.capacity: continue
            util=(loads[route.route_id]+1)/bus.capacity
            score=d+0.5*(len(rstops)*3/60)+2*util+0.1*route_stop_counts[route.route_id]
            candidates.append((score,route.route_id,rs.route_stop_id,rs))
        if candidates:
            _,rid,rsid,rs=min(candidates,key=lambda v:(v[0],v[1],v[2])); loads[rid]+=1
            assignments.append(Assignment(assignment_id=make_id("assignment",1,st.student_id),student_id=st.student_id,route_stop_id=rsid,assigned_at=f"{start.isoformat()}T06:00:00",effective_from=start.isoformat(),effective_to=None,status="ASSIGNED",decision_code="ASSIGNED_BEST_FEASIBLE",decision_reason=f"Nearest feasible approved stop {rs.stop_id}; route {rid} passed capacity, approval, accessibility and radius checks."))
    session.add_all(assignments); session.flush()
    # Keep auditable unassigned decisions in a companion JSON report, not fake assignment rows.
    return {"zones":zones,"assignments":len(assignments),"unassigned":n-len(assignments),"routes":len(routes),"route_stops":len(rstops),"school_days":school_days,"service_date_start":calendar[0].isoformat(),"service_date_end":calendar[-1].isoformat(),"seed":seed,"parameters":params}

def generate(database: str, scale="starter", seed=20261022, custom=None, start=date(2026,1,5)):
    from .db import make_engine, initialize_database, make_session_factory
    params=dict(STARTER if scale=="starter" else FULL if scale=="full" else custom or {})
    if set(params)!={"students","buses","stops","school_days"} or min(params.values())<=0: raise ValueError("custom requires positive students, buses, stops and school_days")
    path=Path(database); path.parent.mkdir(parents=True,exist_ok=True)
    engine=make_engine(database); initialize_database(engine); SessionLocal=make_session_factory(engine)
    with SessionLocal() as session:
        if session.scalar(select(func.count()).select_from(Student)): raise ValueError("database is not empty; use a new output database")
        try:
            result=_populate(session,params,seed,start); session.commit()
        except Exception:
            session.rollback(); raise
    export(database, path.parent, seed=seed, parameters={**params,"start_date":start.isoformat()})
    return result

def export(database: str, output: str|Path, seed=None, parameters=None):
    import csv
    import sqlite3
    from sqlalchemy.schema import CreateTable
    from .db import make_engine
    out=Path(output); out.mkdir(parents=True,exist_ok=True); engine=make_engine(database); counts={}; files={}; checksums={}
    with engine.connect() as con:
        for table in Base.metadata.sorted_tables:
            name=table.name
            csv_path=out/f"{name}.csv"; json_path=out/f"{name}.json"
            fields=[c.name for c in table.columns]
            digest=hashlib.sha256(); row_count=0
            with csv_path.open("w",newline="",encoding="utf-8") as f:
                writer=csv.DictWriter(f,fieldnames=fields); writer.writeheader()
                with json_path.open("w",encoding="utf-8",newline="\n") as jf:
                    jf.write("["); first=True
                    result=con.execution_options(stream_results=True).execute(select(table).order_by(*table.primary_key.columns))
                    while True:
                        chunk=result.fetchmany(5000)
                        if not chunk: break
                        for record in chunk:
                            row=dict(record._mapping); writer.writerow(row)
                            if not first: jf.write(",")
                            jf.write(json.dumps(row,sort_keys=True,default=str,separators=(",",":"))); first=False
                            digest.update(json.dumps(row,sort_keys=True,default=str,separators=(",",":")).encode()); row_count+=1
                    jf.write("]")
            counts[name]=row_count; files[name]=[csv_path.name,json_path.name]; checksums[name]=digest.hexdigest()
    schema="\n\n".join(str(CreateTable(x).compile(dialect=engine.dialect))+";" for x in Base.metadata.sorted_tables)
    (out/"schema.sql").write_text(schema,encoding="utf-8")
    raw=sqlite3.connect(database)
    try:
        with (out/"seed.sql").open("w",encoding="utf-8",newline="\n") as f:
            for line in raw.iterdump(): f.write(line+"\n")
    finally: raw.close()
    from .validation import validate_database
    validation=validate_database(database)
    (out/"validation_summary.json").write_text(json.dumps(validation,indent=2),encoding="utf-8")
    artifact_checksums={}
    for path in sorted(out.iterdir()):
        if path.is_file() and path.name not in ("manifest.json",):
            digest=hashlib.sha256()
            with path.open("rb") as source:
                for chunk in iter(lambda:source.read(1024*1024),b""): digest.update(chunk)
            artifact_checksums[path.name]=digest.hexdigest()
    file_list={name:items for name,items in files.items()}
    file_list["sql"]=["schema.sql","seed.sql"]; file_list["validation"]=["validation_summary.json"]
    (out/"manifest.json").write_text(json.dumps({"seed":seed,"parameters":parameters or {},"simulation_parameters":{"absence_probability":0.04,"disruption_probability":0.025,"pickup_grace_minutes":10},"generator_version":"0.1.0","travel_model":{"road_distance_factor":1.25,"average_speed_kmh":25,"stop_dwell_minutes":2},"row_counts":counts,"files":file_list,"content_checksums":checksums,"artifact_checksums":artifact_checksums,"provenance":"synthetic deterministic generator","database":Path(database).name},indent=2),encoding="utf-8")
    return counts

def effective_capacity(session: Session, bus_id: str, on_date: date) -> int:
    bus=session.get(Bus,bus_id)
    if bus is None: raise ValueError("unknown bus")
    ev=session.scalars(select(BusCapacityEvent).where(BusCapacityEvent.bus_id==bus_id,BusCapacityEvent.effective_from<=on_date.isoformat()).order_by(BusCapacityEvent.effective_from.desc())).first()
    return ev.capacity_after if ev else bus.capacity

def assign_student(session: Session, student_id: str, route_stop_id: str, on_date: date, actor="ACADEMIC_ADMIN"):
    """Validate hard constraints before creating a versioned assignment."""
    if actor not in ("ACADEMIC_ADMIN","PLATFORM_ADMINISTRATOR","Platform administrator","Academic administrator"):
        raise PermissionError("This demo role cannot create assignments.")
    student=session.get(Student,student_id); rs=session.get(RouteStop,route_stop_id)
    def reject(code,reason): return {"accepted":False,"decision_code":code,"reason":reason}
    if student is None or rs is None: return reject("NO_FEASIBLE_ROUTE","Student or route stop does not exist.")
    if student.status!="ACTIVE": return reject("STUDENT_INACTIVE","Student is not active.")
    if not student.address_approved: return reject("ADDRESS_NOT_APPROVED","Student address is not approved.")
    stop=session.get(Stop,rs.stop_id); route=session.get(Route,rs.route_id); bus=session.get(Bus,route.bus_id)
    if not stop.approved or stop.status!="ACTIVE": return reject("NO_APPROVED_STOP_IN_RANGE","Stop is not approved and active.")
    d=distance_km(student.x_km,student.y_km,stop.x_km,stop.y_km)
    if d>Settings().service_radius_km: return reject("NO_APPROVED_STOP_IN_RANGE","No eligible stop within service radius.")
    if route.status not in ("FEASIBLE","ACTIVE"): return reject("NO_FEASIBLE_ROUTE","Route is not feasible.")
    if student.accessibility_required and (not bus.accessible or not stop.accessible): return reject("ACCESSIBILITY_MISMATCH","Accessible bus and pickup stop are required.")
    arrival=datetime.strptime(rs.planned_arrival_time,"%H:%M").time()
    if not (datetime.strptime(student.pickup_window_start,"%H:%M").time()<=arrival<=datetime.strptime(student.pickup_window_end,"%H:%M").time()): return reject("PICKUP_WINDOW_CONFLICT","Planned arrival is outside the student's pickup window.")
    overlap=session.scalar(select(Assignment).where(Assignment.student_id==student_id,Assignment.status=="ASSIGNED",Assignment.effective_from<=on_date.isoformat()).where((Assignment.effective_to.is_(None))|(Assignment.effective_to>=on_date.isoformat())))
    if overlap: return reject("DUPLICATE_ACTIVE_ASSIGNMENT","An active assignment already covers this date.")
    occupancy=session.scalar(select(func.count()).select_from(Assignment).join(RouteStop).where(RouteStop.route_id==route.route_id,Assignment.status=="ASSIGNED",Assignment.effective_from<=on_date.isoformat()).where((Assignment.effective_to.is_(None))|(Assignment.effective_to>=on_date.isoformat()))) or 0
    capacity=effective_capacity(session,bus.bus_id,on_date)
    if occupancy>=capacity: return reject("CAPACITY_LIMIT_REACHED",f"Capacity {capacity} is already occupied by {occupancy} assignments.")
    versions=session.scalars(select(Assignment).where(Assignment.student_id==student_id).order_by(Assignment.assignment_id)).all(); version=len(versions)+1
    assignment=Assignment(assignment_id=make_id("assignment",version,student_id),student_id=student_id,route_stop_id=route_stop_id,assigned_at=f"{on_date.isoformat()}T06:00:00",effective_from=on_date.isoformat(),effective_to=None,status="ASSIGNED",decision_code="ASSIGNED_BEST_FEASIBLE",decision_reason=f"Route {route.route_id}, stop {stop.stop_id}, {d:.2f} km; hard constraints passed.")
    session.add(assignment); session.flush()
    session.add(AuditEvent(audit_event_id=make_id("audit",(session.scalar(select(func.count()).select_from(AuditEvent)) or 0)+1),entity_type="Assignment",entity_id=assignment.assignment_id,action="ASSIGN",actor_role=actor,occurred_at=f"{on_date.isoformat()}T06:00:00",reason=assignment.decision_reason,after_json=json.dumps({"status":"ASSIGNED","route_stop_id":route_stop_id},sort_keys=True)))
    return {"accepted":True,"decision_code":assignment.decision_code,"reason":assignment.decision_reason,"assignment_id":assignment.assignment_id}

def reassign_student(session: Session,student_id: str,route_stop_id: str,on_date: date,actor="ACADEMIC_ADMIN"):
    """Close the covering assignment and create a new immutable version atomically."""
    if actor not in ("ACADEMIC_ADMIN","PLATFORM_ADMINISTRATOR","Platform administrator","Academic administrator"):
        raise PermissionError("This demo role cannot reassign students.")
    savepoint=session.begin_nested()
    current=session.scalar(select(Assignment).where(Assignment.student_id==student_id,Assignment.status=="ASSIGNED",Assignment.effective_from<=on_date.isoformat()).where((Assignment.effective_to.is_(None))|(Assignment.effective_to>=on_date.isoformat())).order_by(Assignment.effective_from.desc()))
    if current is None:
        savepoint.rollback(); return {"accepted":False,"decision_code":"NO_ACTIVE_ASSIGNMENT","reason":"No assignment covers the reassignment date."}
    before={"status":current.status,"effective_to":current.effective_to,"route_stop_id":current.route_stop_id}
    current.status="ENDED"; current.effective_to=(on_date-timedelta(days=1)).isoformat()
    session.flush()
    result=assign_student(session,student_id,route_stop_id,on_date,actor)
    if not result["accepted"]:
        savepoint.rollback(); return result
    seq=(session.scalar(select(func.count()).select_from(AuditEvent)) or 0)+1
    session.add(AuditEvent(audit_event_id=make_id("audit",seq),entity_type="Assignment",entity_id=result["assignment_id"],action="REASSIGN",actor_role=actor,occurred_at=f"{on_date.isoformat()}T06:00:00",reason=f"Reassigned from {current.assignment_id} to {result['assignment_id']}.",before_json=json.dumps(before,sort_keys=True),after_json=json.dumps({"status":"ASSIGNED","route_stop_id":route_stop_id},sort_keys=True)))
    savepoint.commit(); return result

def record_capacity_change(session: Session,bus_id: str,new_capacity:int,effective_from:date,reason="MAINTENANCE"):
    if new_capacity<=0: raise ValueError("capacity must be positive")
    bus=session.get(Bus,bus_id)
    if not bus: raise ValueError("unknown bus")
    route=session.scalar(select(Route).where(Route.bus_id==bus_id,Route.effective_from<=effective_from.isoformat()).order_by(Route.effective_from.desc()))
    if route:
        occ=session.scalar(select(func.count()).select_from(Assignment).join(RouteStop).where(RouteStop.route_id==route.route_id,Assignment.status=="ASSIGNED",Assignment.effective_from<=effective_from.isoformat()).where((Assignment.effective_to.is_(None))|(Assignment.effective_to>=effective_from.isoformat()))) or 0
        if new_capacity<occ: raise ValueError(f"capacity reduction unresolved: {occ} active assignments exceed new capacity {new_capacity}")
    seq=(session.scalar(select(func.count()).select_from(BusCapacityEvent)) or 0)+1
    ev=BusCapacityEvent(capacity_event_id=make_id("capacity_event",seq),bus_id=bus_id,effective_from=effective_from.isoformat(),capacity_before=effective_capacity(session,bus_id,effective_from-timedelta(days=1)),capacity_after=new_capacity,reason_code=reason,created_at=f"{effective_from.isoformat()}T00:00:00")
    session.add(ev); session.flush(); return ev

def simulate_day(session: Session, service_date: date, seed=20261022, create_disruptions=True):
    from sqlalchemy import insert
    day=service_date.isoformat(); assignments=session.scalars(select(Assignment).where(Assignment.status=="ASSIGNED",Assignment.effective_from<=day).where((Assignment.effective_to.is_(None))|(Assignment.effective_to>=day)).order_by(Assignment.assignment_id)).all()
    routes=session.scalars(select(Route).where(Route.status.in_(["FEASIBLE","ACTIVE"])).order_by(Route.route_id)).all(); route_by_id={r.route_id:r for r in routes}
    route_stops={x.route_stop_id:x for x in session.scalars(select(RouteStop)).all()}
    existing_attendance=set(session.scalars(select(AttendanceEvent.assignment_id).where(AttendanceEvent.service_date==day)).all())
    existing_disruptions={(x.route_id,x.disruption_type):x for x in session.scalars(select(RouteDisruptionEvent).where(RouteDisruptionEvent.service_date==day)).all()}
    disruption_map={}; disruption_seq=session.scalar(select(func.count()).select_from(RouteDisruptionEvent)) or 0
    if create_disruptions:
        for route in routes:
            val=int(hashlib.sha256(f"{seed}:{day}:{route.route_id}".encode()).hexdigest()[:8],16)/0xffffffff
            if val<Settings().disruption_probability:
                ev=existing_disruptions.get((route.route_id,"ROAD_DELAY"))
                if ev is None:
                    disruption_seq+=1; ev=RouteDisruptionEvent(disruption_event_id=make_id("disruption",disruption_seq),route_id=route.route_id,service_date=day,affected_stop_id=None,disruption_type="ROAD_DELAY",delay_minutes=12,status="OPEN",resolution_note=None,created_at=f"{day}T06:30:00"); session.add(ev)
                disruption_map[route.route_id]=ev.delay_minutes
    contacts={}
    for c in session.scalars(select(GuardianContact).where(GuardianContact.is_primary==True).order_by(GuardianContact.guardian_contact_id)).all(): contacts.setdefault(c.student_id,c)
    attendance_seq=session.scalar(select(func.count()).select_from(AttendanceEvent)) or 0; notification_seq=session.scalar(select(func.count()).select_from(Notification)) or 0
    attendance_rows=[]; notification_rows=[]
    for a in assignments:
        if a.assignment_id in existing_attendance: continue
        rs=route_stops[a.route_stop_id]; route=route_by_id[rs.route_id]; delay=disruption_map.get(route.route_id,0)
        h=int(hashlib.sha256(f"{seed}:{day}:{a.assignment_id}".encode()).hexdigest()[:16],16)/0xffffffffffffffff
        if h<Settings().absence_probability: status,reason="ABSENT","SEEDED_ABSENCE"
        elif delay>Settings().pickup_grace_minutes*2: status,reason="MISSED_PICKUP","DISRUPTION_DELAY"
        elif delay>Settings().pickup_grace_minutes: status,reason="LATE","DISRUPTION_DELAY"
        else: status,reason="PICKED_UP","ON_TIME"
        attendance_seq+=1; event_id=make_id("attendance",attendance_seq)
        attendance_rows.append({"attendance_event_id":event_id,"assignment_id":a.assignment_id,"service_date":day,"status":status,"observed_at":f"{day}T08:00:00","source":"SIMULATOR","reason_code":reason,"notes":None})
        if status in ("ABSENT","MISSED_PICKUP"):
            contact=contacts.get(a.student_id)
            if contact:
                key=hashlib.sha256(f"{event_id}:{contact.guardian_contact_id}:{status}".encode()).hexdigest()
                eligible=contact.status=="ACTIVE" and contact.is_verified and contact.consent_to_notify and ((contact.preferred_channel=="EMAIL" and contact.synthetic_email.endswith("@example.invalid")) or contact.preferred_channel=="IN_APP")
                notification_seq+=1
                notification_rows.append({"notification_id":make_id("notification",notification_seq),"attendance_event_id":event_id,"guardian_contact_id":contact.guardian_contact_id,"channel":contact.preferred_channel,"template_code":"ABSENCE_NOTICE" if status=="ABSENT" else "MISSED_PICKUP_NOTICE","status":"SIMULATED_SENT" if eligible else "SUPPRESSED","created_at":f"{day}T08:01:00","sent_at":f"{day}T08:01:00" if eligible else None,"idempotency_key":key,"reason_code":None if eligible else "CONTACT_NOT_ELIGIBLE"})
    if session.new: session.flush()
    for i in range(0,len(attendance_rows),5000): session.execute(insert(AttendanceEvent),attendance_rows[i:i+5000])
    for i in range(0,len(notification_rows),5000): session.execute(insert(Notification),notification_rows[i:i+5000])
    session.commit(); created=len(attendance_rows); notices=len(notification_rows)
    return {"service_date":day,"assignments":len(assignments),"attendance_created":created,"notifications_created":notices}

def simulate_history(database: str, days: int, seed=20261022, start=date(2026,1,5)):
    from .db import make_engine,make_session_factory
    Session=make_session_factory(make_engine(database)); results=[]
    with Session() as session:
        for day in service_dates(start,days): results.append(simulate_day(session,day,seed))
    return results
