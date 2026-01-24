from sqlalchemy import create_engine, text
from config import config

print("String de conexão usada:", config.POSTGRES_CONN)

engine = create_engine(config.POSTGRES_CONN)

try:
    with engine.connect() as connection:
        # Teste SELECT
        result = connection.execute(text("SELECT 1"))
        print("Conexão bem-sucedida!")
        print("Resultado da query:", result.scalar())

        # Teste INSERT simples na tabela logs
        connection.execute(text("""
            INSERT INTO logs (uf, turno, linha_numero, timestamp, severidade, mensagem, raw_line)
            VALUES ('TEST', 1, 888, CURRENT_TIMESTAMP, 'INFO', 'Insert de teste do Python no Windows', 'Linha raw de teste 2026')
        """))
        connection.commit()
        print("INSERT de teste realizado com sucesso na tabela logs!")

        # Verificar o registro inserido
        result = connection.execute(text("SELECT * FROM logs ORDER BY created_at DESC LIMIT 1"))
        row = result.fetchone()
        print("Registro inserido (último):")
        print(row)

except Exception as e:
    print("Erro ao conectar ou inserir:")
    print(str(e))