from sqlalchemy import create_engine, text
from config import config
import sys

try:
    engine = create_engine(config.POSTGRES_CONN)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")).fetchall()
        print("Tables found:")
        for row in result:
            print(f"- {row[0]}")
            
            # Inspect columns for key tables
            if row[0] in ['temporal_metrics', 'log_eventos', 'secoes', 'metadata']:
                print(f"  Columns for {row[0]}:")
                cols = conn.execute(text(f"SELECT column_name FROM information_schema.columns WHERE table_name='{row[0]}'")).fetchall()
                print(f"  {[c[0] for c in cols]}")

except Exception as e:
    print(f"Error: {e}")
