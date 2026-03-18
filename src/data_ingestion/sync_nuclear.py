
import os
import time
import json
import subprocess
from sqlalchemy import create_engine, text
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Configs
LOCAL_URL = os.getenv("LOCAL_DATABASE_URL")
REMOTE_URL = os.getenv("REMOTE_DATABASE_URL")
SYNC_STATUS_FILE = "sync_status.json"

import psycopg2
import sys
import re

def get_processed_ufs(engine):
    query = text("""
        SELECT DISTINCT split_part(source_file, '/', 1) as uf 
        FROM log_eventos
        WHERE source_file LIKE '%/%'
    """)
    with engine.connect() as conn:
        return [row[0] for row in conn.execute(query)]

def sync_uf(uf, cleanup_local=True):
    print(f"Syncing UF: {uf.upper()} | Forensic & Streaming Mode...")
    
    # Define explicit columns for each forensic table to avoid schema order mismatches
    TABLE_COLUMNS = {
        'log_patterns': ['uf', 'turno', 'aplicativo', 'severidade', 'mensagem_padrao', 'mensagem_exemplo', 'ocorrencias', 'primeira_ocorrencia', 'ultima_ocorrencia'],
        'temporal_metrics': ['uf', 'turno', 'data', 'hora', 'aplicativo', 'severidade', 'quantidade'],
        'section_metadata': ['uf', 'turno', 'municipio_codigo', 'zona', 'secao', 'pk', 'total_eventos', 'periodo_inicio', 'periodo_fim', 'duracao_segundos', 'aplicativos_usados', 'severidades', 'hash_arquivo', 'modelo_urna', 'votos_computados', 'eleitores_habilitados', 'eleitores_sem_biometria', 'biometria_analysis'],
        'mesarios': ['uf', 'turno', 'municipio_codigo', 'zona', 'secao', 'pk', 'numero_mesario', 'eleitor_secao', 'arquivo_biometria', 'eventos', 'primeiro_evento', 'ultimo_evento'],
        'log_exceptions': ['uf', 'turno', 'municipio_codigo', 'zona', 'secao', 'sec_pk', 'timestamp', 'severidade', 'aplicativo', 'mensagem_bruta']
    }
    
    try:
        l_conn = psycopg2.connect(LOCAL_URL)
        r_conn = psycopg2.connect(REMOTE_URL)
        l_cur = l_conn.cursor()
        r_cur = r_conn.cursor()

        # Ensure cache dir exists
        cache_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../cache/sync'))
        os.makedirs(cache_dir, exist_ok=True)

        # 1. Sync Forensic Tables
        for table, cols in TABLE_COLUMNS.items():
            print(f"  Syncing {table}...")
            temp_forensic = os.path.join(cache_dir, f"sync_{table}_{uf}.csv")
            cols_str = ", ".join(cols)
            
            # Export with explicit columns
            copy_out = f"COPY (SELECT {cols_str} FROM {table} WHERE uf = '{uf.upper()}') TO STDOUT WITH CSV HEADER"
            with open(temp_forensic, 'wb') as f:
                l_cur.copy_expert(copy_out, f)
            
            # Import with explicit columns
            r_cur.execute(f"DELETE FROM {table} WHERE uf = '{uf.upper()}'")
            with open(temp_forensic, 'rb') as f:
                r_cur.copy_expert(f"COPY {table} ({cols_str}) FROM STDIN WITH CSV HEADER", f)
            
            r_conn.commit()
            if os.path.exists(temp_forensic): os.remove(temp_forensic)

        # 2. Cleanup RAW logs from Database to save space (Since we already extracted intelligence)
        # Note: We deliberately skip syncing `log_eventos` to AWS to save bandwidth and compute.

        # 3. Cleanup
        if cleanup_local:
            print(f"Cleaning local raw for {uf.upper()}...")
            l_cur.execute(f"DELETE FROM log_eventos WHERE source_file LIKE '{uf.lower()}/%'")
            l_conn.commit()
            
            print("Vacuuming local...")
            l_conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
            l_cur.execute("VACUUM ANALYZE log_eventos")
        
        l_cur.close(); l_conn.close()
        r_cur.close(); r_conn.close()
        print(f"UF {uf.upper()} full sync completed.")

    except Exception as e:
        print(f"Critical Sync Error for {uf}: {e}")
        if 'l_conn' in locals(): l_conn.close()
        if 'r_conn' in locals(): r_conn.close()
        raise e  # Re-raise to alert orchestrator

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Sync Forensic Data to Remote DB")
    parser.add_argument("--uf", type=str, help="Specific UF to sync (e.g., rr)", required=False)
    args = parser.parse_args()

    if args.uf:
        print(f"SYNC MANAGER: Processing single UF {args.uf.upper()}")
        sync_uf(args.uf.lower(), cleanup_local=True)
        return

    print("SYNC MANAGER ACTIVE (Daemon Mode - DEPRECATED for Parallel Orchestrator)")
    local_engine = create_engine(LOCAL_URL)
    while True:
        try:
            ufs = get_processed_ufs(local_engine)
            for uf in ufs:
                sync_uf(uf)
            
            status = {
                "last_sync": datetime.now().isoformat(),
                "active_sync": "idle"
            }
            with open(SYNC_STATUS_FILE, "w") as f:
                json.dump(status, f)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Sync sleep: 30s...")
        except Exception as e:
            print(f"Loop error: {e}")
        time.sleep(30) # Check every 30s for better visibility

if __name__ == "__main__":
    main()
