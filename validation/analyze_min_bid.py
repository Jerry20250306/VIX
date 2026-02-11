"""分析 c.min_bid 的 45 筆差異"""
import pandas as pd
import numpy as np

# 讀取資料
our_df = pd.read_csv('output/驗證20251231_NearPROD.csv')
prod_df = pd.read_csv(r'資料來源\20251231\NearPROD_20251231.tsv', sep='\t', dtype=str)

# PROD 資料處理
prod_valid = prod_df[prod_df['strike'].notna() & (prod_df['strike'] != '')].copy()
prod_valid['time'] = prod_valid['time'].astype(int)
prod_valid['strike'] = prod_valid['strike'].astype(int)
for c in ['c.min_bid', 'c.min_ask', 'c.bid', 'c.ask']:
    prod_valid[c] = pd.to_numeric(prod_valid[c], errors='coerce')

# 合併
our_df['time'] = our_df['time'].astype(int)
our_df['strike'] = our_df['strike'].astype(int)

merged = pd.merge(
    our_df[['time', 'strike', 'c.min_bid', 'c.min_ask']],
    prod_valid[['time', 'strike', 'c.min_bid', 'c.min_ask']],
    on=['time', 'strike'], suffixes=('_OUR', '_PROD')
)

# 找出 c.min_bid 差異
diff_mask = (merged['c.min_bid_OUR'].fillna(-999) - merged['c.min_bid_PROD'].fillna(-999)).abs() > 0.01
bad = merged[diff_mask].copy()

print(f"=== c.min_bid 差異分析 ===")
print(f"共 {len(bad)} 筆\n")

# 計算 spread
bad['spread_OUR'] = bad['c.min_ask_OUR'] - bad['c.min_bid_OUR']
bad['spread_PROD'] = bad['c.min_ask_PROD'] - bad['c.min_bid_PROD']
bad['spread_diff'] = (bad['spread_OUR'] - bad['spread_PROD']).abs()

# 分類
same_spread = bad['spread_diff'] < 0.01
diff_spread = ~same_spread

print(f"1. Spread 相同但 bid/ask 不同（tie-breaking）: {same_spread.sum()} 筆")
print(f"2. Spread 不同: {diff_spread.sum()} 筆\n")

# 看 spread 相同的案例
if same_spread.sum() > 0:
    print("=== Spread 相同的案例（前 10 筆）===")
    same_cases = bad[same_spread].copy()
    same_cases['bid_diff'] = same_cases['c.min_bid_OUR'] - same_cases['c.min_bid_PROD']
    same_cases['ask_diff'] = same_cases['c.min_ask_OUR'] - same_cases['c.min_ask_PROD']
    
    for _, r in same_cases.head(10).iterrows():
        print(f"\ntime={int(r['time'])}, strike={int(r['strike'])}")
        print(f"  PROD: bid={r['c.min_bid_PROD']:.1f}, ask={r['c.min_ask_PROD']:.1f}, spread={r['spread_PROD']:.1f}")
        print(f"  我們: bid={r['c.min_bid_OUR']:.1f}, ask={r['c.min_ask_OUR']:.1f}, spread={r['spread_OUR']:.1f}")
        print(f"  差異: bid差={r['bid_diff']:.1f}, ask差={r['ask_diff']:.1f}")

# 看 spread 不同的案例
if diff_spread.sum() > 0:
    print("\n\n=== Spread 不同的案例（前 5 筆）===")
    diff_cases = bad[diff_spread].copy()
    
    for _, r in diff_cases.head(5).iterrows():
        print(f"\ntime={int(r['time'])}, strike={int(r['strike'])}")
        print(f"  PROD: bid={r['c.min_bid_PROD']:.1f}, ask={r['c.min_ask_PROD']:.1f}, spread={r['spread_PROD']:.1f}")
        print(f"  我們: bid={r['c.min_bid_OUR']:.1f}, ask={r['c.min_ask_OUR']:.1f}, spread={r['spread_OUR']:.1f}")
        print(f"  spread 差異: {r['spread_diff']:.1f}")

# 時間分佈
print("\n\n=== 時間分佈 ===")
time_dist = bad.groupby('time').size().sort_values(ascending=False)
print(f"受影響的時間點數: {len(time_dist)}")
print("前 10 個時間點:")
for t, cnt in time_dist.head(10).items():
    print(f"  time={t}: {cnt} 筆")

# Strike 分佈
print("\n=== Strike 分佈 ===")
strike_dist = bad.groupby('strike').size().sort_values(ascending=False)
print(f"受影響的 strike 數: {len(strike_dist)}")
print("前 10 個 strike:")
for s, cnt in strike_dist.head(10).items():
    print(f"  strike={s}: {cnt} 筆")

# 讀取 step1 看原始 Q_Min 資料
print("\n\n=== 檢查 step1 原始資料（第一個案例）===")
if len(bad) > 0:
    first = bad.iloc[0]
    t = int(first['time'])
    s = int(first['strike'])
    
    step1 = pd.read_csv('output/驗證20251231_Near_step1.csv', low_memory=False)
    row = step1[(step1['Time'] == t) & (step1['Strike'] == s) & (step1['CP'] == 'Call')]
    
    if len(row) > 0:
        r = row.iloc[0]
        print(f"time={t}, strike={s}, CP=Call")
        print(f"  Q_Min_Valid_Bid: {r['Q_Min_Valid_Bid']}")
        print(f"  Q_Min_Valid_Ask: {r['Q_Min_Valid_Ask']}")
        print(f"  Q_Min_Valid_Spread: {r['Q_Min_Valid_Spread']}")
        print(f"  Q_Last_Valid_Bid: {r['Q_Last_Valid_Bid']}")
        print(f"  Q_Last_Valid_Ask: {r['Q_Last_Valid_Ask']}")
        print(f"  Q_Last_Valid_Spread: {r['Q_Last_Valid_Spread']}")
