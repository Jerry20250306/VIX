"""分析修復 EMA 重置後的剩餘差異"""
import pandas as pd
import numpy as np

prod_df = pd.read_csv(r'資料來源\20251231\NearPROD_20251231.tsv', sep='\t', dtype=str)
our_df = pd.read_csv('output/驗證20251231_NearPROD.csv')

prod_valid = prod_df[prod_df['strike'].notna() & (prod_df['strike'] != '')].copy()
prod_valid['time'] = prod_valid['time'].astype(int)
prod_valid['strike'] = prod_valid['strike'].astype(int)

NUM_COLS = [
    'c.ema', 'c.gamma', 'c.last_bid', 'c.last_ask', 'c.min_bid', 'c.min_ask', 'c.bid', 'c.ask',
    'p.ema', 'p.gamma', 'p.last_bid', 'p.last_ask', 'p.min_bid', 'p.min_ask', 'p.bid', 'p.ask',
]
for c in NUM_COLS:
    if c in prod_valid.columns:
        prod_valid[c] = pd.to_numeric(prod_valid[c], errors='coerce')

our_df['time'] = our_df['time'].astype(int)
our_df['strike'] = our_df['strike'].astype(int)

merged = pd.merge(
    our_df, prod_valid[['time', 'strike'] + NUM_COLS],
    on=['time', 'strike'], how='inner', suffixes=('_OUR', '_PROD')
)

print(f"合併: {len(merged)} 筆")

# =============================================
# 1. c.last_bid 差異分析
# =============================================
print("\n=== 1. c.last_bid 差異 ===")
diff = (merged['c.last_bid_OUR'].fillna(-999) - merged['c.last_bid_PROD'].fillna(-999)).abs() > 0.01
bad = merged[diff].sort_values('time')
print(f"共 {len(bad)} 筆")

our_nan = bad['c.last_bid_OUR'].isna()
prod_nan = bad['c.last_bid_PROD'].isna()
print(f"  我們=nan, PROD有值: {(our_nan & ~prod_nan).sum()}")
print(f"  PROD=nan, 我們有值: {(~our_nan & prod_nan).sum()}")
print(f"  兩邊都有值但不同: {(~our_nan & ~prod_nan).sum()}")

for _, r in bad.head(5).iterrows():
    t = int(r['time'])
    s = int(r['strike'])
    print(f"  time={t}, strike={s}, PROD={r['c.last_bid_PROD']}, 我們={r['c.last_bid_OUR']}")

# 看這些有問題的 strike 在所有時間有沒有 nan 的規律
bad_strikes = bad['strike'].unique()
print(f"\n  受影響的 strike: {bad_strikes}")
for s in bad_strikes[:3]:
    s_data = merged[merged['strike'] == s][['time', 'c.last_bid_OUR', 'c.last_bid_PROD']].sort_values('time')
    # 找第一次 nan 的
    nan_times = s_data[s_data['c.last_bid_OUR'].isna()]['time']
    ok_times = s_data[~s_data['c.last_bid_OUR'].isna()]['time']
    print(f"  strike={s}: 我們有值={len(ok_times)}, nan={len(nan_times)}, 首個nan time={nan_times.min() if len(nan_times)>0 else 'N/A'}")

# =============================================
# 2. c.gamma 差異分析 (175 筆)
# =============================================
print("\n=== 2. c.gamma 差異 ===")
diff_g = (merged['c.gamma_OUR'].fillna(-999) - merged['c.gamma_PROD'].fillna(-999)).abs() > 0.01
bad_g = merged[diff_g].sort_values('time')
print(f"共 {len(bad_g)} 筆")

# 差異分佈
print(f"  首次差異: time={int(bad_g.iloc[0]['time'])}")
print(f"  時間分佈:")
for t in bad_g['time'].unique()[:5]:
    cnt = (bad_g['time'] == t).sum()
    print(f"    time={t}: {cnt} 筆")

# gamma 值分佈
print(f"  gamma 差異模式:")
for _, r in bad_g.head(5).iterrows():
    print(f"    time={int(r['time'])}, strike={int(r['strike'])}, PROD={r['c.gamma_PROD']}, 我們={r['c.gamma_OUR']}")

# =============================================
# 3. c.bid 差異 (189 筆，比之前多)
# =============================================
print("\n=== 3. c.bid 差異 ===")
diff_b = (merged['c.bid_OUR'].fillna(-999) - merged['c.bid_PROD'].fillna(-999)).abs() > 0.01
bad_b = merged[diff_b].sort_values('time')
print(f"共 {len(bad_b)} 筆")

# 看差異中有多少同時有 gamma 差異
gamma_diff_too = (diff_b & diff_g).sum()
print(f"  同時有 gamma 差異: {gamma_diff_too}")
print(f"  純 bid 差異 (gamma 一致): {len(bad_b) - gamma_diff_too}")

# 前5筆
for _, r in bad_b.head(5).iterrows():
    print(f"  time={int(r['time'])}, strike={int(r['strike'])}, "
          f"PROD_bid={r['c.bid_PROD']}, 我們_bid={r['c.bid_OUR']}, "
          f"PROD_gamma={r['c.gamma_PROD']}, 我們_gamma={r['c.gamma_OUR']}")

# =============================================
# 4. p.gamma 差異 (79 筆)
# =============================================
print("\n=== 4. p.gamma 差異 ===")
diff_pg = (merged['p.gamma_OUR'].fillna(-999) - merged['p.gamma_PROD'].fillna(-999)).abs() > 0.01
bad_pg = merged[diff_pg].sort_values('time')
print(f"共 {len(bad_pg)} 筆")

# 首次差異在 85830，這在 EMA 重置之前
print(f"  首次差異: time={int(bad_pg.iloc[0]['time'])}")
pre_90000 = (bad_pg['time'] < 90000).sum()
post_90000 = (bad_pg['time'] >= 90000).sum()
print(f"  09:00前: {pre_90000}, 09:00後: {post_90000}")

for _, r in bad_pg.head(5).iterrows():
    print(f"  time={int(r['time'])}, strike={int(r['strike'])}, "
          f"PROD={r['p.gamma_PROD']}, 我們={r['p.gamma_OUR']}")
