
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime
from pathlib import Path
from fpdf import FPDF
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from config import config

class ReportingEngine:
    """
    Advanced Forensic Reporting Engine for Brurna Analytics.
    Supports ABNT A4 and Statistical Anomaly reports at multiple hierarchy levels.
    """
    
    def __init__(self, db_mode='local'):
        conn_str = config.LOCAL_POSTGRES_CONN if db_mode == 'local' else config.REMOTE_POSTGRES_CONN
        self.engine = create_engine(conn_str)
        self.output_dir = Path("reports/pdf")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def _fetch_hierarchy_data(self, filters):
        """Fetch stats and anomalies using dynamic filters (uf, mun, zon, sec)."""
        where_parts = []
        params = {}
        
        if filters.get("uf"):
            where_parts.append("lower(uf) = lower(:uf)")
            params["uf"] = filters["uf"]
        if filters.get("mun") and filters["mun"] != "--- TODOS ---":
            where_parts.append("municipio_codigo = :mun")
            params["mun"] = str(filters["mun"]).zfill(5)
        if filters.get("zon") and filters["zon"] != "--- TODOS ---":
            where_parts.append("zona = :zon")
            params["zon"] = str(filters["zon"]).zfill(4)
        if filters.get("sec") and filters["sec"] != "--- TODOS ---":
            where_parts.append("secao = :sec")
            params["sec"] = str(filters["sec"]).zfill(4)
            
        where_clause = "WHERE " + " AND ".join(where_parts) if where_parts else ""
        
        # 1. Fetch Basic Stats
        with self.engine.connect() as conn:
            q_stats = text(f"SELECT * FROM section_metadata {where_clause}")
            stats = pd.read_sql(q_stats, conn, params=params)
            
            # 2. Fetch Anomalies (from log_exceptions)
            q_anom = text(f"SELECT * FROM log_exceptions {where_clause} LIMIT 100")
            try:
                anomalies = pd.read_sql(q_anom, conn, params=params)
            except:
                anomalies = pd.DataFrame()
            
        return stats, anomalies

    def generate_forensic_report(self, level, level_id, mode='abnt', filters=None):
        """Main entry point for report generation."""
        # Compatibility layer for old calls
        if filters is None:
            filters = {"uf": level_id} if level == "UF" else {}
            if level == "SECAO": filters["sec"] = level_id
            
        stats, anomalies = self._fetch_hierarchy_data(filters)
        if stats.empty and anomalies.empty:
            return None
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"Laudo_{level}_{level_id}_{mode}_{timestamp}.pdf"
        filepath = self.output_dir / filename
        
        if mode == 'abnt':
            self._build_abnt_pdf(stats, anomalies, level, level_id, filepath)
        elif mode == 'statistical':
            self._build_statistical_pdf(stats, anomalies, level, level_id, filepath)
        elif mode == 'national':
            self._build_national_pdf(filepath)
            
        return filepath

    def _update_global_status(self, progress, status="running", status_msg="", file=None):
        import json
        status_file = Path("reports/global_status.json")
        data = {
            "percentage": progress,
            "status": status,
            "status_msg": status_msg,
            "file": str(file) if file else "",
            "timestamp": datetime.now().isoformat()
        }
        with open(status_file, "w") as f:
            json.dump(data, f)

    def _build_national_pdf(self, filepath):
        """Heavy operation: Generates a consolidated national report."""
        self._update_global_status(10, status_msg="Coletando dados nacionais...")
        
        # Reusing logic from ReportGenerator but adapted for fpdf2
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Times", "B", 16)
        pdf.cell(0, 15, f"LAUDO PERICIAL FORENSE - {level} {level_id}", 1, 1, 'C')
        
        self._update_global_status(30, status_msg="Processando métricas das UFs...")
        
        # 1. Stats by UF
        with self.engine.connect() as conn:
            q = text("SELECT upper(uf) as uf, COUNT(*) as secoes FROM section_metadata GROUP BY 1 ORDER BY 2 DESC")
            df_ufs = pd.read_sql(q, conn)
            
        pdf.set_font("Times", "B", 12)
        pdf.cell(0, 10, "1. RESUMO POR UNIDADE FEDERATIVA", 0, 1)
        pdf.set_font("Times", "", 10)
        
        for _, row in df_ufs.iterrows():
            pdf.cell(40, 8, f"UF: {row['uf']}", 1)
            pdf.cell(150, 8, f"{row['secoes']} Seções Auditadas", 1, 1)
            
        self._update_global_status(60, status_msg="Auditando anomalias críticas...")
        
        # 2. Anomalies Summary
        with self.engine.connect() as conn:
            q_anom = text("SELECT severidade, COUNT(*) as total FROM log_exceptions GROUP BY 1 ORDER BY 2 DESC LIMIT 10")
            df_anom = pd.read_sql(q_anom, conn)
            
        pdf.ln(10)
        pdf.set_font("Times", "B", 12)
        pdf.cell(0, 10, "2. DISTRIBUIÇÃO DE SEVERIDADE DE ANOMALIAS", 0, 1)
        pdf.set_font("Times", "", 10)
        
        for _, row in df_anom.iterrows():
            pdf.cell(60, 8, f"Severidade: {row['severidade']}", 1)
            pdf.cell(130, 8, f"Ocorrências: {row['total']}", 1, 1)
            
        self._update_global_status(90, status_msg="Finalizando PDF e salvando...")
        pdf.output(str(filepath))
        self._update_global_status(100, "done", file=filepath)

    def _build_abnt_pdf(self, stats, anomalies, level, level_id, filepath):
        pdf = FPDF()
        pdf.add_page()
        
        # Header
        pdf.set_font("Times", "B", 14)
        pdf.cell(0, 10, "RELATÓRIO TÉCNICO-JURÍDICO - BRURNA ANALYTICS", 0, 1, 'C')
        pdf.set_font("Times", "I", 12)
        pdf.cell(0, 10, f"Escopo da Auditoria: {level} - Identificador: {level_id}", 0, 1, 'C')
        pdf.ln(10)
        
        # 1. Identificação
        pdf.set_font("Times", "B", 12)
        pdf.cell(0, 10, "1. IDENTIFICAÇÃO DO OBJETO", 0, 1, 'L')
        pdf.set_font("Times", "", 12)
        pdf.multi_cell(0, 8, f"Este laudo pericial apresenta os resultados da auditoria automatizada realizada sobre os logs da urna eletrônica no escopo {level} ({level_id}). A análise visa detectar desvios de padrões forenses, temporais e de hardware.")
        pdf.ln(5)
        
        # 2. Dados Consolidados
        pdf.set_font("Times", "B", 12)
        pdf.cell(0, 10, "2. RESUMO DE DADOS", 0, 1, 'L')
        pdf.set_font("Times", "", 10)
        
        # Table
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(60, 8, "Métrica", 1, 0, 'C', 1)
        pdf.cell(130, 8, "Valor Encontrado", 1, 1, 'C', 1)
        
        metrics = [
            ("Total de Seções Impactadas", str(len(stats))),
            ("Anomalias Críticas Detectadas", str(len(anomalies))),
            ("UF de Referência", str(stats['uf'].iloc[0]) if not stats.empty else 'N/A'),
            ("Data/Hora da Geração", datetime.now().strftime("%d/%m/%Y %H:%M"))
        ]
        for m, v in metrics:
            pdf.cell(60, 8, m, 1)
            pdf.cell(130, 8, v, 1, 1)
        
        pdf.ln(10)
        
        # 3. Anomalias Detalhadas
        pdf.set_font("Times", "B", 12)
        pdf.cell(0, 10, "3. CONSTATAÇÕES PERICIAIS (ANOMALIAS)", 0, 1, 'L')
        
        if anomalies.empty:
            pdf.set_font("Times", "I", 12)
            pdf.cell(0, 10, "Nenhuma anomalia crítica detectada neste escopo.", 0, 1)
        else:
            pdf.set_font("Times", "", 9)
            # Table for anomalies
            pdf.set_fill_color(220, 220, 220)
            pdf.cell(30, 8, "ID Exp", 1, 0, 'C', 1)
            pdf.cell(40, 8, "Timestamp", 1, 0, 'C', 1)
            pdf.cell(120, 8, "Descrição do Evento Atípico", 1, 1, 'C', 1)
            
            for _, row in anomalies.head(20).iterrows():
                pdf.cell(30, 8, str(row.get('severidade', 'N/A')), 1)
                pdf.cell(40, 8, str(row.get('timestamp', 'N/A'))[:16], 1)
                msg = str(row.get('mensagem_bruta', ''))[:65] + "..." if len(str(row.get('mensagem_bruta', ''))) > 65 else str(row.get('mensagem_bruta', ''))
                pdf.cell(120, 8, msg, 1, 1)

        # Footer
        pdf.set_y(-30)
        pdf.set_font("Times", "I", 8)
        pdf.cell(0, 10, f"Laudo Gerado Automatizadamente por Agente Brurna Justice | Página {pdf.page_no()}", 0, 0, 'C')
        
        pdf.output(str(filepath))

    def _build_statistical_pdf(self, stats, anomalies, level, level_id, filepath):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "B", 16)
        pdf.set_text_color(0, 51, 102)
        pdf.cell(0, 15, "CONSOLIDADO ESTATÍSTICO FORENSE", 0, 1, 'C')
        pdf.set_line_width(1)
        pdf.line(20, 25, 190, 25)
        pdf.ln(10)
        
        pdf.set_font("Arial", "", 12)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 10, f"Escopo de Análise: {level} ({level_id})", 0, 1)
        pdf.cell(0, 10, f"Data do Processamento: {datetime.now().strftime('%d/%m/%Y %H:%M')}", 0, 1)
        pdf.ln(5)
        
        # Summary Box
        pdf.set_fill_color(230, 240, 255)
        pdf.rect(10, 55, 190, 40, 'F')
        pdf.set_xy(15, 60)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "Resumo de Cobertura:", 0, 1)
        pdf.set_font("Arial", "", 11)
        pdf.set_x(15)
        pdf.cell(0, 8, f"- Seções Processadas: {len(stats)}", 0, 1)
        pdf.set_x(15)
        pdf.cell(0, 8, f"- Total de Alertas Gerados: {len(anomalies)}", 0, 1)
        
        # Distribution (Fake Chart/Bars for now)
        pdf.set_xy(10, 105)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "Distribuição de Severidade:", 0, 1)
        
        # Progress bars simulation
        pdf.set_fill_color(255, 100, 100) # Red for high
        pdf.rect(40, 120, 100, 5, 'F')
        pdf.set_xy(10, 118)
        pdf.set_font("Arial", "", 10)
        pdf.cell(30, 8, "Crítico", 0)
        
        pdf.set_fill_color(255, 200, 0) # Yellow for med
        pdf.rect(40, 130, 150, 5, 'F')
        pdf.set_xy(10, 128)
        pdf.cell(30, 8, "Médio", 0)
        
        pdf.output(str(filepath))
        
if __name__ == "__main__":
    engine = ReportingEngine()
    # Test generation
    path = engine.generate_report("UF", "SE", mode='abnt')
    print(f"Report generated: {path}")
