"""驗證 PROD 的 Q_Min tie-breaking 邏輯"""
import pandas as pd

# 讀取 step1
step1 = pd.read_csv('output/驗證20251231_Near_step1.csv', low_memory=False)

# 讀取 PROD
prod_df = pd.read_csv(r'資料來源\20251231\NearPROD_20251231.tsv', sep='\t', dtype=str)
prod_valid = prod_df[prod_df['strike'].notna() & (prod_df['strike'] != '')].copy()
prod_valid['time'] = prod_valid['time'].astype(int)
prod_valid['strike'] = prod_valid['strike'].astype(int)
for c in ['c.min_bid', 'c.min_ask', 'c.last_bid', 'c.last_ask']:
    prod_valid[c] = pd.to_numeric(prod_valid[c], errors='coerce')

# 看幾個案例
cases = [
    (85345, 31400),
    (85615, 31800),
    (90730, 31300),
]

for t, s in cases:
    print(f"\n=== time={t}, strike={s} ===")
    
    # step1 資料
    row = step1[(step1['Time'] == t) & (step1['Strike'] == s) & (step1['CP'] == 'Call')]
    if len(row) > 0:
        r = row.iloc[0]
        q_last_spread = r['Q_Last_Valid_Spread']
        q_min_spread = r['Q_Min_Valid_Spread']
        
        print(f"step1:")
        print(f"  Q_Last: bid={r['Q_Last_Valid_Bid']}, ask={r['Q_Last_Valid_Ask']}, spread={q_last_spread}")
        print(f"  Q_Min:  bid={r['Q_Min_Valid_Bid']}, ask={r['Q_Min_Valid_Ask']}, spread={q_min_spread}")
        print(f"  Spread 相同? {abs(float(q_last_spread) - float(q_min_spread)) < 0.01}")
    
    # PROD 資料
    prod_row = prod_valid[(prod_valid['time'] == t) & (prod_valid['strike'] == s)]
    if len(prod_row) > 0:
        p = prod_row.iloc[0]
        print(f"\nPROD:")
        print(f"  c.last: bid={p['c.last_bid']}, ask={p['c.last_ask']}")
        print(f"  c.min:  bid={p['c.min_bid']}, ask={p['c.min_ask']}")
        
        # 檢查 PROD 的 c.min 是否等於 c.last
        if abs(p['c.min_bid'] - p['c.last_bid']) < 0.01:
            print(f"  → PROD 的 c.min == c.last（選了 Q_Last）")
        else:
            print(f"  → PROD 的 c.min != c.last（選了其他 tick）")
