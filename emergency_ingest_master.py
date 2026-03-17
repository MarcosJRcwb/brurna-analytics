
import os
import sys
import time
from sqlalchemy import create_engine, text
from datetime import datetime

# Adiciona src ao path para importar módulos do projeto
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

try:
    from config import config
except ImportError:
    import config

import data_ingestion.ingest_nuclear as ingest_nuclear
import data_ingestion.sync_nuclear as sync_nuclear
from database.db_writer import create_tables
from analytics.process_forensic_patterns import process_uf_batch

def run_emergency():
    print(f"\n{'='*60}")
    print(f"EMERGENCY PARALLEL ORCHESTRATOR - PHASE 14")
    print(f"Target UFs: SE, RR, TO, AC, AP")
    print(f"Workers: 30 (Ryzen 9 Mode)")
    print(f"{'='*60}\n")
    
    # 1. Ensure schema is ready (Local and Remote)
    print("Verificando Schema Local...")
    create_tables()
    
    print("Verificando Schema Remoto...")
    remote_engine = create_engine(config.REMOTE_POSTGRES_CONN)
    try:
        from database.db_writer import SQL_CREATE_TABLES
        with remote_engine.connect() as conn:
            conn.execute(text(SQL_CREATE_TABLES))
            conn.commit()
        print("✅ Schema Remoto pronto.")
    except Exception as e:
        print(f"⚠️ Aviso Schema Remoto: {e}")

    # 2. Define target states
    states = ['se', 'rr', 'to', 'ac', 'ap']
    
    for uf in states:
        print(f"\n>>> INICIANDO CICLO FULL-DATA UF: {uf.upper()}")
        
        # Phase 1: Local Ingestion (Nuclear Mode)
        print(f"  [1/3] Local Raw Ingest...")
        ingest_nuclear.main(target_uf=uf)
        
        # Phase 2: Forensic Aggregation (Local Pattern Discovery)
        # This MUST happen while local log_eventos still has raw data
        print(f"  [2/3] Forensic Discovery (Pattern Aggregation)...")
        process_uf_batch(uf, db_url=config.LOCAL_POSTGRES_CONN)
        
        # Phase 3: Total Sync (Forensics + Raw Logs + Remote Ops)
        # sync_uf now handles forensics, raw copy, and local cleanup
        print(f"  [3/3] Streaming Sync to Remote + Cleanup...")
        sync_nuclear.sync_uf(uf, cleanup_local=True)
        
        print(f"--- UF {uf.upper()} CICLO COMPLETO ---\n")
        
    print(f"\n{'='*60}")
    print(f" EMERGENCY PROCESS COMPLETED.")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    run_emergency()
