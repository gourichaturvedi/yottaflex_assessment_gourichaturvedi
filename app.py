from pathlib import Path
from datetime import date
import pandas as pd
import streamlit as st
from sqlalchemy import select,func
from transport_ops.db import make_engine,make_session_factory
from transport_ops.models import *
from transport_ops.services import generate,simulate_day
from transport_ops.validation import validate_database
from transport_ops.scenarios import evaluate_scenarios
from transport_ops.metrics import metrics_snapshot

st.set_page_config(page_title="YottaFlex Student Transport Ops",layout="wide")
st.title("Student Transport Routing & Daily Operations")
st.caption("Synthetic local challenge demo · Demo role switcher is not secure authentication")
role=st.sidebar.selectbox("Demo role",["Platform administrator","Academic administrator","Instructor","Support staff","Learner"])
database=st.sidebar.text_input("SQLite database","data/generated/transport_ops.sqlite")
pages=["Overview Dashboard","Data Setup and Generator","Route Planning","Students and Assignments","Daily Operations","Exceptions / Exception Lab","Data Explorer and Validation","Documentation and About"]
page=st.sidebar.radio("Page",pages)

def count(s,model): return s.scalar(select(func.count()).select_from(model)) or 0
if not Path(database).exists():
    st.info("No generated dataset found. Open Data Setup to create a starter or full dataset.")
    scale=st.selectbox("Scale",["starter","full"]); seed=st.number_input("Seed",value=20261022,step=1); start=st.date_input("Start date",date(2026,1,5))
    target=st.text_input("New database output",f"data/generated/run_{seed}_{scale}/transport_ops.sqlite")
    if st.button("Generate dataset"):
        if Path(target).exists(): st.error("Database already exists. Choose a new path to preserve it.")
        else:
            with st.spinner("Generating synthetic records..."): result=generate(target,scale,int(seed),start=start)
            st.success("Generation complete"); st.json(result)
