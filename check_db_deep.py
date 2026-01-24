
from sqlalchemy import create_engine, text
from config import config

engine = create_engine(config.POSTGRES_CONN)

def check_mg_data():
    with engine.connect() as conn:
        print("🔍 Verificação profunda de dados de MG (Docker Contabo)...")
        tables = ['temporal_metrics', 'processed_sections', 'section_metadata', 'log_patterns']
        for table in tables:
            try:
                count = conn.execute(text(f"SELECT COUNT(*) FROM {table} WHERE uf = 'MG'")).scalar()
                print(f"   - {table} (MG): {count} registros")
            except Exception as e:
                print(f"   - {table}: Erro ao consultar (pode não ter coluna 'uf'): {e}")
        
        # Também verifica se há registros SEM UF ou com UF minúsculo
        try:
            count_null = conn.execute(text("SELECT COUNT(*) FROM section_metadata WHERE uf IS NULL OR uf = ''")).scalar()
            print(f"   - section_metadata (Sem UF): {count_null}")
        except: pass

if __name__ == "__main__":
    check_mg_data()
