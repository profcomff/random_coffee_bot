from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base

from data.config import DB_DSN

engine = create_engine(DB_DSN)
engine.connect()
db_session = Session(bind=engine)

Base = declarative_base()
