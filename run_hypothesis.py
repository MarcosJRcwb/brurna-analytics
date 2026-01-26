"""
Unit Test Runner - Execução Individual de Hipóteses
Permite executar uma ou mais hipóteses específicas sem rodar todas as 500
"""
import sys
import os
import argparse
from pathlib import Path

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

# Import dos módulos de análise
from src.analytics.g1_temporal import run_g1_temporal
from src.analytics.g4_crosscheck import run_g4_crosscheck
from src.analytics.h501_hash_chain import run_h501

def run_single_hypothesis(h_id):
    """Executa uma única hipótese pelo ID"""
    h_num = int(h_id[1:])  # Remove 'H' e converte para int
    
    print(f"\n{'='*60}")
    print(f"Executando Hipótese {h_id}")
    print(f"{'='*60}\n")
    
    # Mapear hipótese para função
    if 1 <= h_num <= 125:
        # G1 - Temporal
        print("Grupo: G1 - Dinâmica Temporal")
        result = run_g1_temporal()
        # Filtrar resultado específico
        if isinstance(result, list):
            result = [r for r in result if r['ID'] == h_id]
            if result:
                return result[0]
    
    elif 126 <= h_num <= 250:
        # G2 - Hardware (implementar quando necessário)
        print("Grupo: G2 - Hardware/Operacional")
        return {'ID': h_id, 'Status': 'NOT_IMPLEMENTED', 'Observation': 'Grupo G2 não implementado ainda'}
    
    elif 251 <= h_num <= 375:
        # G3 - Forense (implementar quando necessário)
        print("Grupo: G3 - Forense/Segurança")
        return {'ID': h_id, 'Status': 'NOT_IMPLEMENTED', 'Observation': 'Grupo G3 não implementado ainda'}
    
    elif 376 <= h_num <= 500:
        # G4 - Cruzamento
        print("Grupo: G4 - Cruzamento de Dados")
        result = run_g4_crosscheck()
        if isinstance(result, list):
            result = [r for r in result if r['ID'] == h_id]
            if result:
                return result[0]
    
    elif h_num == 501:
        # H501 - Hash Chain
        print("Grupo: Fase 10 - Integridade Criptográfica")
        return run_h501()
    
    return {'ID': h_id, 'Status': 'NOT_FOUND', 'Observation': 'Hipótese não encontrada'}

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
