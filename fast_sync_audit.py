
import os
import sys
from sqlalchemy import create_engine, text

# Add src to path
sys.path.append(os.path.abspath('src'))
from config import config

def fast_audit():
    l_engine = create_engine(config.LOCAL_POSTGRES_CONN)
    r_engine = create_engine(config.REMOTE_POSTGRES_CONN)
    ufs = ['SE', 'RR', 'TO', 'AC', 'AP']
    
    print("\n--- Auditoria Ultrarrápida de Sincronização (Apenas Inteligência) ---")
    
    with l_engine.connect() as l_conn, r_engine.connect() as r_conn:
        # Set short timeout for remote
        r_conn.execute(text("SET statement_timeout = 3000"))
        
        for uf in ufs:
            # Local
            l_meta = l_conn.execute(text(f"SELECT COUNT(*) FROM section_metadata WHERE uf = '{uf}'")).scalar()
            l_pats = l_conn.execute(text(f"SELECT COUNT(*) FROM log_patterns WHERE uf = '{uf}'")).scalar()
            
            # Remote
            try:
                r_meta = r_conn.execute(text(f"SELECT COUNT(*) FROM section_metadata WHERE uf = '{uf}'")).scalar()
            except: r_meta = -1
            
            try:
                r_pats = r_conn.execute(text(f"SELECT COUNT(*) FROM log_patterns WHERE uf = '{uf}'")).scalar()
            except: r_pats = -1
            
            print(f"UF: {uf} | Meta: L={l_meta} R={r_meta} | Pats: L={l_pats} R={r_pats}")

if __name__ == "__main__":
    fast_audit()
