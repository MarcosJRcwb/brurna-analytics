
from sqlalchemy import create_engine, text
from config import config

engine = create_engine(config.POSTGRES_CONN)

def check_db():
    with engine.connect() as conn:
        print("🔍 Relatório de Integridade do Banco:")
        count_total = conn.execute(text("SELECT COUNT(1) FROM section_metadata")).scalar()
        count_models = conn.execute(text("SELECT COUNT(1) FROM section_metadata WHERE modelo_urna IS NOT NULL")).scalar()
        print(f"   Total de Urnas: {count_total}")
        print(f"   Urnas com Modelo Mapeado: {count_models} ({100*count_models/count_total:.1f}%)")
        
        if count_models > 0:
            print("\n🏛️ Distribuição de Modelos:")
            models = conn.execute(text("SELECT modelo_urna, COUNT(*) FROM section_metadata WHERE modelo_urna IS NOT NULL GROUP BY modelo_urna")).fetchall()
            for m in models:
                print(f"   {m[0]}: {m[1]}")

if __name__ == "__main__":
    check_db()
