
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()
db_url = os.getenv('DATABASE_URL')
engine = create_engine(db_url)

with engine.connect() as conn:
    print("--- POSTGRES SETTINGS ---")
    for param in ['max_connections', 'shared_buffers', 'synchronous_commit', 'work_mem']:
        res = conn.execute(text(f"SHOW {param}")).fetchone()
        print(f"{param}: {res[0] if res else 'N/A'}")
    
    conn_count = conn.execute(text("SELECT count(*) FROM pg_stat_activity")).fetchone()[0]
    print(f"Current Active Connections: {conn_count}")
    
    config_path = conn.execute(text("SHOW config_file")).fetchone()[0]
    print(f"Config File Path: {config_path}")
