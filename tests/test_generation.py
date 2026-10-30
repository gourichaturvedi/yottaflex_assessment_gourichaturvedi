from datetime import date
from sqlalchemy import func,select
from transport_ops.db import make_engine,make_session_factory
from transport_ops.models import Student,Bus,Stop,Route,Assignment
from transport_ops.services import generate

def test_starter_generation(tmp_path):
    db=tmp_path/"ops.sqlite"; result=generate(str(db),"starter",123)
    assert result["seed"]==123
    Session=make_session_factory(make_engine(db))
    with Session() as s:
        assert s.scalar(select(func.count()).select_from(Student))==250
        assert s.scalar(select(func.count()).select_from(Bus))==10
        assert s.scalar(select(func.count()).select_from(Stop))==30
        assert s.scalar(select(func.count()).select_from(Route))==10
        assert s.scalar(select(func.count()).select_from(Assignment))>0
