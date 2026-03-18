import psycopg2
try:
    conn = psycopg2.connect('postgresql://postgres:brurna2024@localhost:5432/postgres')
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'brurna_db' AND pid <> pg_backend_pid()")
    print("Sucesso: Todas as conexões com brurna_db foram encerradas.")
    cur.close()
    conn.close()
except Exception as e:
    print(f"Erro ao encerrar conexões: {e}")
