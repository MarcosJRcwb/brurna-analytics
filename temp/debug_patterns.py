
from sqlalchemy import create_engine, text
from config import config

engine = create_engine(config.POSTGRES_CONN)

def debug_patterns():
    query = """
    SELECT mensagem_padrao, aplicativo, severidade, ocorrencias 
    FROM log_patterns 
    WHERE mensagem_padrao LIKE 'Eleitor foi habilitado' 
       OR mensagem_padrao LIKE 'O voto do eleitor foi computado'
    """
    with engine.connect() as conn:
        results = conn.execute(text(query)).fetchall()
        print("🔍 Detalhes dos Padrões de Votação:")
        for r in results:
            print(f"  [{r[3]:8}] App: {r[1]:15} | Sev: {r[2]:10} | Msg: {r[0]}")

if __name__ == "__main__":
    debug_patterns()