else:
    engine=make_engine(database); Session=make_session_factory(engine)
    with Session() as session:
        if page=="Overview Dashboard":
            dates=session.scalars(select(ServiceDate.service_date).order_by(ServiceDate.day_number)).all(); start=dates[0] if dates else None; end=dates[-1] if dates else None
            m=metrics_snapshot(database,date.fromisoformat(start) if start else None,date.fromisoformat(end) if end else None)
            st.caption(f"Dataset: {Path(database).parent.name} · Service dates: {start or 'n/a'} to {end or 'n/a'}")
            cols=st.columns(5)
            for col,label,value in zip(cols,["Students","Assigned","Active routes","Feasible routes","Approved stops"],[m["students_total"],m["assigned_students"],m["active_routes"],m["feasible_routes"],m["approved_stops"]]): col.metric(label,value)
            cols=st.columns(4); cols[0].metric("Assignment coverage",f"{m['assignment_coverage_pct']:.1%}"); cols[1].metric("Avg route utilization",f"{m['average_capacity_utilization']:.1%}"); cols[2].metric("Capacity violations",m["capacity_violations"]); cols[3].metric("Accessibility violations",m["inaccessible_assignments"])
            st.subheader("Persisted attendance by status"); st.dataframe(pd.DataFrame(m["attendance_by_status"].items(),columns=["status","count"]),width="stretch")
            st.metric("Missed pickup rate",f"{m['missed_pickup_rate']:.2%}"); st.subheader("Notification outcomes"); st.dataframe(pd.DataFrame(m["notifications_by_status"].items(),columns=["status","count"]),width="stretch")
        elif page=="Data Setup and Generator":
            st.warning("Generation requires a new output database; existing files are never overwritten.")
            scale=st.selectbox("Scale",["starter","full"]); seed=st.number_input("Seed",value=20261022,step=1); start=st.date_input("Start date",date(2026,1,5)); target=st.text_input("New database output",f"data/generated/run_{seed}_{scale}/transport_ops.sqlite")
            if st.button("Generate dataset"):
                if Path(target).exists(): st.error("Database already exists. Choose a new path to preserve it.")
                else:
                    with st.spinner("Generating synthetic records..."): result=generate(target,scale,int(seed),start=start)
                    st.success("Generation complete"); st.json(result)
        elif page=="Route Planning":
            rows=session.scalars(select(Route).order_by(Route.route_id)).all(); st.dataframe(pd.DataFrame([{"route_id":r.route_id,"status":r.status,"bus_id":r.bus_id,"driver_id":r.driver_id,"start":r.planned_start_time,"max_minutes":r.max_duration_minutes} for r in rows]),width="stretch")
            selected=st.selectbox("Route detail",[r.route_id for r in rows]) if rows else None
            if selected:
                detail=session.execute(select(RouteStop,Stop).join(Stop).where(RouteStop.route_id==selected).order_by(RouteStop.sequence_no)).all()
                st.dataframe(pd.DataFrame([{"sequence":rs.sequence_no,"stop_id":stop.stop_id,"name":stop.stop_name,"arrival":rs.planned_arrival_time,"departure":rs.planned_departure_time,"travel_minutes":rs.travel_minutes_from_previous} for rs,stop in detail]),width="stretch")
        elif page=="Students and Assignments":
            query=st.text_input("Search student ID"); stmt=select(Student).order_by(Student.student_id).limit(200)
            if query: stmt=select(Student).where(Student.student_id.contains(query)).order_by(Student.student_id).limit(200)
            rows=session.scalars(stmt).all(); data=[]
            for student in rows:
                assignment=session.scalar(select(Assignment).where(Assignment.student_id==student.student_id).order_by(Assignment.effective_from.desc()))
                data.append({"student_id":student.student_id,"grade":student.grade,"status":student.status,"zone":student.address_zone_id,"accessibility_required":student.accessibility_required,"address":student.address_line if role=="Platform administrator" and student.address_approved else ("[REDACTED]" if not student.address_approved else None),"assignment_id":assignment.assignment_id if assignment else None,"decision":assignment.decision_code if assignment else "UNASSIGNED"})
            st.dataframe(pd.DataFrame(data),width="stretch")
            if role in ("Platform administrator","Academic administrator"):
                from transport_ops.services import reassign_student
                active=session.scalars(select(Assignment).where(Assignment.status=="ASSIGNED").order_by(Assignment.assignment_id)).all(); eligible_stops=session.scalars(select(RouteStop).order_by(RouteStop.route_stop_id)).all()
                if active and eligible_stops:
                    who=st.selectbox("Student to reassign",[a.student_id for a in active]); destination=st.selectbox("New route stop",[r.route_stop_id for r in eligible_stops]); effective=st.date_input("Reassignment effective date",date(2026,2,1))
                    if st.button("Validate and reassign"):
                        result=reassign_student(session,who,destination,effective,role); session.commit()
                        st.success(result["reason"]) if result["accepted"] else st.error(result["reason"])
        elif page=="Daily Operations":
            dates=session.scalars(select(ServiceDate.service_date).order_by(ServiceDate.day_number)).all(); day=st.selectbox("Service date",dates) if dates else None
            if day:
                if st.button("Simulate day"):
                    st.json(simulate_day(session,date.fromisoformat(day)))
                events=session.scalars(select(AttendanceEvent).where(AttendanceEvent.service_date==day).order_by(AttendanceEvent.attendance_event_id).limit(500)).all()
                st.dataframe(pd.DataFrame([{"event_id":e.attendance_event_id,"assignment_id":e.assignment_id,"status":e.status,"reason":e.reason_code} for e in events]),width="stretch")
        elif page=="Exceptions / Exception Lab":
            if st.button("Run five edge-case tests"): st.session_state["scenario_results"]=evaluate_scenarios()
            if "scenario_results" in st.session_state: st.dataframe(pd.DataFrame(st.session_state["scenario_results"]),width="stretch")
            if st.button("Run baseline validation"): st.session_state["validation"]=validate_database(database)
            if "validation" in st.session_state: st.json(st.session_state["validation"])
        elif page=="Data Explorer and Validation":
            names={m.__tablename__:m for m in ALL_MODELS}; table=st.selectbox("Table",list(names)); model=names[table]; page_no=st.number_input("Page",min_value=1,value=1,step=1); limit=st.selectbox("Page size",[25,50,100])
            rows=session.scalars(select(model).offset((page_no-1)*limit).limit(limit)).all(); st.dataframe(pd.DataFrame([{c.name:getattr(row,c.name) for c in model.__table__.columns} for row in rows]),width="stretch")
            if st.button("Validate data"): st.json(validate_database(database))
        else:
            st.markdown("Coordinates are synthetic kilometres on a plane. Travel uses road distance = Euclidean distance × 1.25, at 25 km/h, with 2-minute stop dwell.")
            for name in ["DATA_DICTIONARY.md","SCHEMA.md","DECISIONS.md","METRICS.md","VALIDATION.md","LIMITATIONS.md","AI_USAGE.md"]:
                path=Path("docs")/name
                if path.exists():
                    with st.expander(name): st.markdown(path.read_text(encoding="utf-8"))

