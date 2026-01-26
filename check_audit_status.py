
from sqlalchemy import create_engine, text
from config import config

engine = create_engine(config.POSTGRES_CONN)

def check_audit():
    with engine.connect() as conn:
        print("🔍 Relatório de Auditoria (Logs):")
        res = conn.execute(text("SELECT uf, COUNT(1), SUM(votos_computados) FROM section_metadata WHERE votos_computados > 0 GROUP BY uf")).fetchall()
        for r in res:
            print(f"   UF: {r[0]} | Urnas Auditadas: {r[1]} | Total Votos Log: {r[2]}")

if __name__ == "__main__":
    check_audit()
