from datetime import date
from sqlalchemy import select
from transport_ops.db import make_engine,make_session_factory
from transport_ops.models import Assignment,Student,RouteStop,Bus,Route
from transport_ops.services import generate,assign_student,reassign_student,validate_route_stops,Settings

def test_assignment_rejects_capacity_and_duplicate(tmp_path):
    db=tmp_path/"ops.sqlite"; generate(str(db),"starter",5)
    Session=make_session_factory(make_engine(db))
    with Session() as s:
        route=s.scalars(select(Route).order_by(Route.route_id)).first(); bus=s.get(Bus,route.bus_id); bus.capacity=1; s.commit()
        assigned=s.scalars(select(Assignment).join(RouteStop).where(RouteStop.route_id==route.route_id)).first()
        assert assigned is not None
        first=assign_student(s,assigned.student_id,assigned.route_stop_id,date(2026,1,5))
        assert first["decision_code"]=="DUPLICATE_ACTIVE_ASSIGNMENT"
        original=s.get(Student,assigned.student_id)
        student=Student(student_id="STU-999999",first_name="Test",last_name="Candidate",grade=5,address_line="Synthetic Lane",address_zone_id=original.address_zone_id,x_km=original.x_km,y_km=original.y_km,accessibility_required=False,pickup_window_start="06:30",pickup_window_end="09:30",address_approved=True,status="ACTIVE",created_at="2026-01-01T00:00:00")
        s.add(student); s.flush()
        result=assign_student(s,student.student_id,assigned.route_stop_id,date(2026,1,5))
        assert result["decision_code"]=="CAPACITY_LIMIT_REACHED"

def test_route_sequence_and_timing_validation():
    from types import SimpleNamespace
    rs=[SimpleNamespace(sequence_no=1,planned_arrival_time="07:00",planned_departure_time="07:02",travel_minutes_from_previous=0,route_stop_id="a"),SimpleNamespace(sequence_no=2,planned_arrival_time="07:03",planned_departure_time="07:05",travel_minutes_from_previous=10,route_stop_id="b")]
    assert "IMPOSSIBLE_TRAVEL_TIME:b" in validate_route_stops(rs,Settings())

def test_accessibility_and_address_approval_are_hard_constraints(tmp_path):
    db=tmp_path/"ops.sqlite"; generate(str(db),"starter",9); Session=make_session_factory(make_engine(db))
    with Session() as s:
        rs=s.scalars(select(RouteStop).join(Route).join(Bus).where(Bus.accessible==False)).first(); stop=s.get(__import__('transport_ops.models',fromlist=['Stop']).Stop,rs.stop_id)
        student=Student(student_id="STU-999998",first_name="Synthetic",last_name="Learner",grade=4,address_line="Synthetic Lane",address_zone_id=stop.address_zone_id,x_km=stop.x_km,y_km=stop.y_km,accessibility_required=True,pickup_window_start="06:00",pickup_window_end="10:00",address_approved=True,status="ACTIVE",created_at="2026-01-01T00:00:00")
        s.add(student); s.flush()
        assert assign_student(s,student.student_id,rs.route_stop_id,date(2026,1,5))["decision_code"]=="ACCESSIBILITY_MISMATCH"
        student.address_approved=False; student.accessibility_required=False; s.flush()
        assert assign_student(s,student.student_id,rs.route_stop_id,date(2026,1,5))["decision_code"]=="ADDRESS_NOT_APPROVED"

def test_reassignment_versions_and_closes_prior_assignment(tmp_path):
    db=tmp_path/"ops.sqlite"; generate(str(db),"starter",11); Session=make_session_factory(make_engine(db))
    with Session() as s:
        first=s.scalars(select(Assignment).order_by(Assignment.assignment_id)).first(); old_route_stop=s.get(RouteStop,first.route_stop_id)
        candidate=s.scalars(select(RouteStop).where(RouteStop.route_id!=old_route_stop.route_id).order_by(RouteStop.route_stop_id)).first()
        result=reassign_student(s,first.student_id,candidate.route_stop_id,date(2026,2,1))
        assert result["accepted"] and result["assignment_id"].endswith("-V02")
        assert first.status=="ENDED" and first.effective_to=="2026-01-31"

def test_service_layer_rejects_read_only_role(tmp_path):
    db=tmp_path/"ops.sqlite"; generate(str(db),"starter",12); Session=make_session_factory(make_engine(db))
    with Session() as s:
        st=s.scalars(select(Student).where(Student.status=="ACTIVE",Student.address_approved==True)).first(); rs=s.scalars(select(RouteStop)).first()
        try: assign_student(s,st.student_id,rs.route_stop_id,date(2026,1,5),actor="INSTRUCTOR")
        except PermissionError: pass
        else: assert False,"read-only role must not create assignments"

def test_pickup_window_is_a_hard_constraint(tmp_path):
    db=tmp_path/"ops.sqlite"; generate(str(db),"starter",15); Session=make_session_factory(make_engine(db))
    with Session() as s:
        rs=s.scalars(select(RouteStop)).first(); stop=s.get(__import__('transport_ops.models',fromlist=['Stop']).Stop,rs.stop_id)
        student=Student(student_id="STU-999997",first_name="Synthetic",last_name="Learner",grade=4,address_line="Synthetic Lane",address_zone_id=stop.address_zone_id,x_km=stop.x_km,y_km=stop.y_km,accessibility_required=False,pickup_window_start="23:00",pickup_window_end="23:30",address_approved=True,status="ACTIVE",created_at="2026-01-01T00:00:00")
        s.add(student); s.flush()
        assert assign_student(s,student.student_id,rs.route_stop_id,date(2026,1,5))["decision_code"]=="PICKUP_WINDOW_CONFLICT"
