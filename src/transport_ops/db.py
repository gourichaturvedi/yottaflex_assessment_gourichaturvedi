from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from .models import Base

def make_engine(database: str | Path = "data/generated/transport_ops.sqlite"):
    path=Path(database)
    if str(database) != ":memory:": path.parent.mkdir(parents=True,exist_ok=True)
    engine=create_engine(f"sqlite:///{database}" if str(database) != ":memory:" else "sqlite://", future=True)
    @event.listens_for(engine,"connect")
    def enable_fk(dbapi_connection, _):
        cursor=dbapi_connection.cursor(); cursor.execute("PRAGMA foreign_keys=ON"); cursor.close()
    return engine

def initialize_database(engine):
    Base.metadata.create_all(engine)

def make_session_factory(engine): return sessionmaker(bind=engine, expire_on_commit=False)
