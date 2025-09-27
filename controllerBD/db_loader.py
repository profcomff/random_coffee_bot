from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from data.config import DB_DSN

engine = create_engine(DB_DSN, pool_pre_ping=True, isolation_level="AUTOCOMMIT")
Session = sessionmaker(bind=engine)

Base = declarative_base()
