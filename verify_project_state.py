
from sqlalchemy import create_engine, text
from config import config
from pathlib import Path

def verify_state():
    engine = create_engine(config.POSTGRES_CONN)
    ufs = ['RR', 'AP', 'AC', 'TO', 'SE']
    
    print("--- Database Counts (section_metadata) ---")
    with engine.connect() as conn:
        for uf in ufs:
            try:
                result = conn.execute(text(f"SELECT count(*) FROM section_metadata WHERE uf = '{uf}'")).scalar()
                print(f"{uf}: {result} seções")
            except Exception as e:
                print(f"{uf}: Erro ao acessar banco ({e})")

    print("\n--- Raw Logs File Counts ---")
    for uf in ufs:
        log_dir = config.RAW_LOGS_DIR / uf.lower()
        if log_dir.exists():
            count = len(list(log_dir.glob('*.logjez')))
            print(f"{uf}: {count} arquivos .logjez")
        else:
            print(f"{uf}: Diretório não encontrado")

if __name__ == "__main__":
    verify_state()
