
from sqlalchemy import create_engine, text
from config import config

engine = create_engine(config.POSTGRES_CONN)

def check_status():
    with engine.connect() as conn:
        print("🔍 Verificando status do Acre (AC)...")
        count = conn.execute(text("SELECT COUNT(1) FROM section_metadata WHERE uf = 'AC'")).scalar()
        print(f"✅ Seções processadas (AC): {count}")
        
        # Detalhes de integridade
        if count > 0:
            events = conn.execute(text("SELECT SUM(total_eventos) FROM section_metadata WHERE uf = 'AC'")).scalar()
            print(f"📊 Total de eventos (AC): {events:,}")

if __name__ == "__main__":
    check_status()
