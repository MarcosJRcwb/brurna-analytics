
import os
import sys
from sqlalchemy import create_engine, text

# Add src to path
sys.path.append(os.path.abspath('src'))
from config import config

def check_remote():
    try:
        r_engine = create_engine(config.REMOTE_POSTGRES_CONN)
        ufs = ['SE', 'RR', 'TO', 'AC', 'AP']
        
        print("\n=== VERIFICAÇÃO DE DADOS NO SERVIDOR REMOTO ===")
        
        with r_engine.connect() as conn:
            conn.execute(text("SET statement_timeout = 5000"))
            
            for uf in ufs:
                # Check metadata
                try:
                    meta_exists = conn.execute(text(f"SELECT EXISTS(SELECT 1 FROM section_metadata WHERE uf = '{uf}')")).scalar()
                except: meta_exists = "TIMEOUT"
                
                # Check patterns
                try:
                    pats_count = conn.execute(text(f"SELECT COUNT(*) FROM log_patterns WHERE uf = '{uf}'")).scalar()
                except: pats_count = "TIMEOUT"
                
                # Check logs (very fast check)
                try:
                    logs_exists = conn.execute(text(f"SELECT EXISTS(SELECT 1 FROM log_eventos WHERE source_file LIKE '{uf.lower()}/%')")).scalar()
                except: logs_exists = "TIMEOUT"
                
                print(f"UF: {uf:<4} | Metadados: {meta_exists:<8} | Padrões: {pats_count:<8} | Logs Brutos: {logs_exists}")

    except Exception as e:
        print(f"Erro na verificação remota: {e}")

if __name__ == "__main__":
    check_remote()
