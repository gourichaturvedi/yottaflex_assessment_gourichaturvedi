import json
import time
from sqlalchemy import text,select,func
from .db import make_engine,make_session_factory
from .ids import valid_id
from .models import *
from .services import Settings,validate_route_stops

def validate_database(database: str):
    started=time.perf_counter()
    engine=make_engine(database); Session=make_session_factory(engine); checks=[]
    def add(name,checked,failures,severity="ERROR",explanation=""):
        checks.append({"check_name":name,"records_checked":int(checked),"pass_count":int(checked)-len(failures),"fail_count":len(failures),"severity":severity,"affected_ids":failures[:100],"explanation":explanation})
    with engine.connect() as con:
        fk=[str(tuple(x)) for x in con.execute(text("PRAGMA foreign_key_check"))]
        add("foreign_keys",sum(1 for _ in Base.metadata.tables),fk,explanation="SQLite foreign_key_check; zero rows means no orphans.")
    with Session() as s:
        for model,field,kind in [(Student,"student_id","student"),(Stop,"stop_id","stop"),(Bus,"bus_id","bus"),(Route,"route_id","route"),(Assignment,"assignment_id","assignment"),(GuardianContact,"guardian_contact_id","guardian"),(RouteStop,"route_stop_id","route_stop"),(AttendanceEvent,"attendance_event_id","attendance"),(Notification,"notification_id","notification"),(BusCapacityEvent,"capacity_event_id","capacity_event"),(RouteDisruptionEvent,"disruption_event_id","disruption"),(AuditEvent,"audit_event_id","audit")]:
            total=s.scalar(select(func.count()).select_from(model)) or 0; fails=[]
            for value in s.scalars(select(getattr(model,field)).execution_options(yield_per=5000)):
                if not valid_id(kind,value):
                    fails.append(value)
                    if len(fails)>=100: break
            add(f"id_pattern_{model.__tablename__}",total,fails,explanation=f"{field} must match documented deterministic pattern.")
        routes=s.scalars(select(Route)).all(); route_fail=[]
        for route in routes:
            items=s.scalars(select(RouteStop).where(RouteStop.route_id==route.route_id).order_by(RouteStop.sequence_no)).all()
            errors=validate_route_stops(items,Settings())
            if errors and route.status in ("FEASIBLE","ACTIVE"): route_fail.append(route.route_id)
        add("route_feasibility",len(routes),route_fail,explanation="Active/feasible routes must have contiguous sequence and physically possible times.")
        assignments=s.scalars(select(Assignment).where(Assignment.status=="ASSIGNED")).all(); access_fail=[]; approval_fail=[]; overlap_fail=[]; cap_fail=[]
        students={x.student_id:x for x in s.scalars(select(Student)).all()}; route_stops={x.route_stop_id:x for x in s.scalars(select(RouteStop)).all()}; stops={x.stop_id:x for x in s.scalars(select(Stop)).all()}; routes_by_id={x.route_id:x for x in routes}; buses={x.bus_id:x for x in s.scalars(select(Bus)).all()}
        occupancy_by_route={rid:n for rid,n in s.execute(select(RouteStop.route_id,func.count(Assignment.assignment_id)).join(Assignment,Assignment.route_stop_id==RouteStop.route_stop_id).where(Assignment.status=="ASSIGNED").group_by(RouteStop.route_id)).all()}
        capacity_events={}
        for event in s.scalars(select(BusCapacityEvent).order_by(BusCapacityEvent.effective_from)).all(): capacity_events.setdefault(event.bus_id,[]).append(event)
        for a in assignments:
            st=students[a.student_id]; rs=route_stops[a.route_stop_id]; stop=stops[rs.stop_id]; route=routes_by_id[rs.route_id]; bus=buses[route.bus_id]
            if not st.address_approved or not stop.approved: approval_fail.append(a.assignment_id)
            if st.accessibility_required and (not bus.accessible or not stop.accessible): access_fail.append(a.assignment_id)
            if st.pickup_window_start>rs.planned_arrival_time or st.pickup_window_end<rs.planned_arrival_time: overlap_fail.append(a.assignment_id)
            occupancy=occupancy_by_route.get(route.route_id,0)
            capacity=bus.capacity
            effective=[e for e in capacity_events.get(bus.bus_id,[]) if e.effective_from<=a.effective_from]
            if effective: capacity=effective[-1].capacity_after
            if occupancy>capacity: cap_fail.append(route.route_id)
        add("assignment_approval",len(assignments),approval_fail,explanation="Assignments require approved student address and stop.")
        add("assignment_accessibility",len(assignments),access_fail,explanation="Accessibility-requiring students require accessible bus and stop.")
        add("assignment_pickup_window",len(assignments),overlap_fail,explanation="Planned stop arrival must be within student pickup window.")
        add("route_capacity",len(assignments),sorted(set(cap_fail)),explanation="Occupancy must not exceed effective bus capacity.")
        from sqlalchemy.orm import aliased
        a1=aliased(Assignment); a2=aliased(Assignment)
        overlap_ids=s.scalars(select(a1.assignment_id).join(a2,a1.student_id==a2.student_id).where(a1.assignment_id<a2.assignment_id,a1.status=="ASSIGNED",a2.status=="ASSIGNED",a1.effective_from<=func.coalesce(a2.effective_to,"9999-12-31"),a2.effective_from<=func.coalesce(a1.effective_to,"9999-12-31")).limit(100)).all()
        add("assignment_effective_overlap",len(assignments),overlap_ids,explanation="A student cannot have overlapping assigned effective periods.")
        weekend_dates=s.scalars(select(ServiceDate.service_date).where(func.strftime("%w",ServiceDate.service_date).in_(["0","6"]))).all()
        add("service_calendar_weekdays",s.scalar(select(func.count()).select_from(ServiceDate)) or 0,weekend_dates,explanation="Service calendar contains weekdays only.")
        bad_link=s.scalars(select(Notification.notification_id).join(AttendanceEvent,AttendanceEvent.attendance_event_id==Notification.attendance_event_id).join(Assignment,Assignment.assignment_id==AttendanceEvent.assignment_id).join(GuardianContact,GuardianContact.guardian_contact_id==Notification.guardian_contact_id).where(GuardianContact.student_id!=Assignment.student_id).limit(100)).all()
        add("notification_student_contact_link",s.scalar(select(func.count()).select_from(Notification)) or 0,bad_link,explanation="Notification contact must belong to the attendance assignment's student.")
        att_count=s.scalar(select(func.count()).select_from(AttendanceEvent)) or 0
        bad_att=s.scalars(select(AttendanceEvent.attendance_event_id).join(Assignment,Assignment.assignment_id==AttendanceEvent.assignment_id).where((Assignment.effective_from>AttendanceEvent.service_date)|((Assignment.effective_to.is_not(None))&(Assignment.effective_to<AttendanceEvent.service_date))).limit(100)).all()
        add("attendance_effective_assignment",att_count,bad_att,explanation="Attendance must fall within assignment effective dates.")
        sent_count=s.scalar(select(func.count()).select_from(Notification).where(Notification.status=="SIMULATED_SENT")) or 0
        bad_notice=s.scalars(select(Notification.notification_id).join(GuardianContact,GuardianContact.guardian_contact_id==Notification.guardian_contact_id).where(Notification.status=="SIMULATED_SENT",((GuardianContact.is_verified==False)|(GuardianContact.consent_to_notify==False)|(GuardianContact.status!="ACTIVE"))).limit(100)).all()
        add("notification_eligibility",sent_count,bad_notice,explanation="Only active, verified, consenting synthetic contacts may be simulated sent.")
    report={"database":database,"checks":checks,"pass_count":sum(x["fail_count"]==0 for x in checks),"check_count":len(checks),"fail_count":sum(x["fail_count"]>0 for x in checks),"valid":all(x["fail_count"]==0 for x in checks),"duration_seconds":round(time.perf_counter()-started,3)}
    return report
