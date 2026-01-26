import sys
import os
import argparse
from pathlib import Path
import subprocess

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

def run_single_hypothesis(h_id):
    """Executa uma única hipótese pelo ID usando subprocess"""
    h_num = int(h_id[1:])  # Remove 'H' e converte para int
    
    print(f"\n{'='*60}")
    print(f"Executando Hipótese {h_id}")
    print(f"{'='*60}\n")
    
    # Executar H501 diretamente
    if h_num == 501:
        print("Grupo: Fase 10 - Integridade Criptográfica")
        result = subprocess.run(
            [sys.executable, "src/analytics/h501_hash_chain.py"],
            capture_output=True,
            text=True
        )
        print(result.stdout)
        return {
            'ID': h_id,
            'Status': 'PASS' if result.returncode == 0 else 'FAIL',
            'Description': 'Validação de hash chain',
            'Observation': 'Executado via subprocess'
        }
    
    # Para outras hipóteses, executar o motor analítico completo e filtrar
    print(f"Executando motor analítico para {h_id}...")
    print("(Nota: Executa todas as hipóteses e filtra o resultado)")
    
    result = subprocess.run(
        [sys.executable, "src/analytics/analytical_engine.py"],
        capture_output=True,
        text=True
    )
    
    # Ler resultado do CSV
    try:
        import pandas as pd
        df = pd.read_csv("analysis_results.csv")
        row = df[df['ID'] == h_id]
        if not row.empty:
            return row.iloc[0].to_dict()
    except:
        pass
    
    return {'ID': h_id, 'Status': 'ERROR', 'Observation': 'Erro ao executar hipótese'}

def run_multiple_hypotheses(h_ids):
    """Executa múltiplas hipóteses"""
    results = []
    
    for h_id in h_ids:
        result = run_single_hypothesis(h_id)
        results.append(result)
        
        # Salvar resultado individual
        save_individual_report(result)
    
    return results

def save_individual_report(result):
    """Salva relatório individual da hipótese"""
    output_dir = Path("reports/por_hipotese")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    filename = output_dir / f"{result['ID']}_resultado.txt"
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"Hipótese: {result['ID']}\n")
        f.write(f"Descrição: {result.get('Description', 'N/A')}\n")
        f.write(f"Status: {result['Status']}\n")
        f.write(f"Observação: {result.get('Observation', 'N/A')}\n")
    
    print(f"  💾 Relatório salvo: {filename}")

def main():
    parser = argparse.ArgumentParser(description='Executar hipóteses específicas')
    parser.add_argument('hypotheses', nargs='+', help='IDs das hipóteses (ex: H001 H464 H501)')
    parser.add_argument('--save', action='store_true', help='Salvar relatórios individuais')
    
    args = parser.parse_args()
    
    print(f"\n🚀 Executando {len(args.hypotheses)} hipótese(s)...\n")
    
    results = run_multiple_hypotheses(args.hypotheses)
    
    # Resumo
    print(f"\n{'='*60}")
    print("RESUMO DA EXECUÇÃO")
    print(f"{'='*60}\n")
    
    for result in results:
        status_icon = "✅" if result['Status'] == "PASS" else "⚠️" if "FAIL" in result['Status'] else "ℹ️"
        print(f"{status_icon} {result['ID']}: {result['Status']}")
    
    print(f"\n📁 Relatórios salvos em: reports/por_hipotese/")

if __name__ == "__main__":
    # Exemplos de uso:
    # python run_hypothesis.py H001
    # python run_hypothesis.py H001 H464 H501
    # python run_hypothesis.py H001 --save
    
    main()
