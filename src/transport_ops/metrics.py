from datetime import date
from sqlalchemy import select,func
from .db import make_engine,make_session_factory
from .models import *

def metrics_snapshot(database: str,start:date|None=None,end:date|None=None):
    engine=make_engine(database); Session=make_session_factory(engine)
    with Session() as s:
        total=s.scalar(select(func.count()).select_from(Student)) or 0
        active=s.scalar(select(func.count()).select_from(Student).where(Student.status=="ACTIVE")) or 0
        assigned_ids=s.scalars(select(Assignment.student_id).where(Assignment.status=="ASSIGNED").distinct()).all()
        assigned=len(assigned_ids); routes=s.scalars(select(Route).order_by(Route.route_id)).all()
        buses={b.bus_id:b for b in s.scalars(select(Bus)).all()}; rstop={r.route_stop_id:r for r in s.scalars(select(RouteStop)).all()}
        counts={rid:n for rid,n in s.execute(select(RouteStop.route_id,func.count(Assignment.assignment_id)).join(Assignment,Assignment.route_stop_id==RouteStop.route_stop_id).where(Assignment.status=="ASSIGNED").group_by(RouteStop.route_id)).all()}
        utilizations=[]; capacity_violations=0; inaccessible=0; durations=[]; travel=[]
        cap_events={}
        for ev in s.scalars(select(BusCapacityEvent).order_by(BusCapacityEvent.effective_from)).all(): cap_events.setdefault(ev.bus_id,[]).append(ev)
        as_of=end.isoformat() if end else None
        for route in routes:
            bus=buses[route.bus_id]; occupancy=counts.get(route.route_id,0)
            changes=[e for e in cap_events.get(bus.bus_id,[]) if as_of is None or e.effective_from<=as_of]
            capacity=changes[-1].capacity_after if changes else bus.capacity
            utilization=occupancy/capacity if capacity else 0
            utilizations.append(utilization); capacity_violations+=int(occupancy>capacity)
            stops=s.scalars(select(RouteStop).where(RouteStop.route_id==route.route_id).order_by(RouteStop.sequence_no)).all()
            if stops:
                a=int(route.planned_start_time[:2])*60+int(route.planned_start_time[3:]); d=int(stops[-1].planned_departure_time[:2])*60+int(stops[-1].planned_departure_time[3:]); durations.append(d-a)
                travel.extend(x.travel_minutes_from_previous for x in stops)
        for a in s.scalars(select(Assignment).where(Assignment.status=="ASSIGNED")).all():
            student=s.get(Student,a.student_id); rs=rstop[a.route_stop_id]
            if student.accessibility_required and (not buses[next(r.bus_id for r in routes if r.route_id==rs.route_id)].accessible or not s.get(Stop,rs.stop_id).accessible): inaccessible+=1
        attq=select(AttendanceEvent.status,func.count()).group_by(AttendanceEvent.status)
        if start: attq=attq.where(AttendanceEvent.service_date>=start.isoformat())
        if end: attq=attq.where(AttendanceEvent.service_date<=end.isoformat())
        attendance=dict(s.execute(attq).all()); att_total=sum(attendance.values()); missed=attendance.get("MISSED_PICKUP",0); absent=attendance.get("ABSENT",0)
        ntq=select(Notification.status,func.count()).group_by(Notification.status)
        if start: ntq=ntq.where(Notification.created_at>=start.isoformat())
        if end: ntq=ntq.where(Notification.created_at<=end.isoformat()+"T23:59:59")
        notifications=dict(s.execute(ntq).all()); not_total=sum(notifications.values())
        return {"students_total":total,"students_active":active,"assigned_students":assigned,"unassigned_students":max(0,active-assigned),"assignment_coverage_pct":assigned/active if active else 0,"active_routes":sum(r.status=="ACTIVE" for r in routes),"feasible_routes":sum(r.status in ("ACTIVE","FEASIBLE") for r in routes),"buses":len(buses),"approved_stops":s.scalar(select(func.count()).select_from(Stop).where(Stop.approved==True,Stop.status=="ACTIVE")) or 0,"average_capacity_utilization":sum(utilizations)/len(utilizations) if utilizations else 0,"maximum_capacity_utilization":max(utilizations,default=0),"capacity_violations":capacity_violations,"inaccessible_assignments":inaccessible,"feasible_route_pct":sum(r.status in ("FEASIBLE","ACTIVE") for r in routes)/len(routes) if routes else 0,"average_planned_duration_minutes":sum(durations)/len(durations) if durations else 0,"planned_travel_minutes":sum(travel),"attendance_by_status":attendance,"attendance_events":att_total,"missed_pickups":missed,"missed_pickup_rate":missed/att_total if att_total else 0,"absences":absent,"absence_rate":absent/att_total if att_total else 0,"notifications_by_status":notifications,"notifications_created":not_total,"notification_sent":notifications.get("SIMULATED_SENT",0),"notification_suppressed":notifications.get("SUPPRESSED",0),"notification_failed":notifications.get("FAILED",0),"notification_delivery_rate":notifications.get("SIMULATED_SENT",0)/not_total if not_total else 0,"open_disruptions":s.scalar(select(func.count()).select_from(RouteDisruptionEvent).where(RouteDisruptionEvent.status=="OPEN")) or 0}
