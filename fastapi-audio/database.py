from sqlmodel import create_engine, SQLModel, Session
from sqlalchemy.exc import OperationalError

DATABASE_URL = "postgresql+psycopg2://postgres:admin@localhost:5432/Test2"
engine = create_engine(DATABASE_URL, echo=True)

def create_db_and_tables():
    try:
        SQLModel.metadata.create_all(engine)
    except OperationalError as e:
        print(f"Database error: {e}. Ensure PostgreSQL is running and the 'Test2' database exists.")
        raise

def get_session():
    with Session(engine) as session:
        yield session