
from sqlalchemy import create_engine, text
from config import config
import re

engine = create_engine(config.POSTGRES_CONN)

def setup_db():
    print("🛠️  Configurando banco de dados...")
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE section_metadata ADD COLUMN IF NOT EXISTS modelo_urna VARCHAR(50)"))
        conn.execute(text("ALTER TABLE section_metadata ADD COLUMN IF NOT EXISTS votos_computados INTEGER DEFAULT 0"))
        conn.execute(text("ALTER TABLE section_metadata ADD COLUMN IF NOT EXISTS eleitores_habilitados INTEGER DEFAULT 0"))
        conn.commit()
    print("✅ Colunas de Auditoria e Modelo garantidas.")

def extract_models():
    # Busca qualquer mensagem que contenha UE seguido de 4 digitos
    query = "SELECT uf, mensagem_exemplo FROM log_patterns WHERE mensagem_exemplo ~* 'UE[0-9]{4}'"
    with engine.connect() as conn:
        results = conn.execute(text(query)).fetchall()
        
        if not results:
            print("⚠️ Nenhuma mensagem encontrada com padrão 'UE20xx'.")
            return

        models = {}
        for row in results:
            uf = row[0]
            msg = row[1]
            match = re.search(r'(UE\d{4})', msg, re.IGNORECASE)
            if match:
                model = match.group(1).upper()
                if uf not in models: models[uf] = set()
                models[uf].add(model)
        
        print("🏛️ Modelos detectados por UF:")
        for uf, m_list in models.items():
            print(f"   {uf}: {', '.join(sorted(list(m_list)))}")

if __name__ == "__main__":
    extract_models()

if __name__ == "__main__":
    extract_models()
