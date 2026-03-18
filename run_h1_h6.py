import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from sqlalchemy import create_engine, text
from config import config

engine = create_engine(config.POSTGRES_CONN)
lines = []

def p(s=""):
    lines.append(s)
    print(s)

with engine.connect() as conn:
    total_sections = conn.execute(text("SELECT COUNT(*) FROM section_metadata")).scalar()
    total_metrics = conn.execute(text("SELECT COUNT(*) FROM temporal_metrics")).scalar()
    total_patterns = conn.execute(text("SELECT COUNT(*) FROM log_patterns")).scalar()
    total_exceptions = conn.execute(text("SELECT COUNT(*) FROM log_exceptions")).scalar()
    total_mesarios = conn.execute(text("SELECT COUNT(*) FROM mesarios")).scalar()
    ufs = conn.execute(text("SELECT DISTINCT uf FROM section_metadata ORDER BY uf")).fetchall()
    
    p("BASE DE DADOS:")
    p(f"  Secoes: {total_sections}")
    p(f"  Metricas temporais: {total_metrics}")
    p(f"  Padroes: {total_patterns}")
    p(f"  Excecoes: {total_exceptions}")
    p(f"  Mesarios: {total_mesarios}")
    p(f"  UFs: {', '.join([r[0] for r in ufs])}")
    
    # H001
    r = conn.execute(text("""
        SELECT 
            SUM(CASE WHEN hora BETWEEN 8 AND 11 THEN quantidade ELSE 0 END) as manha,
            SUM(CASE WHEN hora BETWEEN 13 AND 16 THEN quantidade ELSE 0 END) as tarde
        FROM temporal_metrics
    """)).fetchone()
    manha = r[0] or 0
    tarde = r[1] or 0
    p(f"\nH001 Manha vs Tarde: Manha={manha}, Tarde={tarde} -> {'PASS' if manha > tarde else 'FAIL'}")
    
    # H002
    p(f"H002 Secoes grandes vs pequenas: SKIPPED (join pending)")
    
    # H003
    rows = conn.execute(text("""
        SELECT uf, VARIANCE(quantidade) as var, AVG(quantidade) as avg, COUNT(*) as n
        FROM temporal_metrics WHERE hora BETWEEN 8 AND 17 GROUP BY uf ORDER BY var DESC
    """)).fetchall()
    p(f"\nH003 Variancia por UF:")
    for r in rows:
        p(f"  {r[0]}: var={r[1]:.1f}, media={r[2]:.1f}, n={r[3]}")
    
    # H004
    rows = conn.execute(text("""
        SELECT uf, MAX(quantidade) as max_vph FROM temporal_metrics GROUP BY uf ORDER BY max_vph DESC
    """)).fetchall()
    p(f"\nH004 Max VPH por UF:")
    for r in rows:
        p(f"  {r[0]}: max_vph={r[1]}")
    
    # H005
    r = conn.execute(text("""
        WITH h AS (
            SELECT hora, AVG(quantidade) as avg FROM temporal_metrics WHERE hora BETWEEN 8 AND 17 GROUP BY hora
        )
        SELECT MAX(CASE WHEN hora=12 THEN avg END) as lunch, AVG(CASE WHEN hora!=12 THEN avg END) as rest FROM h
    """)).fetchone()
    lunch = float(r[0] or 0)
    rest = float(r[1] or 0)
    drop = (1.0 - (lunch / rest)) * 100 if rest > 0 else 0
    p(f"\nH005 Queda no almoco: lunch={lunch:.1f}, rest={rest:.1f}, drop={drop:.1f}% -> {'PASS' if drop > 40 else 'FAIL'}")
    
    # H006
    r = conn.execute(text("""
        SELECT COUNT(*) as total,
            COUNT(CASE WHEN EXTRACT(HOUR FROM periodo_inicio) < 7 THEN 1 END) as antes_7,
            COUNT(CASE WHEN EXTRACT(HOUR FROM periodo_inicio) = 7 THEN 1 END) as as_7,
            COUNT(CASE WHEN EXTRACT(HOUR FROM periodo_inicio) = 8 THEN 1 END) as as_8,
            COUNT(CASE WHEN EXTRACT(HOUR FROM periodo_inicio) > 8 THEN 1 END) as apos_8
        FROM section_metadata WHERE periodo_inicio IS NOT NULL
    """)).fetchone()
    p(f"\nH006 Horarios de inicio:")
    p(f"  Total com horario: {r[0]}")
    p(f"  Antes 07h: {r[1]}")
    p(f"  07h: {r[2]}")
    p(f"  08h: {r[3]}")
    p(f"  Apos 09h: {r[4]}")

# Save to file
with open("h1_h6_results.txt", "w") as f:
    f.write("\n".join(lines))
    
p("\nSalvo em h1_h6_results.txt")
