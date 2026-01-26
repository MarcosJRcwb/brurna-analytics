
from src.parser.log_parser import TSELogParser
from config import config
import pandas as pd

def inspect_urna_voters():
    file = list((config.RAW_LOGS_DIR / 'rr').glob('*.logjez'))[0]
    print(f"🔍 Inspecionando urna: {file.name}")
    parser = TSELogParser(str(file))
    df = parser.parse_file()
    
    count_hab = len(df[df['mensagem'].str.contains('Eleitor foi habilitado', case=False, na=False)])
    count_comp = len(df[df['mensagem'].str.contains('O voto do eleitor foi computado', case=False, na=False)])
    count_fim = len(df[df['mensagem'].str.contains('Fim de votação', case=False, na=False)]) # Errado, é Fim da votação ou similar
    
    print(f"   - Eleitor foi habilitado: {count_hab}")
    print(f"   - O voto do eleitor foi computado: {count_comp}")
    
    # Busca por padrões de fim de processo por eleitor
    # Normalmente: "Votação encerrada para o eleitor" ou similar
    patterns = df[df['mensagem'].str.contains('votação|eleitor|confirmado', case=False, na=False)]['mensagem'].value_counts()
    print("\n📈 Frequência de padrões:")
    for m, c in patterns.head(10).items():
        print(f"   [{c:3}] {m}")

if __name__ == "__main__":
    inspect_urna_voters()
