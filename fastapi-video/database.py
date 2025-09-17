from sqlmodel import create_engine, SQLModel, Session

DATABASE_URL = "postgresql+psycopg2://postgres:admin@localhost:5432/Test1"
engine = create_engine(DATABASE_URL, echo=True)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session