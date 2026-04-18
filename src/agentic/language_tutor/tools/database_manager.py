# tools/database_manager.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

psql_user = os.environ.get("PSQL_USER")
psql_pswq = os.environ.get("PSQL_PASSWORD")

# The connection string uses the psycopg driver
DATABASE_URL = f"postgresql+psycopg://{psql_user}:{psql_pswq}@localhost:5432/{psql_user}"

# pool_size ensures we don't crash Postgres with too many agent connections
engine = create_engine(DATABASE_URL, pool_size=5, max_overflow=10)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
