from sqlalchemy import text
from transport_ops.db import initialize_database, make_engine
from transport_ops.ids import make_id, valid_id
from transport_ops.models import ALL_MODELS

def test_required_ids():
    assert make_id("student",1)=="STU-000001"
    assert make_id("route",1)=="ROUTE-2026-000001"
    assert make_id("assignment",1,"STU-000001")=="ASN-STU-000001-2026"
    assert valid_id("notification",make_id("notification",1))

def test_schema_and_fk_enforcement():
    engine=make_engine(":memory:"); initialize_database(engine)
    with engine.connect() as c:
        tables={r[0] for r in c.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))}
        assert len(tables)==len(ALL_MODELS)
        assert c.exec_driver_sql("PRAGMA foreign_keys").scalar()==1
        try:
            c.execute(text("INSERT INTO guardian_contacts (guardian_contact_id,student_id,relationship,preferred_channel,is_primary,is_verified,consent_to_notify,effective_from,status) VALUES ('GUA-000001','MISSING','PARENT','EMAIL',1,1,1,'2026-01-01','ACTIVE')")); c.commit()
            assert False, "foreign key should reject missing parent"
        except Exception: c.rollback()

