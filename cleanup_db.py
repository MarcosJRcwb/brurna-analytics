
from sqlalchemy import create_engine, text
from config import config

engine = create_engine(config.POSTGRES_CONN)

def cleanup_mg():
    with engine.connect() as conn:
        print("🔍 Verificando registros de MG nas novas tabelas...")
        for table in ['log_patterns', 'temporal_metrics', 'section_metadata']:
            count = conn.execute(text(f"SELECT COUNT(*) FROM {table} WHERE uf = 'MG'")).scalar()
            print(f"   - {table} (MG): {count} registros")
            
            if count > 0:
                print(f"   🗑️ Removendo registros de MG em {table}...")
                conn.execute(text(f"DELETE FROM {table} WHERE uf = 'MG'"))
        
        # Verifica se ainda existe a tabela logs antiga por algum motivo
        from sqlalchemy import inspect
        inspector = inspect(engine)
        if 'logs' in inspector.get_table_names():
            print("⚠️ A tabela 'logs' antiga ainda existe! Dropando agora...")
            conn.execute(text("DROP TABLE logs CASCADE"))
            print("✅ Tabela 'logs' (40GB) removida definitivamente.")
        
        conn.commit()
        print("\n✅ Limpeza de MG concluída.")

if __name__ == "__main__":
    cleanup_mg()
