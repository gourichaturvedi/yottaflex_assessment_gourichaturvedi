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
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@400;500;600;700;800&display=swap');
:root { --ink:#172b35; --muted:#6a7b7d; --paper:#f4f3ed; --panel:#fffefa; --line:#dce2dc; --lime:#d6ed65; --orange:#f08a52; }
.stApp { background:var(--paper); color:var(--ink); font-family:'Manrope',sans-serif; }
[data-testid="stHeader"] { background:transparent; }
[data-testid="stSidebar"] { background:#172b35; border-right:0; }
[data-testid="stSidebar"] * { color:#edf1e9 !important; }
[data-testid="stSidebar"] [data-testid="stRadio"] label { padding:8px 10px; border-radius:7px; }
[data-testid="stSidebar"] [data-testid="stRadio"] label:hover { background:#29414a; }
[data-testid="stSidebar"] input { color:#172b35 !important; }
.block-container { max-width:1500px; padding-top:2rem; padding-bottom:3rem; }
h1,h2,h3 { color:var(--ink); letter-spacing:-.045em; font-family:'Manrope',sans-serif; }
h1 { font-size:2.5rem !important; font-weight:800 !important; }
h2 { font-weight:800 !important; }
[data-testid="stMetric"] { background:var(--panel); border:1px solid var(--line); border-radius:10px; padding:16px 18px; box-shadow:0 2px 8px #172b3508; }
[data-testid="stMetricLabel"] { color:var(--muted); font-size:.75rem; text-transform:uppercase; letter-spacing:.09em; font-weight:700; }
[data-testid="stMetricValue"] { color:var(--ink); font-weight:800; }
[data-testid="stDataFrame"] { border:1px solid var(--line); border-radius:9px; overflow:hidden; background:var(--panel); }
div.stButton > button { background:var(--ink); color:white; border:0; border-radius:6px; font-weight:700; padding:.55rem 1rem; }
div.stButton > button:hover { background:#29414a; color:var(--lime); border:0; }
[data-testid="stTextInput"] input, [data-testid="stNumberInput"] input, [data-testid="stSelectbox"] div[data-baseweb="select"] { border-radius:6px; }
.yf-mast { display:flex; align-items:center; justify-content:space-between; border-bottom:1px solid var(--line); padding:0 0 14px; margin-bottom:30px; }
.yf-brand { display:flex; align-items:center; gap:11px; font-weight:800; letter-spacing:.03em; font-size:13px; text-transform:uppercase; }
.yf-mark { display:grid; place-items:center; width:32px; height:32px; border-radius:7px; color:var(--ink); background:var(--lime); font-weight:900; }
.yf-micro { color:var(--muted); font:11px 'DM Mono',monospace; letter-spacing:.04em; text-transform:uppercase; }
.yf-kicker { color:#658044; font:11px 'DM Mono',monospace; letter-spacing:.12em; text-transform:uppercase; margin-bottom:7px; }
.yf-note { border-left:3px solid var(--orange); padding:10px 14px; background:#fffefa; color:#536467; font-size:.9rem; }
@media (max-width:800px) { h1 {font-size:1.9rem !important;} .yf-micro{display:none;} }
</style>
<div class="yf-mast"><div class="yf-brand"><span class="yf-mark">Y</span><span>YottaFlex <span style="font-weight:500;color:#6a7b7d">/ Transit operations</span></span></div><div class="yf-micro">FIELD SYSTEMS&nbsp;&nbsp;·&nbsp;&nbsp;LOCAL DEMO</div></div>
""",unsafe_allow_html=True)
role=st.sidebar.selectbox("Demo role",["Platform administrator","Academic administrator","Instructor","Support staff","Learner"])
database=st.sidebar.text_input("SQLite database","data/generated/transport_ops.sqlite")
pages=["Overview Dashboard","Data Setup and Generator","Route Planning","Students and Assignments","Daily Operations","Exceptions / Exception Lab","Data Explorer and Validation","Documentation and About"]
page=st.sidebar.radio("Page",pages)
page_titles={"Overview Dashboard":"Daily transport, under control.","Data Setup and Generator":"Build a service dataset.","Route Planning":"Routes at a glance.","Students and Assignments":"People and their journeys.","Daily Operations":"Today’s service, live.","Exceptions / Exception Lab":"Find the edge cases.","Data Explorer and Validation":"Inspect the underlying data.","Documentation and About":"How this demo works."}
st.markdown('<div class="yf-kicker">Student mobility · Operations console</div>',unsafe_allow_html=True)
st.title(page_titles[page])
st.caption("Local operations demo · Synthetic student and route data · Role selector is for demonstration only")

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

