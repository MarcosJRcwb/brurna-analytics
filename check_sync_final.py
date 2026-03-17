
import os
import sys
from sqlalchemy import create_engine, text

# Add src to path
sys.path.append(os.path.abspath('src'))
from config import config

def get_final_status():
    l_engine = create_engine(config.LOCAL_POSTGRES_CONN)
    r_engine = create_engine(config.REMOTE_POSTGRES_CONN)
    ufs = ['SE', 'RR', 'TO', 'AC', 'AP']
    
    print("\n--- Auditoria Final de Sincronização ---")
    
    with l_engine.connect() as l_conn, r_engine.connect() as r_conn:
        # Set timeout
        r_conn.execute(text("SET statement_timeout = 5000"))
        
        for uf in ufs:
            print(f"\nEstado: {uf}")
            
            # Local stats
            l_meta = l_conn.execute(text(f"SELECT COUNT(*) FROM section_metadata WHERE uf = '{uf}'")).scalar()
            l_pats = l_conn.execute(text(f"SELECT COUNT(*) FROM log_patterns WHERE uf = '{uf}'")).scalar()
            
            # Local Logs (Fast estimate if possible, or direct count if table is indexable)
            l_logs = l_conn.execute(text(f"SELECT COUNT(*) FROM log_eventos WHERE source_file LIKE '{uf.lower()}/%'")).scalar()

            # Remote stats
            try:
                r_meta = r_conn.execute(text(f"SELECT COUNT(*) FROM section_metadata WHERE uf = '{uf}'")).scalar()
                r_pats = r_conn.execute(text(f"SELECT COUNT(*) FROM log_patterns WHERE uf = '{uf}'")).scalar()
            except:
                r_meta, r_pats = -2, -2 # Indicates Timeout
            
            # Remote Logs (Fast check)
            try:
                # Use a very short timeout for the count
                r_conn.execute(text("SET statement_timeout = 3000"))
                r_logs = r_conn.execute(text(f"SELECT COUNT(*) FROM log_eventos WHERE source_file LIKE '{uf.lower()}/%'")).scalar()
            except:
                r_logs = -2 # Indicates Timeout/Pending

            p_meta = (r_meta / l_meta * 100) if l_meta > 0 and r_meta >= 0 else 0
            p_logs = (r_logs / l_logs * 100) if l_logs > 0 and r_logs >= 0 else 0
            
            print(f"  Metadados: Local={l_meta:<5} | Remoto={r_meta:<5} ({p_meta:.1f}%)")
            print(f"  Padrões:   Local={l_pats:<5} | Remoto={r_pats:<5}")
            
            log_str = f"{r_logs}" if r_logs >= 0 else ("TIMEOUT/PENDENTE" if r_logs == -2 else "ERRO")
            print(f"  Logs Brutos: Local={l_logs:<10} | Remoto={log_str:<10} ({p_logs:.1f}%)")
            
            if p_logs >= 99 and p_meta >= 99:
                print(f"  STATUS FINAL: ✅ SINCRONIZADO")
            elif r_meta == -2 or r_logs == -2:
                print(f"  STATUS FINAL: ⚠️ CONEXÃO LENTA / PENDENTE")
            else:
                print(f"  STATUS FINAL: 🔄 EM SINCRONIA")

if __name__ == "__main__":
    get_final_status()
