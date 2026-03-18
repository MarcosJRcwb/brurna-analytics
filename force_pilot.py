from config import config
from sqlalchemy import create_engine, text

def wipe_states(states):
    remote = create_engine(config.REMOTE_POSTGRES_CONN)
    local = create_engine(config.LOCAL_POSTGRES_CONN)
    
    tables = [
        "log_exceptions",
        "log_patterns",
        "temporal_metrics",
        "section_metadata",
        "mesarios"
    ]
    
    for state in states:
        print(f"Deleting {state} from Remote aggregated tables...")
        with remote.begin() as conn:
            for table in tables:
                conn.execute(text(f"DELETE FROM {table} WHERE uf = '{state}'"))
            
        print(f"Deleting {state} from Local aggregated tables...")
        with local.begin() as conn:
            for table in tables:
                conn.execute(text(f"DELETE FROM {table} WHERE uf = '{state}'"))
                
        print(f"Successfully cleared {state}.")

if __name__ == "__main__":
    wipe_states(['SE', 'RR', 'TO'])
