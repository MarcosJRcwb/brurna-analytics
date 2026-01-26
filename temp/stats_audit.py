import pandas as pd
import sys

try:
    df = pd.read_csv("analysis_results.csv")
except Exception as e:
    print(f"Error reading CSV: {e}")
    sys.exit(1)

# Define Groups
groups = {
    "G1: Temporal (H001-H125)": (1, 125),
    "G2: Hardware (H126-H250)": (126, 250),
    "G3: Forense (H251-H375)": (251, 375),
    "G4: Cruzamento (H376-H500)": (376, 500)
}

print(f"{'Grupo':<30} | {'Total':<5} | {'Cob. (INFO/PASS/FAIL)':<20} | {'Pend. (PEND/SKIP/ERR)':<20} | {'% Cobertura'}")
print("-" * 100)

total_covered = 0
total_items = 0

for name, (start, end) in groups.items():
    # Filter by ID range
    # IDs are strings like "H001", so slice [1:] and convert to int
    mask = df['ID'].apply(lambda x: start <= int(x[1:]) <= end if pd.notnull(x) and x.startswith('H') and x[1:].isdigit() else False)
    subset = df[mask]
    
    count_total = len(subset)
    
    # Coverage: Status is INFO, PASS, FAIL (FAIL is a result, not a skip)
    covered_mask = subset['Status'].isin(['INFO', 'PASS', 'FAIL', 'FAIL (Anomaly)'])
    not_covered_mask = subset['Status'].isin(['PENDING', 'SKIPPED', 'ERROR', 'SKIP'])
    
    count_covered = covered_mask.sum()
    count_pending =  count_total - count_covered # Safer than sum of specific statuses
    
    pct = (count_covered / count_total * 100) if count_total > 0 else 0
    
    print(f"{name:<30} | {count_total:<5} | {count_covered:<20} | {count_pending:<20} | {pct:.1f}%")
    
    total_covered += count_covered
    total_items += count_total

print("-" * 100)
total_pct = (total_covered / total_items * 100) if total_items > 0 else 0
print(f"{'TOTAL':<30} | {total_items:<5} | {total_covered:<20} | {total_items - total_covered:<20} | {total_pct:.1f}%")
