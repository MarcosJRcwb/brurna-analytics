
import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

def setup():
    # Try with confirmed password
    urls = [
        "postgresql://postgres:1@localhost:5432/postgres",
        "postgresql://postgres:1@127.0.0.1:5432/postgres",
    ]
    target_db = "brurna_db"
    
    success = False
    for admin_url in urls:
        try:
            print(f"Trying connection to {admin_url}...")
            engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
            with engine.connect() as conn:
                # Check if db exists
                result = conn.execute(text(f"SELECT 1 FROM pg_database WHERE datname = '{target_db}'"))
                if not result.fetchone():
                    print(f"Creating database {target_db}...")
                    conn.execute(text(f"CREATE DATABASE {target_db}"))
                else:
                    print(f"Database {target_db} already exists.")
                success = True
                break
        except Exception as e:
            print(f"Failed to connect with {admin_url}: {repr(e)}")
            
    if not success:
        print("CRITICAL: Could not connect to local PostgreSQL with any default credentials.")
        sys.exit(1)

    # Now connect to brurna_db and create table
    db_url = f"postgresql://postgres:1@localhost:5432/{target_db}"
    try:
        engine = create_engine(db_url)
        with engine.connect() as conn:
            print("Creating table log_eventos if not exists...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS public.log_eventos (
                    id serial4 NOT NULL,
                    source_file varchar(255) NULL,
                    "timestamp" timestamp NULL,
                    "level" varchar(50) NULL,
                    code varchar(50) NULL,
                    message text NULL,
                    original_line text NULL,
                    CONSTRAINT log_eventos_pkey PRIMARY KEY (id)
                );
            """))
            conn.commit()
            print("Table log_eventos ready.")
    except Exception as e:
        # Avoid print encoding issues
        print(f"Error setting up table: {type(e).__name__}")
        try:
            print(f"Details: {str(e).encode('ascii', 'ignore').decode()}")
        except:
            print("Could not decode error details.")
        sys.exit(1)

if __name__ == "__main__":
    setup()
