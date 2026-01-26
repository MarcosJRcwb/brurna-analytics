"""
Gerador de Relatórios Forenses do TSE
Gera relatórios técnico-jurídicos em PDF/Docx a partir de análises eleitorais
"""
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime
from pathlib import Path
import sys
import os

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))
from config import config

class ReportGenerator:
    """
    Gerador de Relatórios Técnicos do Brurna Analytics
    
    Capabilities:
    - Relatório Nacional (consolidado)
    - Relatório por UF
    - Fundamentação jurídica via TSE Justice
    - Export: PDF, Docx, HTML
    """
    
    def __init__(self):
        self.engine = create_engine(config.POSTGRES_CONN)
        self.results_path = Path("analysis_results.csv")
        
    def _collect_national_data(self):
        """Coleta dados agregados nacionais"""
        df_results = pd.read_csv(self.results_path)
        
        # Métricas gerais
        total = len(df_results)
        covered = len(df_results[df_results['Status'].isin(['PASS', 'INFO', 'FAIL', 'FAIL (Anomaly)'])])
        anomalies = df_results[df_results['Status'].str.contains('FAIL|Anomaly', na=False)]
        
        # Dados do banco
        with self.engine.connect() as conn:
            total_logs = conn.execute(text("SELECT COUNT(*) FROM log_eventos")).scalar()
            total_sections = conn.execute(text("SELECT COUNT(DISTINCT source_file) FROM log_eventos")).scalar()
            
        return {
            'total_hipoteses': total,
            'cobertura_pct': (covered / 500) * 100,
            'anomalias': anomalies,
            'total_logs': total_logs,
            'total_sections': total_sections,
            'timestamp': datetime.now()
        }
    
    def _collect_uf_data(self, uf):
        """Coleta dados específicos de uma UF"""
        query = text(f"""
        SELECT COUNT(*) as total
        FROM log_eventos
        WHERE source_file LIKE '%/{uf.lower()}/%' OR source_file LIKE '%\\{uf.lower()}\\%'
        """)
        
        with self.engine.connect() as conn:
            uf_logs = conn.execute(query).scalar()
            
        return {
            'uf': uf.upper(),
            'total_logs': uf_logs,
            'timestamp': datetime.now()
        }
    
    def generate_national_report_html(self, output_path='relatorio_nacional.html'):
        """Gera relatório nacional em HTML"""
        data = self._collect_national_data()
        
        html_content = f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Relatório Técnico Brurna Analytics - Nacional</title>
    <style>
        body {{ font-family: 'Times New Roman', serif; margin: 40px; line-height: 1.6; }}
        h1 {{ color: #003366; border-bottom: 3px solid #003366; padding-bottom: 10px; }}
        h2 {{ color: #0066cc; margin-top: 30px; }}
        .metric {{ background: #f0f0f0; padding: 15px; margin: 10px 0; border-left: 4px solid #0066cc; }}
        .anomaly {{ background: #fff3cd; padding: 10px; margin: 5px 0; border-left: 4px solid #ff9800; }}
        .footer {{ margin-top: 50px; font-size: 0.9em; color: #666; border-top: 1px solid #ccc; padding-top: 20px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #003366; color: white; }}
    </style>
</head>
<body>
    <h1>RELATÓRIO TÉCNICO-JURÍDICO BRURNA ANALYTICS</h1>
    <h2>Análise Nacional Consolidada</h2>
    
    <div class="metric">
        <strong>Período de Análise:</strong> {data['timestamp'].strftime('%d/%m/%Y %H:%M')}<br>
        <strong>Estados Analisados:</strong> AC, AP, RR, TO, SE<br>
        <strong>Total de Logs Processados:</strong> {data['total_logs']:,}<br>
        <strong>Total de Seções:</strong> {data['total_sections']:,}
    </div>
    
    <h2>I. SUMÁRIO EXECUTIVO</h2>
    <div class="metric">
        <strong>Cobertura de Hipóteses:</strong> {data['cobertura_pct']:.1f}% ({data['total_hipoteses']} de 500)<br>
        <strong>Anomalias Detectadas:</strong> {len(data['anomalias'])}<br>
        <strong>Status Geral:</strong> {'CONFORME' if len(data['anomalias']) < 10 else 'REQUER ATENÇÃO'}
    </div>
    
    <h2>II. ANOMALIAS DETECTADAS</h2>
    <table>
        <tr>
            <th>ID</th>
            <th>Descrição</th>
            <th>Status</th>
            <th>Observação</th>
        </tr>
"""
        
        for _, row in data['anomalias'].head(20).iterrows():
            html_content += f"""
        <tr>
            <td>{row['ID']}</td>
            <td>{row['Description'][:80]}...</td>
            <td>{row['Status']}</td>
            <td>{row['Observation'][:100]}...</td>
        </tr>
"""
        
        html_content += f"""
    </table>
    
    <h2>III. PARECER JURÍDICO</h2>
    <p><strong>Fundamentação Legal:</strong> Art. 5º da Resolução TSE 23.603/2019</p>
    <p>
    Com base na análise estatística realizada pelo sistema Brurna Analytics, 
    conclui-se que os dados apresentam <strong>indícios</strong> de comportamento 
    atípico em {len(data['anomalias'])} hipóteses ({len(data['anomalias'])/500*100:.1f}% do total).
    </p>
    <p>
    Tais indícios, por si sós, não configuram prova material de irregularidade 
    eleitoral, mas merecem aprofundamento mediante auditoria complementar, 
    nos termos do art. 103 do Código Eleitoral.
    </p>
    
    <h2>IV. RECOMENDAÇÕES</h2>
    <ul>
        <li>Auditoria física das urnas com anomalias detectadas</li>
        <li>Verificação de lacres e BU impresso vs. digital</li>
        <li>Análise forense de logs com timestamps suspeitos</li>
        <li>Monitoramento contínuo em eleições futuras</li>
    </ul>
    
    <div class="footer">
        <p><strong>AVISO LEGAL:</strong> Este relatório é gerado por sistema automatizado de análise estatística 
        e não substitui perícia oficial da Justiça Eleitoral. Os pareceres jurídicos são fundamentados em 
        legislação vigente e jurisprudência, mas não constituem decisão judicial. Uso restrito para fins de 
        auditoria interna e transparência.</p>
        <p><strong>Gerado em:</strong> {data['timestamp'].strftime('%d/%m/%Y às %H:%M:%S')}</p>
        <p><strong>Sistema:</strong> Brurna Analytics v1.0 | <strong>Agente:</strong> TSE Justice</p>
    </div>
</body>
</html>
"""
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
            
        print(f"✅ Relatório nacional gerado: {output_path}")
        return output_path
    
    def generate_uf_report_html(self, uf, output_path=None):
        """Gera relatório específico de UF em HTML"""
        if output_path is None:
            output_path = f'relatorio_{uf.lower()}.html'
            
        data = self._collect_uf_data(uf)
        national_data = self._collect_national_data()
        
        # Calcular percentual da UF em relação ao total
        pct_nacional = (data['total_logs'] / national_data['total_logs'] * 100) if national_data['total_logs'] > 0 else 0
        
        html_content = f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Relatório Técnico - {uf.upper()}</title>
    <style>
        body {{ font-family: 'Times New Roman', serif; margin: 40px; line-height: 1.6; }}
        h1 {{ color: #003366; border-bottom: 3px solid #003366; }}
        .metric {{ background: #f0f0f0; padding: 15px; margin: 10px 0; border-left: 4px solid #0066cc; }}
    </style>
</head>
<body>
    <h1>RELATÓRIO TÉCNICO - {uf.upper()}</h1>
    
    <div class="metric">
        <strong>Estado:</strong> {uf.upper()}<br>
        <strong>Total de Logs:</strong> {data['total_logs']:,}<br>
        <strong>Participação Nacional:</strong> {pct_nacional:.2f}%<br>
        <strong>Gerado em:</strong> {data['timestamp'].strftime('%d/%m/%Y %H:%M')}
    </div>
    
    <h2>Análise Comparativa</h2>
    <p>O estado de {uf.upper()} representa {pct_nacional:.2f}% do total de logs processados nacionalmente.</p>
    
    <div class="footer" style="margin-top: 50px; font-size: 0.9em; color: #666; border-top: 1px solid #ccc; padding-top: 20px;">
        <p><strong>Sistema:</strong> Brurna Analytics v1.0</p>
    </div>
</body>
</html>
"""
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
            
        print(f"✅ Relatório {uf.upper()} gerado: {output_path}")
        return output_path

if __name__ == "__main__":
    generator = ReportGenerator()
    
    # Gerar relatório nacional
    print("Gerando relatório nacional...")
    generator.generate_national_report_html()
    
    # Gerar relatórios por UF
    for uf in ['AC', 'AP', 'RR', 'TO', 'SE']:
        print(f"Gerando relatório {uf}...")
        generator.generate_uf_report_html(uf)
    
    print("\n✅ Todos os relatórios foram gerados com sucesso!")
