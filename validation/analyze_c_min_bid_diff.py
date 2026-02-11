"""分析 c.min_bid 的差異"""
import pandas as pd
import numpy as np

# 讀取 step2
step2 = pd.read_csv('output/驗證20251231_Near_step2.csv', low_memory=False)

# 讀取 PROD
prod_df = pd.read_csv(r'資料來源\20251231\NearPROD_20251231.tsv', sep='\t', dtype=str)
prod_valid = prod_df[prod_df['strike'].notna() & (prod_df['strike'] != '')].copy()
prod_valid['time'] = prod_valid['time'].astype(int)
prod_valid['strike'] = prod_valid['strike'].astype(int)

# 轉換數值欄位
for col in ['c.min_bid', 'c.min_ask']:
    prod_valid[col] = pd.to_numeric(prod_valid[col], errors='coerce')

# 合併
merged = step2.merge(
    prod_valid[['time', 'strike', 'c.min_bid', 'c.min_ask']],
    left_on=['Time', 'Strike'],
    right_on=['time', 'strike'],
    how='inner',
    suffixes=('', '_prod')
)

# 找差異
merged['c_min_bid_diff'] = abs(merged['c.min_bid'] - merged['c.min_bid_prod'])
diff_rows = merged[merged['c_min_bid_diff'] > 1e-6].copy()

print(f"=== c.min_bid 差異分析 ===")
print(f"總共 {len(diff_rows)} 筆\n")

# 顯示所有差異
for idx, row in diff_rows.iterrows():
    print(f"time={row['Time']}, strike={row['Strike']}")
    print(f"  PROD: bid={row['c.min_bid_prod']:.1f}, ask={row['c.min_ask_prod']:.1f}")
    print(f"  我們: bid={row['c.min_bid']:.1f}, ask={row['c.min_ask']:.1f}")
    print(f"  差異: bid差={row['c_min_bid_diff']:.1f}")
    print()

# 讀取 step1 來看詳細資訊
step1 = pd.read_csv('output/驗證20251231_Near_step1.csv', low_memory=False)

print("=== 查看 step1 的 Q_Min 資訊 ===\n")
for idx, row in diff_rows.head(3).iterrows():
    time = row['Time']
    strike = row['Strike']
    
    step1_row = step1[(step1['Time'] == time) & (step1['Strike'] == strike) & (step1['CP'] == 'Call')]
    if len(step1_row) > 0:
        r = step1_row.iloc[0]
        print(f"time={time}, strike={strike}")
        print(f"  Q_Last: bid={r['Q_Last_Valid_Bid']}, ask={r['Q_Last_Valid_Ask']}")
        print(f"  Q_Min:  bid={r['Q_Min_Valid_Bid']}, ask={r['Q_Min_Valid_Ask']}")
        print(f"  PROD c.min: bid={row['c.min_bid_prod']:.1f}, ask={row['c.min_ask_prod']:.1f}")
        print(f"  我們 c.min: bid={row['c.min_bid']:.1f}, ask={row['c.min_ask']:.1f}")
        print()
