#db.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import ProgrammingError
from dotenv import load_dotenv
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from models import Base 

load_dotenv()


DB_HOST = os.getenv('PG_HOST')
DB_NAME = os.getenv('PG_DB')
DB_USER = os.getenv('PG_USER')
DB_PASS = os.getenv('PG_PASSWORD')

DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Provides a database session for application use."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def setup_database():
    print("Starting automatic database setup...")
    
    try:
        conn = psycopg2.connect(host=DB_HOST, user=DB_USER, password=DB_PASS, dbname='postgres')
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        cursor.execute(f"SELECT 1 FROM pg_database WHERE datname = '{DB_NAME}'")
        if not cursor.fetchone():
            cursor.execute(f"CREATE DATABASE {DB_NAME}")
            print(f" Database '{DB_NAME}' created.")
        else:
            print(f" Database '{DB_NAME}' already exists.")
            
        cursor.close()
        conn.close()
    except Exception as e:
        print(f" Could not create or verify the database. Please check your PostgreSQL server and credentials. Error: {e}")
        return


    try:
        conn = psycopg2.connect(host=DB_HOST, user=DB_USER, password=DB_PASS, dbname=DB_NAME)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        print(" pg_vector extension enabled successfully.")
        
        cursor.close()
        conn.close()
    except ProgrammingError as e:
         print(f" Could not enable pg_vector. Please ensure it is installed for your PostgreSQL version. Error: {e}")
         print("   On Ubuntu, you can install it with: sudo apt install postgresql-XX-pgvector")
         return
    except Exception as e:
        print(f" An error occurred while enabling the extension: {e}")
        return


    try:
        print("Creating tables from models.py...")
        # The engine is already configured with the correct DATABASE_URL
        Base.metadata.create_all(bind=engine)
        print(" All tables created successfully (if they didn't already exist).")
    except Exception as e:
        print(f" An error occurred while creating tables: {e}")
        return
        
    print("\n Database setup is complete and correct.")

if __name__ == "__main__":
    # This allows you to run `python db.py` to set up everything.
    setup_database()
