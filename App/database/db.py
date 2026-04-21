from sqlalchemy import create_engine, URL
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# ✅ Safe way — handles special characters in password
connection_url = URL.create(
    drivername="postgresql",
    username="postgres",
    password="Parth@123#",  # paste exact password here — special chars are fine
    host="localhost",
    port=5432,
    database="water_distribution"
)

engine = create_engine(connection_url)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables."""
    from App.database import models
    Base.metadata.create_all(bind=engine)