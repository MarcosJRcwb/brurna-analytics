
from sqlalchemy import create_engine, text
from config import config

engine = create_engine(config.POSTGRES_CONN)

def find_voting_patterns():
    query = """
    SELECT mensagem_exemplo, ocorrencias 
    FROM log_patterns 
    WHERE mensagem_exemplo ILIKE '%eleitor%' 
       OR mensagem_exemplo ILIKE '%voto%'
       OR mensagem_exemplo ILIKE '%votação%'
    ORDER BY ocorrencias DESC
    LIMIT 30
    """
    with engine.connect() as conn:
        results = conn.execute(text(query)).fetchall()
        print("🗳️ Padrões identificados para Auditoria BU:")
        for r in results:
            print(f"  [{r[1]:8}] {r[0]}")

if __name__ == "__main__":
    find_voting_patterns()
