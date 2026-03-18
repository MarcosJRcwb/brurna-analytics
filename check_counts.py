import os; import sys; sys.path.append('src')
from sqlalchemy import create_engine, text, pool
from config import config
engine = create_engine(config.LOCAL_POSTGRES_CONN, poolclass=pool.NullPool)
with engine.connect() as conn:
    print('Total Sections in DB:', conn.execute(text('SELECT COUNT(*) FROM section_metadata')).scalar())
    print('Total Patterns in DB:', conn.execute(text('SELECT COUNT(*) FROM log_patterns')).scalar())
    res = conn.execute(text("SELECT upper(uf), COUNT(*) FROM section_metadata GROUP BY 1 ORDER BY 1")).fetchall()
    for uf, count in res:
        print(f"UF {uf}: {count} seções")
