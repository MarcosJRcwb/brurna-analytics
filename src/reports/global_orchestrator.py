
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from src.reports.engine import ReportingEngine

def run_global():
    engine = ReportingEngine(db_mode='local')
    print("🚀 Iniciando Relatório Global 1T...")
    try:
        path = engine.generate_report("GLOBAL", "NACIONAL", mode='national')
        print(f"✅ Relatório concluído: {path}")
    except Exception as e:
        print(f"❌ Erro: {e}")
        engine._update_global_status(0, status=f"error: {str(e)}")

if __name__ == "__main__":
    run_global()
