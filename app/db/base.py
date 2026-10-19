import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

load_dotenv()

engine = create_engine(
    os.environ["DATABASE_URL"],
    connect_args={"connect_timeout": 3})
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass

def check_db() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except OperationalError:
        return False