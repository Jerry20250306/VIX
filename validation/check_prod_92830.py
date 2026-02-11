"""
檢查 PROD 在 92830, 31800 (Call) 的狀態
"""
import pandas as pd

# 讀取 PROD
prod_df = pd.read_csv(r'資料來源\20251231\NearPROD_20251231.tsv', sep='\t', dtype=str)
row = prod_df[(prod_df['time'] == '92830') & (prod_df['strike'] == '31800')]

print("=== PROD 在 92830, 31800 (Call) ===")
if len(row) > 0:
    r = row.iloc[0]
    print(f"c.bid: {r['c.bid']}, c.ask: {r['c.ask']}, c.source: {r['c.source']}")
    print(f"c.gamma: {r['c.gamma']}")
else:
    print("PROD 沒有這一筆")
