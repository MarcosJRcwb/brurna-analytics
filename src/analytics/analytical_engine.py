
import pandas as pd
import re
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from sqlalchemy import create_engine, text
try:
    from config import config
except ImportError:
    # Fallback if running from root
    import config

import logging
from datetime import datetime
# Import new module
try:
    from analytics.g1_temporal import TemporalAnalyzer
    from analytics.g4_crosscheck import G4CrossChecker
except ImportError:
    # If running from root without package structure
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), '../'))
    from analytics.g1_temporal import TemporalAnalyzer
    from analytics.g4_crosscheck import G4CrossChecker

# Setup Logging
logging.basicConfig(
    filename='analytical_engine.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class AnalyticalEngine:
    def __init__(self, plan_path: str):
        self.plan_path = Path(plan_path)
        self.results_path = Path("analysis_results.csv")
        self.engine = create_engine(config.POSTGRES_CONN)
        
        # Initialize sub-modules
        self.temporal_analyzer = TemporalAnalyzer(self.engine)
        self.g4_checker = G4CrossChecker(self.engine)
        
        self.hypotheses = self._load_plan()
        
    def _load_plan(self):
        """Parse the markdown plan to extract hypotheses IDs and descriptions."""
        if not self.plan_path.exists():
            raise FileNotFoundError(f"Plan not found: {self.plan_path}")
            
        with open(self.plan_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Regex to find hypotheses like "**H001**: Description"
        pattern = r"\*\*H(\d{3})\*\*: (.*)"
        matches = re.findall(pattern, content)
        
        return {f"H{mid}": desc for mid, desc in matches}

    def run_check(self, h_id, description):
        """Dispatch logic based on ID ranges."""
        try:
            hid_int = int(h_id[1:])
            
            # Group 1: Temporal Dynamics (H001-H125)
            if 1 <= hid_int <= 125:
                # Try new batch processor first
                res = self.temporal_analyzer.run_g1_batch(h_id)
                if res != "PENDING": return res
                # Fallback to legacy
                return self._check_temporal(h_id, description)

            # Group 2: Hardware/Operational (H126-H250)
            elif 126 <= hid_int <= 250:
                return self._check_hardware_logs(h_id, description)

            # Group 3: Forensic/Security (H251-H375) 
            elif 251 <= hid_int <= 375:
                # Check for Benford (H391 moved or similar)
                # But mostly log scan
                return self._check_hardware_logs(h_id, description)

            # Group 4: Cross-Checks (H376-H500)
            elif 376 <= hid_int <= 500:
                 # Check Benford (H391, H460)
                 if h_id in ["H391", "H460"]:
                     return self.temporal_analyzer.run_g1_batch(h_id)
                 
                 # Delegate to G4 Module (ML & CrossCheck)
                 return self.g4_checker.run_g4_batch(h_id)

            # Group 3: Forensic/Security (H251-H375) 
            elif 251 <= hid_int <= 375:
                # Dispatch generic forensic log check (keywords like security, ass., hash)
                return self._check_hardware_logs(h_id, description) # Re-use generic for now

            # Group 4: Cross-Checks (H376-H500) - Some might be possible later
            elif 376 <= hid_int <= 500:
                 return "PENDING", "Logic not defined yet"
                
            return "SKIPPED", "Not Implemented Yet"
            
        except Exception as e:
            logging.error(f"Error checking {h_id}: {str(e)}")
            return "ERROR", str(e)

    def _check_temporal(self, h_id, description):
        """Execute SQL checks for Temporal group."""
        try:
            # H001: Morning (08-11) vs Afternoon (13-16) VPH
            # Schema: usage of 'quantidade' for vote count
            if h_id == "H001":
                query = text("""
                WITH periods AS (
                    SELECT 
                        SUM(CASE WHEN hora BETWEEN 8 AND 11 THEN quantidade ELSE 0 END) / 4.0 as avg_morning,
                        SUM(CASE WHEN hora BETWEEN 13 AND 16 THEN quantidade ELSE 0 END) / 4.0 as avg_afternoon
                    FROM temporal_metrics
                )
                SELECT 
                    CASE WHEN avg_morning > avg_afternoon THEN 'PASS' ELSE 'FAIL' END as status,
                    avg_morning, avg_afternoon
                FROM periods
                """)
                with self.engine.connect() as conn:
                    result = conn.execute(query).fetchone()
                    if not result: return "ERROR", "No data returned"
                    # status = "PASS" if result.avg_morning > result.avg_afternoon else "FAIL"
                    return result.status, f"Morning: {result.avg_morning:.1f}, Afternoon: {result.avg_afternoon:.1f}"

            # H002: Disabling temporarily due to join schema mismatch (section_id vs compound keys)
            if h_id == "H002":
                return "SKIPPED", "Join schema mapping pending"

            # H005: Lunch dip (12h) < 40% of daily average
            if h_id == "H005":
                query = text("""
                WITH hourly_avg AS (
                    SELECT hora, AVG(quantidade) as avg_votes
                    FROM temporal_metrics
                    WHERE hora BETWEEN 8 AND 17
                    GROUP BY hora
                )
                SELECT 
                    MAX(CASE WHEN hora = 12 THEN avg_votes END) as lunch_vol,
                    AVG(CASE WHEN hora != 12 THEN avg_votes END) as rest_avg
                FROM hourly_avg
                """)
                with self.engine.connect() as conn:
                    result = conn.execute(query).fetchone()
                    if not result.rest_avg or result.rest_avg == 0: return "SKIP", "No baseline data"
                    # Fix: Ensure float arithmetic
                    lunch = float(result.lunch_vol or 0)
                    rest = float(result.rest_avg)
                    drop = 1.0 - (lunch / rest)
                    status = "PASS" if drop > 0.4 else "FAIL"
                    return status, f"Lunch avg: {lunch:.1f}, Rest avg: {rest:.1f} (Drop: {drop*100:.1f}%)"

            # H003: Variância do tempo entre votos (Inter-arrival time)
            if h_id == "H003":
                # PROXY: Usar variância da quantidade por hora como proxy de fluxo
                query = text("""
                SELECT VARIANCE(quantidade) as var_vph, uf
                FROM temporal_metrics
                WHERE hora BETWEEN 8 AND 17
                GROUP BY uf
                """)
                with self.engine.connect() as conn:
                    result = conn.execute(query).fetchall()
                    obs = ", ".join([f"{row.uf}: {row.var_vph:.1f}" for row in result])
                    return "INFO", f"Variância de Fluxo (Proxy): {obs}"

            # H011: Spikes > 3 Sigma (Volume Anomalies)
            if h_id == "H011":
                query = text("""
                WITH stats AS (
                    SELECT AVG(quantidade) as mu, STDDEV(quantidade) as sigma
                    FROM temporal_metrics
                    WHERE hora BETWEEN 8 AND 17
                ),
                anomalies AS (
                    SELECT COUNT(*) as cnt
                    FROM temporal_metrics tm, stats s
                    WHERE tm.hora BETWEEN 8 AND 17
                    AND tm.quantidade > (s.mu + 3 * s.sigma)
                )
                SELECT cnt FROM anomalies
                """)
                with self.engine.connect() as conn:
                    cnt = conn.execute(query).scalar()
                    # If anomalies exist, are they only in peak hours? 
                    # Simplified check: if anomalies count is low (< 1%), it's expected/PASS?
                    # Or H011 says "Occur ONLY in peak hours".
                    # For now, just detecting if exists.
                    return ("FAIL (Anomaly)" if cnt > 0 else "PASS"), f"Found {cnt} outliers > 3 sigma"

            # H012: Clock Drift (Future Timestamps)
            if h_id == "H012":
                query = text("SELECT COUNT(*) FROM log_eventos WHERE timestamp > NOW()")
                with self.engine.connect() as conn:
                    cnt = conn.execute(query).scalar()
                    return ("FAIL" if cnt > 0 else "PASS"), f"Future logs found: {cnt}"
            
            # H013: Pre-Boot Votes (Before 07:00)
            if h_id == "H013":
                # Assuming election start 08:00, boot 07:00. Votes before 07:00 are wierd.
                query = text("SELECT COUNT(*) FROM log_eventos WHERE EXTRACT(HOUR FROM timestamp) < 7")
                with self.engine.connect() as conn:
                    cnt = conn.execute(query).scalar()
                    return ("INFO" if cnt > 0 else "PASS"), f"Early morning logs: {cnt}"

            # H020: Error Rate < 0.1%
            if h_id == "H020":
                query = text("""
                SELECT 
                    SUM(CASE WHEN level IN ('ERROR','CRITICAL') THEN 1 ELSE 0 END) as errors,
                    COUNT(*) as total
                FROM log_eventos
                """)
                with self.engine.connect() as conn:
                    res = conn.execute(query).fetchone()
                    if not res or res.total == 0: return "INFO", "No logs to parse"
                    rate = (res.errors / res.total) * 100
                    status = "PASS" if rate < 0.1 else "FAIL"
                    return status, f"Error Rate: {rate:.4f}% ({res.errors}/{res.total})"

            # H030: Monotonic Clock Check
            if h_id == "H030":
                # Expensive check, sample or limit? checking last 1000 for speed
                query = text("""
                WITH ordered AS (
                    SELECT timestamp, LAG(timestamp) OVER (ORDER BY id) as prev
                    FROM log_eventos
                    ORDER BY id DESC
                    LIMIT 1000
                )
                SELECT COUNT(*) FROM ordered WHERE timestamp < prev
                """)
                with self.engine.connect() as conn:
                    cnt = conn.execute(query).scalar()
                    return ("FAIL" if cnt > 0 else "PASS"), f"Time inversions found (Scanning sample): {cnt}"


            # H009: Tempo médio de votação (Proxy via VPH)
            if h_id == "H009":
                # Se VPH é alto, tempo é baixo. 
                # Benchmarks reais: 1 min/voto = 60 VPH. 
                query = text("SELECT AVG(quantidade) as avg_vph FROM temporal_metrics WHERE hora BETWEEN 8 AND 17")
                with self.engine.connect() as conn:
                    avg = conn.execute(query).scalar()
                    # Approx duration = 60 mins / avg_vph * 60 seconds
                    if not avg or avg == 0: return "SKIP", "No data"
                    sec_per_vote = 3600 / float(avg)
                    return "INFO", f"Est. Duration: {sec_per_vote:.1f}s (Avg VPH: {avg:.1f})"

            # H037: Turno 2 vs Turno 1 Volume
            if h_id == "H037":
                query = text("""
                SELECT turno, AVG(quantidade) as avg_vol 
                FROM temporal_metrics 
                WHERE hora BETWEEN 8 AND 17 
                GROUP BY turno
                """)
                with self.engine.connect() as conn:
                    rows = conn.execute(query).fetchall()
                    data = {r.turno: r.avg_vol for r in rows}
                    if 1 not in data or 2 not in data: return "SKIP", "Turno data missing"
                    
                    # Expect Turno 2 > Turno 1 (Faster voting) -> Higher VPH?
                    # Or Turno 2 has less abstention? Usually Turno 2 is faster.
                    status = "PASS" if data[2] > data[1] else "INFO"
                    return status, f"T1: {data[1]:.0f}, T2: {data[2]:.0f}"

            # H040: Uptime (Ligada < 14h)
            if h_id == "H040":
                query = text("""
                SELECT source_file, (MAX(timestamp) - MIN(timestamp)) as uptime
                FROM log_eventos
                GROUP BY source_file
                LIMIT 100
                """)
                with self.engine.connect() as conn:
                    rows = conn.execute(query).fetchall()
                    # Check if any > 14 hours
                    long_runners = [r for r in rows if r.uptime.total_seconds() > 14*3600]
                    cnt = len(long_runners)
                    return ("FAIL" if cnt > 0 else "PASS"), f"Urnas > 14h found: {cnt}"

            
            return "PENDING", "Logic not defined yet"
            
        except Exception as e:
            return "ERROR", str(e)

    def _check_hardware_logs(self, h_id, description):
        """
        Generic check for hardware/operational logs using keyword matching against log_eventos.
        """
        try:
            # maintain connection
            if self.engine is None:
                 self.engine = create_engine(config.POSTGRES_CONN)

            # Smart Keyword Extraction
            keywords = []
            desc_lower = description.lower()
            
            if "bateria" in desc_lower: keywords.extend(["bateria", "battery", "carga"])
            if "boot" in desc_lower or "inicializa" in desc_lower: keywords.extend(["boot", "start", "inic", "ligar"])
            if "reboot" in desc_lower or "reinic" in desc_lower: keywords.extend(["reboot", "reinic", "shutdown"])
            if "energi" in desc_lower or "tensão" in desc_lower: keywords.extend(["energia", "tensão", "voltage", "power"])
            if "papel" in desc_lower or "impress" in desc_lower: keywords.extend(["papel", "bobina", "impress", "printer"])
            if "biometri" in desc_lower: keywords.extend(["bio", "finger", "dacty"])
            if "touch" in desc_lower or "tela" in desc_lower: keywords.extend(["touch", "screen", "tela", "calib"])
            if "usb" in desc_lower or "midia" in desc_lower: keywords.extend(["usb", "flash", "pendrive", "midia"])
            if "viol" in desc_lower or "lacre" in desc_lower: keywords.extend(["viol", "intrus", "lacre", "romp"])
            if "assinatura" in desc_lower: keywords.extend(["assinatura", "sign", "hash"])
            
            # Default fallback
            if not keywords:
                # Use significant words (len > 4)
                keywords = [w for w in desc_lower.split() if len(w) > 4][:1]
                if not keywords: keywords = ["erro"]

            # Construct ILIKE query OR
            conditions = " OR ".join([f"message ILIKE '%%{k}%%'" for k in keywords])
            
            sql = text(f"SELECT COUNT(*) FROM log_eventos WHERE {conditions}")
            
            with self.engine.connect() as conn:
                result = conn.execute(sql).scalar()
            
            status = "INFO"
            obs = f"Found {result} logs matching keywords: {keywords}"
            
            # Heuristic: If we expect "No logs" (e.g. "Não há logs de erro") and count > 0 -> FAIL?
            # Too risky for generic. Stick to INFO.
            if "não há" in desc_lower or "não existe" in desc_lower:
                if result > 0:
                    status = "FAIL (Anomaly)"
                else:
                    status = "PASS"
            
            return status, obs

        except Exception as e:
            return "SKIPPED", f"Log Check Error: {e}"

    def execute_all(self):
        """Run all loaded hypotheses and save results."""
        results = []
        print(f"🚀 Starting execution of {len(self.hypotheses)} hypotheses...")
        
        for h_id, desc in self.hypotheses.items():
            print(f"Processing {h_id}...", end="\r")
            status, observation = self.run_check(h_id, desc)
            results.append({
                "ID": h_id,
                "Description": desc,
                "Status": status,
                "Observation": observation,
                "Timestamp": datetime.now().isoformat()
            })
            
        df_res = pd.DataFrame(results)
        df_res.to_csv(self.results_path, index=False)
        print(f"\n✅ Execution completed. Results saved to {self.results_path}")

if __name__ == "__main__":
    # Pointing to the definitive brain artifact
    PLAN_PATH = r"C:\Users\marco\.gemini\antigravity\brain\823a5e8b-dcb0-4e8e-84b0-5afb5d3b200b\plano_analise_500_final.md"
    
    engine = AnalyticalEngine(PLAN_PATH)
    engine.execute_all()
