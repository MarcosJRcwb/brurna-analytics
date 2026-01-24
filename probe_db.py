
from sqlalchemy import create_engine, text, inspect
from config import config

engine = create_engine(config.POSTGRES_CONN)

def probe_database():
    with engine.connect() as conn:
        print("🕵️ Investigação de tabelas no banco Contabo...")
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        for table in tables:
            size_query = f"SELECT pg_size_pretty(pg_total_relation_size('{table}'))"
            count_query = f"SELECT COUNT(*) FROM {table}"
            try:
                size = conn.execute(text(size_query)).scalar()
                count = conn.execute(text(count_query)).scalar()
                print(f"📋 Tabela: {table}")
                print(f"   - Tamanho: {size}")
                print(f"   - Linhas: {count}")
                
                # Tenta ver se tem coluna uf ou algo que identifique MG
                cols = [c['name'] for c in inspector.get_columns(table)]
                if 'uf' in cols:
                    mg_count = conn.execute(text(f"SELECT COUNT(*) FROM {table} WHERE uf ILIKE 'MG'")).scalar()
                    print(f"   - Registros MG: {mg_count}")
            except Exception as e:
                print(f"   - Erro ao sondar {table}: {e}")
        
        # Verifica se há alguma tabela que parece ser backup ou antiga
        print("\n🔍 Verificando esquemas e tabelas ocultas...")
        result = conn.execute(text("SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname = 'public'"))
        for row in result:
            if row[0] not in tables:
                print(f"   - Tabela encontrada via pg_catalog: {row[0]}")

if __name__ == "__main__":
    probe_database()
