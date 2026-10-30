from datetime import date
from sqlalchemy import func,select
from transport_ops.db import make_engine,make_session_factory
from transport_ops.models import AttendanceEvent,Notification,RouteDisruptionEvent
from transport_ops.services import generate,simulate_day

def test_day_simulation_is_idempotent(tmp_path):
    db=tmp_path/"ops.sqlite"; generate(str(db),"starter",20261022)
    Session=make_session_factory(make_engine(db))
    with Session() as s:
        first=simulate_day(s,date(2026,1,5),20261022)
        second=simulate_day(s,date(2026,1,5),20261022)
        assert first["attendance_created"]>0
        assert second["attendance_created"]==0
        count=s.scalar(select(func.count()).select_from(AttendanceEvent))
        assert count==first["attendance_created"]
        keys=s.scalars(select(Notification.idempotency_key)).all()
        assert len(keys)==len(set(keys))
        # Disruptions are unique per route/date on rerun too.
        assert s.scalar(select(func.count()).select_from(RouteDisruptionEvent))==len(set((x.route_id,x.service_date) for x in s.scalars(select(RouteDisruptionEvent))))
