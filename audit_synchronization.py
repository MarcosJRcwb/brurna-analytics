
import os
import sys
from sqlalchemy import create_engine, text

# Add src to path
sys.path.append(os.path.abspath('src'))
from config import config

def audit_sync():
    try:
        l_engine = create_engine(config.LOCAL_POSTGRES_CONN)
        r_engine = create_engine(config.REMOTE_POSTGRES_CONN)
        ufs = ['SE', 'RR', 'TO', 'AC', 'AP']
        
        print("\n=== RELATÓRIO DE AUDITORIA DE SINCRONIZAÇÃO ===")
        print(f"{'UF':<4} | {'LOGS (L)':<10} | {'LOGS (R)':<10} | {'DIFF':<10} | {'% SYNC'}")
        print("-" * 65)
        
        with l_engine.connect() as l_conn, r_engine.connect() as r_conn:
            # Set shorter timeout for remote to avoid hanging
            r_conn.execute(text("SET statement_timeout = 10000"))
            
            for uf in ufs:
                # Local counts (fast)
                # count from log_eventos
                l_logs = l_conn.execute(text(f"SELECT COUNT(*) FROM log_eventos WHERE source_file LIKE '{uf.lower()}/%'")).scalar()
                
                # Remote counts
                try:
                    r_logs = r_conn.execute(text(f"SELECT COUNT(*) FROM log_eventos WHERE source_file LIKE '{uf.lower()}/%'")).scalar()
                except Exception as e:
                    r_logs = -1 # Error or timeout
                
                diff = l_logs - r_logs if r_logs >= 0 else l_logs
                percent = (r_logs / l_logs * 100) if (l_logs > 0 and r_logs >= 0) else 0
                
                print(f"{uf:<4} | {l_logs:<10} | {r_logs:<10} | {diff:<10} | {percent:.1f}%")
        
        print("\n--- METADADOS E PADRÕES ---")
        print(f"{'UF':<4} | {'META (L)':<8} | {'META (R)':<8} | {'PATS (L)':<8} | {'PATS (R)':<8}")
        print("-" * 65)
        
        with l_engine.connect() as l_conn, r_engine.connect() as r_conn:
            for uf in ufs:
                l_meta = l_conn.execute(text(f"SELECT COUNT(*) FROM section_metadata WHERE uf = '{uf}'")).scalar()
                l_pats = l_conn.execute(text(f"SELECT COUNT(*) FROM log_patterns WHERE uf = '{uf}'")).scalar()
                
                try:
                    r_meta = r_conn.execute(text(f"SELECT COUNT(*) FROM section_metadata WHERE uf = '{uf}'")).scalar()
                    r_pats = r_conn.execute(text(f"SELECT COUNT(*) FROM log_patterns WHERE uf = '{uf}'")).scalar()
                except:
                    r_meta, r_pats = -1, -1
                
                print(f"{uf:<4} | {l_meta:<8} | {r_meta:<8} | {l_pats:<8} | {r_pats:<8}")

    except Exception as e:
        print(f"ERRO NA AUDITORIA: {e}")

if __name__ == "__main__":
    audit_sync()
