"""
Detector de anomalias críticas em logs eleitorais.
Busca CPFs, valida mesários, detecta encoding anômalo.
"""

import re
import pandas as pd
from pathlib import Path
from typing import List, Dict, Set
import chardet
from collections import Counter


class CriticalAnomalyDetector:
    """Detecta anomalias críticas que podem indicar problemas de segurança ou LGPD"""
    
    # Padrões regex
    CPF_PATTERN = re.compile(r'\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b')
    TITULO_PATTERN = re.compile(r'\b\d{12}\b')
    MESARIO_PATTERN = re.compile(r'\[(\d{12,13})\]')  # CPF entre colchetes
    
    def __init__(self):
        self.cpfs_found = []
        self.titulos_found = []
        self.mesarios = {}
        self.encoding_stats = Counter()
    
    def validate_cpf(self, cpf: str) -> bool:
        """
        Valida dígitos verificadores de CPF.
        
        Args:
            cpf: String com 11 dígitos
            
        Returns:
            True se CPF é válido
        """
        # Remove formatação
        cpf = re.sub(r'[^\d]', '', cpf)
        
        if len(cpf) != 11 or cpf == cpf[0] * 11:
            return False
        
        # Calcula primeiro dígito
        soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
        digito1 = (soma * 10 % 11) % 10
        
        # Calcula segundo dígito
        soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
        digito2 = (soma * 10 % 11) % 10
        
        return cpf[-2:] == f"{digito1}{digito2}"
    
    def detect_cpf_in_text(self, text: str, file_path: str = None) -> List[Dict]:
        """
        Busca CPFs em texto.
        
        Args:
            text: Texto para buscar
            file_path: Caminho do arquivo (para logging)
            
        Returns:
            Lista de CPFs encontrados com contexto
        """
        matches = []
        
        for match in self.CPF_PATTERN.finditer(text):
            cpf = match.group()
            cpf_clean = re.sub(r'[^\d]', '', cpf)
            
            if self.validate_cpf(cpf_clean):
                # Extrai contexto (50 chars antes e depois)
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                context = text[start:end]
                
                matches.append({
                    'cpf': cpf,
                    'file': file_path,
                    'context': context,
                    'position': match.start()
                })
        
        return matches
    
    def extract_mesarios(self, text: str, file_path: str = None) -> List[str]:
        """
        Extrai números de mesários (padrão [XXXXXXXXXXX]).
        
        Args:
            text: Texto para buscar
            file_path: Caminho do arquivo
            
        Returns:
            Lista de números de mesários
        """
        mesarios = []
        
        for match in self.MESARIO_PATTERN.finditer(text):
            numero = match.group(1)
            
            # Tenta validar como CPF (primeiros 11 dígitos)
            if len(numero) >= 11:
                cpf_candidate = numero[:11]
                is_valid_cpf = self.validate_cpf(cpf_candidate)
                
                mesarios.append({
                    'numero': numero,
                    'cpf_candidate': cpf_candidate,
                    'is_valid_cpf': is_valid_cpf,
                    'file': file_path
                })
        
        return mesarios
    
    def detect_encoding(self, file_path: Path) -> Dict:
        """
        Detecta encoding de um arquivo.
        
        Args:
            file_path: Caminho do arquivo
            
        Returns:
            Dict com encoding e confiança
        """
        with open(file_path, 'rb') as f:
            raw_data = f.read(10000)  # Lê primeiros 10KB
        
        result = chardet.detect(raw_data)
        
        self.encoding_stats[result['encoding']] += 1
        
        return {
            'file': file_path,
            'encoding': result['encoding'],
            'confidence': result['confidence']
        }
    
    def analyze_file(self, file_path: Path) -> Dict:
        """
        Analisa um arquivo completo para anomalias.
        
        Args:
            file_path: Caminho do arquivo
            
        Returns:
            Dict com todas as anomalias encontradas
        """
        # Detecta encoding
        encoding_info = self.detect_encoding(file_path)
        
        # Lê arquivo
        try:
            with open(file_path, 'r', encoding=encoding_info['encoding']) as f:
                content = f.read()
        except:
            # Fallback para latin-1
            with open(file_path, 'r', encoding='latin-1') as f:
                content = f.read()
        
        # Busca anomalias
        cpfs = self.detect_cpf_in_text(content, str(file_path))
        mesarios = self.extract_mesarios(content, str(file_path))
        
        return {
            'file': str(file_path),
            'encoding': encoding_info,
            'cpfs_found': cpfs,
            'mesarios': mesarios,
            'has_critical_anomaly': len(cpfs) > 0
        }
    
    def analyze_directory(self, directory: Path, pattern: str = '*.logjez') -> Dict:
        """
        Analisa todos os arquivos em um diretório.
        
        Args:
            directory: Diretório para analisar
            pattern: Padrão de arquivos
            
        Returns:
            Dict com resumo de anomalias
        """
        from tqdm import tqdm
        
        files = list(directory.glob(pattern))
        
        print(f"🔍 Analisando {len(files)} arquivos em {directory}")
        
        all_cpfs = []
        all_mesarios = []
        anomalous_files = []
        
        for file in tqdm(files, desc="Detectando anomalias"):
            result = self.analyze_file(file)
            
            if result['cpfs_found']:
                all_cpfs.extend(result['cpfs_found'])
                anomalous_files.append(result['file'])
            
            all_mesarios.extend(result['mesarios'])
        
        # Analisa mesários duplicados
        mesario_counts = Counter(m['cpf_candidate'] for m in all_mesarios if m['is_valid_cpf'])
        duplicated_mesarios = {cpf: count for cpf, count in mesario_counts.items() if count > 1}
        
        return {
            'total_files': len(files),
            'cpfs_found': all_cpfs,
            'total_cpfs': len(all_cpfs),
            'anomalous_files': anomalous_files,
            'mesarios': all_mesarios,
            'duplicated_mesarios': duplicated_mesarios,
            'encoding_stats': dict(self.encoding_stats)
        }
    
    def generate_report(self, results: Dict) -> str:
        """
        Gera relatório de anomalias críticas.
        
        Args:
            results: Resultados da análise
            
        Returns:
            String com relatório formatado
        """
        report = []
        report.append("=" * 80)
        report.append("RELATÓRIO DE ANOMALIAS CRÍTICAS")
        report.append("=" * 80)
        
        # CPFs encontrados
        report.append(f"\n🚨 CPFs DE ELEITORES ENCONTRADOS: {results['total_cpfs']}")
        
        if results['total_cpfs'] > 0:
            report.append("\n⚠️  VIOLAÇÃO DE LGPD DETECTADA!")
            report.append("\nArquivos com CPFs:")
            for file in set(results['anomalous_files']):
                report.append(f"  - {file}")
            
            report.append("\nPrimeiros 5 CPFs encontrados:")
            for i, cpf_info in enumerate(results['cpfs_found'][:5], 1):
                report.append(f"\n{i}. CPF: {cpf_info['cpf']}")
                report.append(f"   Arquivo: {cpf_info['file']}")
                report.append(f"   Contexto: ...{cpf_info['context']}...")
        else:
            report.append("  ✅ Nenhum CPF de eleitor encontrado")
        
        # Mesários
        report.append(f"\n\n👥 MESÁRIOS IDENTIFICADOS: {len(results['mesarios'])}")
        report.append(f"   CPFs válidos: {sum(1 for m in results['mesarios'] if m['is_valid_cpf'])}")
        
        # Mesários duplicados
        if results['duplicated_mesarios']:
            report.append(f"\n⚠️  MESÁRIOS EM MÚLTIPLAS SEÇÕES: {len(results['duplicated_mesarios'])}")
            report.append("\nTop 10 mesários mais frequentes:")
            for cpf, count in sorted(results['duplicated_mesarios'].items(), key=lambda x: x[1], reverse=True)[:10]:
                report.append(f"  CPF {cpf}: {count} seções")
        else:
            report.append("  ✅ Nenhum mesário duplicado detectado")
        
        # Encoding
        report.append(f"\n\n🔤 ENCODING DOS ARQUIVOS:")
        for encoding, count in results['encoding_stats'].items():
            percentage = (count / results['total_files']) * 100
            report.append(f"  {encoding}: {count} arquivos ({percentage:.1f}%)")
        
        # Alerta se houver encoding Windows
        windows_encodings = ['cp1252', 'windows-1252', 'iso-8859-1']
        for enc in windows_encodings:
            if enc in results['encoding_stats']:
                report.append(f"\n⚠️  ATENÇÃO: {results['encoding_stats'][enc]} arquivos com encoding Windows detectado!")
                report.append("   Arquivos gerados em Linux não deveriam ter este encoding.")
        
        report.append("\n" + "=" * 80)
        
        return "\n".join(report)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Detecção de anomalias críticas")
    parser.add_argument("--dir", required=True, help="Diretório para analisar")
    parser.add_argument("--output", default="anomalias_criticas.txt", help="Arquivo de saída")
    
    args = parser.parse_args()
    
    detector = CriticalAnomalyDetector()
    results = detector.analyze_directory(Path(args.dir))
    report = detector.generate_report(results)
    
    print(report)
    
    with open(args.output, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n✅ Relatório salvo em: {args.output}")
