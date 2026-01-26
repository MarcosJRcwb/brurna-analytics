from src.parser.log_parser import TSELogParser
import pandas as pd

log_file = r'C:\Users\marco\Downloads\TSE\data\raw_logs\ac\o00407-0106600040077.logjez'
print(f'Testando arquivo: {log_file}')

parser = TSELogParser(log_file)
df = parser.parse_file(uf='AC', turno=1)

print(f'\nShape do DataFrame: {df.shape}')
print(f'Colunas: {df.columns.tolist()}')
print(f'\nPrimeiras 5 linhas:')
print(df.head())

print(f'\nContagem de severidades:')
print(df['severidade'].value_counts())

print(f'\nLinhas com timestamp válido: {df.timestamp.notna().sum()}')
print(f'Linhas com data válida: {df.data.notna().sum()}')
print(f'Linhas com hora válida: {df.hora.notna().sum()}')

if df.timestamp.notna().any():
    print(f'\nExemplo de linha com timestamp válido:')
    valid_row = df[df.timestamp.notna()].iloc[0]
    print(f'  Linha: {valid_row.linha_numero}')
    print(f'  Timestamp: {valid_row.timestamp}')
    print(f'  Severidade: {valid_row.severidade}')
    print(f'  Aplicativo: {valid_row.aplicativo}')
    print(f'  Mensagem: {valid_row.mensagem[:50]}...')
else:
    print('\nNenhum timestamp válido encontrado.')
    
    print('\nPrimeiras linhas brutas:')
    for i in range(min(3, len(df))):
        raw = df.iloc[i].raw_line
        if isinstance(raw, str):
            print(f'{i+1}: {raw[:100]}...')
        else:
            print(f'{i+1}: [NÃO É STRING]...')
