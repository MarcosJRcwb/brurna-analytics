from src.parser.log_parser import TSELogParser
import pandas as pd

# Caminho de um arquivo logd.dat de exemplo (substitua pelo seu real)
log_file = r"C:\Users\marco\Downloads\TSE\data\raw_logs\ac\temp_inspect\logd.dat"  # Ex.: r"C:\Users\marco\Downloads\TSE\data\raw_logs\ac\logd.dat"

parser = TSELogParser(log_file)
df = parser.parse_file(uf='AC', turno=1)  # Salva no banco
print(df.head())
