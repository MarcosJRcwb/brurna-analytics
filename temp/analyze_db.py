#!/usr/bin/env python3
"""
Script to analyze current database size and prepare for cleanup
"""
from sqlalchemy import create_engine, text
from config import config
import sys

def analyze_database():
    """Analyze current database state"""
    try:
        engine = create_engine(config.POSTGRES_CONN)
        conn = engine.connect()
        
        print("=" * 60)
        print("DATABASE ANALYSIS - BRURNA Analytics")
        print("=" * 60)
        
        # Database size
        result = conn.execute(text("SELECT pg_size_pretty(pg_database_size(current_database())) as size"))
        db_size = result.scalar()
        print(f"\n📊 Database Size: {db_size}")
        
        # Total rows
        result = conn.execute(text("SELECT COUNT(*) FROM logs"))
        total_rows = result.scalar()
        print(f"📝 Total Rows in 'logs': {total_rows:,}")
        
        # Size of logs table
        result = conn.execute(text("SELECT pg_size_pretty(pg_total_relation_size('logs')) as size"))
        table_size = result.scalar()
        print(f"📦 'logs' Table Size: {table_size}")
        
        # Breakdown by UF
        result = conn.execute(text("""
            SELECT uf, COUNT(*) as count, 
                   MIN(timestamp) as min_date, 
                   MAX(timestamp) as max_date
            FROM logs 
            GROUP BY uf 
            ORDER BY uf
        """))
        
        print("\n📍 Breakdown by UF:")
        print("-" * 60)
        for row in result:
            print(f"  {row[0]}: {row[1]:,} rows ({row[2]} to {row[3]})")
        
        # Sample data structure
        result = conn.execute(text("SELECT * FROM logs LIMIT 1"))
        row = result.fetchone()
        if row:
            print(f"\n🔍 Sample Row Columns: {len(row._mapping.keys())} columns")
            print(f"   Columns: {', '.join(row._mapping.keys())}")
        
        conn.close()
        
        print("\n" + "=" * 60)
        print("✅ Analysis Complete")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"❌ Error analyzing database: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = analyze_database()
    sys.exit(0 if success else 1)
