
import os
import sys
from sqlalchemy import create_engine, text

# Adiciona src ao path
sys.path.append(os.path.abspath('src'))

from config import config

def check_rr_progress():
    try:
        engine = create_engine(config.LOCAL_POSTGRES_CONN)
        with engine.connect() as conn:
            # Conta arquivos distintos já no banco para RR
            query = text("SELECT COUNT(DISTINCT source_file) FROM log_eventos WHERE source_file LIKE 'rr/%'")
            db_count = conn.execute(query).scalar()
            
            # Conta arquivos .logjez no disco para RR
            base_dir = config.RAW_LOGS_DIR
            state_dir = os.path.join(base_dir, 'rr')
            disk_count = 0
            if os.path.exists(state_dir):
                for root, _, files in os.walk(state_dir):
                    for f in files:
                        if f.endswith('.logjez'):
                            disk_count += 1
            
            if disk_count > 0:
                percent = (db_count / disk_count) * 100
                print(f"PROGRESSO_RR: {db_count}/{disk_count} ({percent:.2f}%)")
            else:
                print("ERRO: Arquivos de RR não encontrados no diretório RAW.")
                
    except Exception as e:
        print(f"ERRO: {e}")

if __name__ == "__main__":
    check_rr_progress()
