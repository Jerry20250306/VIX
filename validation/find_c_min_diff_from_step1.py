"""找出 c.min_bid 的差異案例（使用 step1）"""
import pandas as pd
import numpy as np

# 讀取 step1
step1 = pd.read_csv('output/驗證20251231_Near_step1.csv', low_memory=False)

# 讀取 PROD
prod_df = pd.read_csv(r'資料來源\20251231\NearPROD_20251231.tsv', sep='\t', dtype=str)
prod_valid = prod_df[prod_df['strike'].notna() & (prod_df['strike'] != '')].copy()
prod_valid['time'] = prod_valid['time'].astype(int)
prod_valid['strike'] = prod_valid['strike'].astype(int)

# 轉換數值欄位
for col in ['c.min_bid', 'c.min_ask', 'c.bid', 'c.ask', 'c.last_bid', 'c.last_ask']:
    prod_valid[col] = pd.to_numeric(prod_valid[col], errors='coerce')

# 從 step1 計算 c.min (使用 Replacement 邏輯)
step1_call = step1[step1['CP'] == 'Call'].copy()

# 計算 c.min_bid/ask
def get_c_min(row):
    if row['Replacement'] == 'Q_Min_Valid':
        return row['Q_Min_Valid_Bid'], row['Q_Min_Valid_Ask']
    elif row['Replacement'] == 'Q_Last_Valid':
        return row['Q_Last_Valid_Bid'], row['Q_Last_Valid_Ask']
    else:  # Replacement
        return row['Q_Last_Bid'], row['Q_Last_Ask']

step1_call[['c_min_bid', 'c_min_ask']] = step1_call.apply(
    lambda row: pd.Series(get_c_min(row)), axis=1
)

# 合併
merged = step1_call.merge(
    prod_valid[['time', 'strike', 'c.min_bid', 'c.min_ask', 'c.bid', 'c.ask']],
    left_on=['Time', 'Strike'],
    right_on=['time', 'strike'],
    how='inner',
    suffixes=('', '_prod')
)

# 找 c.min_bid 差異
merged['c_min_bid_diff'] = abs(merged['c_min_bid'] - merged['c.min_bid_prod'])
diff_rows = merged[merged['c_min_bid_diff'] > 1e-6].copy()

print(f"=== c.min_bid 差異分析 ===")
print(f"總共 {len(diff_rows)} 筆\n")

# 分類差異類型
print("=== 差異類型分類 ===\n")

# 檢查是否是 spread 相同的 tie-breaking 問題
tie_breaking_cases = []
other_cases = []

for idx, row in diff_rows.iterrows():
    # 檢查 Q_Last 和 Q_Min 的 spread
    if not pd.isna(row['Q_Last_Valid_Bid']) and not pd.isna(row['Q_Min_Valid_Bid']):
        last_spread = row['Q_Last_Valid_Ask'] - row['Q_Last_Valid_Bid']
        min_spread = row['Q_Min_Valid_Ask'] - row['Q_Min_Valid_Bid']
        
        if abs(last_spread - min_spread) < 1e-9:
            tie_breaking_cases.append(row)
        else:
            other_cases.append(row)
    else:
        other_cases.append(row)

print(f"1. Spread 相同（tie-breaking）: {len(tie_breaking_cases)} 筆")
print(f"2. 其他原因: {len(other_cases)} 筆\n")

# 顯示所有差異的詳細資訊
print("=== 所有差異詳細資訊 ===\n")
for idx, row in diff_rows.iterrows():
    print(f"time={row['Time']}, strike={row['Strike']}")
    print(f"  Replacement: {row['Replacement']}")
    print(f"  Q_Last_Valid: bid={row['Q_Last_Valid_Bid']}, ask={row['Q_Last_Valid_Ask']}")
    print(f"  Q_Min_Valid:  bid={row['Q_Min_Valid_Bid']}, ask={row['Q_Min_Valid_Ask']}")
    
    if not pd.isna(row['Q_Last_Valid_Bid']) and not pd.isna(row['Q_Min_Valid_Bid']):
        last_spread = row['Q_Last_Valid_Ask'] - row['Q_Last_Valid_Bid']
        min_spread = row['Q_Min_Valid_Ask'] - row['Q_Min_Valid_Bid']
        print(f"  Q_Last spread: {last_spread:.2f}, Q_Min spread: {min_spread:.2f}")
        print(f"  Spread 相同? {abs(last_spread - min_spread) < 1e-9}")
    
    print(f"  PROD c.min: bid={row['c.min_bid_prod']:.1f}, ask={row['c.min_ask_prod']:.1f}")
    print(f"  我們 c.min: bid={row['c_min_bid']:.1f}, ask={row['c_min_ask']:.1f}")
    print(f"  差異: bid差={row['c_min_bid_diff']:.1f}")
    print()
