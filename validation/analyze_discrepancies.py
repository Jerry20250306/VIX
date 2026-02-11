"""
深入分析 PROD 與我們計算結果的不一致原因
分析策略：
1. 找每個欄位的「首次差異時間點」
2. 分析 min_bid/ask 差異的具體原因
3. 追溯 EMA 滾雪球效應的起源
4. 分析 bid/ask 最終報價差異
"""
import pandas as pd
import numpy as np

# ============================================================
# 讀取資料
# ============================================================
print("=" * 70)
print("PROD vs 我們 — 深入差異分析")
print("=" * 70)

prod_df = pd.read_csv(r'資料來源\20251231\NearPROD_20251231.tsv', sep='\t', dtype=str)
our_df = pd.read_csv('output/驗證20251231_NearPROD.csv')

# 清理 PROD 資料
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

print(f"\n合併後: {len(merged)} 筆")
print(f"時間範圍: {merged['time'].min()} ~ {merged['time'].max()}")
print(f"不同時間點數: {merged['time'].nunique()}")

# ============================================================
# 1. 每個欄位的首次差異分析
# ============================================================
print("\n" + "=" * 70)
print("1. 每個欄位的首次差異時間點與 Strike")
print("=" * 70)

for col in NUM_COLS:
    our_c = col + '_OUR'
    prod_c = col + '_PROD'
    if our_c not in merged.columns or prod_c not in merged.columns:
        continue
    
    tol = 1e-4 if 'ema' in col else 0.01
    diff_mask = (merged[our_c].fillna(-999) - merged[prod_c].fillna(-999)).abs() > tol
    cnt = diff_mask.sum()
    
    if cnt == 0:
        print(f"\n[OK] {col}: 全部一致")
        continue
    
    diff_rows = merged[diff_mask].sort_values('time')
    first = diff_rows.iloc[0]
    
    # 分析差異的時間分佈
    diff_times = diff_rows['time'].unique()
    first_time = diff_times[0]
    
    print(f"\n[X] {col}: {cnt} 筆不一致 ({cnt/len(merged)*100:.2f}%)")
    print(f"    首次差異: time={int(first['time'])}, strike={int(first['strike'])}")
    print(f"    PROD={first[prod_c]}, 我們={first[our_c]}, 差={first[our_c] - first[prod_c]:.6f}")
    print(f"    涉及時間點: {len(diff_times)} 個 (共 {merged['time'].nunique()} 個)")
    print(f"    涉及 Strike: {diff_rows['strike'].nunique()} 個")
    
    # 顯示前 5 筆差異
    print(f"    前5筆差異:")
    for i, (_, r) in enumerate(diff_rows.head(5).iterrows()):
        print(f"      [{i+1}] time={int(r['time'])}, strike={int(r['strike'])}, "
              f"PROD={r[prod_c]:.4f}, 我們={r[our_c]:.4f}, 差={r[our_c]-r[prod_c]:.6f}")

# ============================================================
# 2. min_bid/ask 差異深入分析
# ============================================================
print("\n" + "=" * 70)
print("2. min_bid 差異深入分析")
print("=" * 70)

for prefix in ['c', 'p']:
    min_bid_our = f'{prefix}.min_bid_OUR'
    min_bid_prod = f'{prefix}.min_bid_PROD'
    min_ask_our = f'{prefix}.min_ask_OUR'
    min_ask_prod = f'{prefix}.min_ask_PROD'
    
    if min_bid_our not in merged.columns:
        continue
    
    diff_mask = (merged[min_bid_our].fillna(-999) - merged[min_bid_prod].fillna(-999)).abs() > 0.01
    diff_rows = merged[diff_mask].sort_values('time')
    
    if len(diff_rows) == 0:
        print(f"\n  {prefix}.min_bid: 全部一致")
        continue
    
    print(f"\n  {prefix}.min_bid: {len(diff_rows)} 筆不一致")
    
    # 分析差異模式：是 spread 選擇不同，還是同 spread 取了不同 tick
    for i, (_, r) in enumerate(diff_rows.head(10).iterrows()):
        our_spread = r[min_ask_our] - r[min_bid_our] if pd.notna(r[min_ask_our]) and pd.notna(r[min_bid_our]) else np.nan
        prod_spread = r[min_ask_prod] - r[min_bid_prod] if pd.notna(r[min_ask_prod]) and pd.notna(r[min_bid_prod]) else np.nan
        
        print(f"    [{i+1}] time={int(r['time'])}, strike={int(r['strike'])}")
        print(f"        PROD: bid={r[min_bid_prod]}, ask={r[min_ask_prod]}, spread={prod_spread:.2f}")
        print(f"        我們: bid={r[min_bid_our]}, ask={r[min_ask_our]}, spread={our_spread:.2f}")
        spread_diff = "不同 Spread" if abs(our_spread - prod_spread) > 0.01 else "同 Spread, 不同 tick"
        print(f"        → {spread_diff}")

# ============================================================
# 3. EMA 差異追溯（逐時間點比對特定 Strike）
# ============================================================
print("\n" + "=" * 70)
print("3. EMA 差異追溯（找 P 端首次差異的 Strike）")
print("=" * 70)

p_ema_diff = (merged['p.ema_OUR'].fillna(-999) - merged['p.ema_PROD'].fillna(-999)).abs() > 1e-4
p_ema_diff_rows = merged[p_ema_diff].sort_values('time')

if len(p_ema_diff_rows) > 0:
    first_diff = p_ema_diff_rows.iloc[0]
    target_strike = int(first_diff['strike'])
    first_diff_time = int(first_diff['time'])
    
    print(f"  首次 p.ema 差異: time={first_diff_time}, strike={target_strike}")
    print(f"  PROD={first_diff['p.ema_PROD']:.6f}, 我們={first_diff['p.ema_OUR']:.6f}")
    
    # 追溯該 strike 的所有時間點
    strike_data = merged[merged['strike'] == target_strike].sort_values('time')
    
    print(f"\n  追溯 strike={target_strike} 的 p.ema 歷程:")
    print(f"  {'time':>8} | {'PROD_ema':>12} | {'OUR_ema':>12} | {'差值':>12} | {'PROD_bid':>10} | {'OUR_bid':>10} | {'PROD_ask':>10} | {'OUR_ask':>10}")
    print(f"  {'-'*8} | {'-'*12} | {'-'*12} | {'-'*12} | {'-'*10} | {'-'*10} | {'-'*10} | {'-'*10}")
    
    found_first = False
    context_before = 3  # 差異前顯示幾行
    context_after = 5   # 差異後顯示幾行
    
    # 找到差異開始的位置
    for idx, (_, row) in enumerate(strike_data.iterrows()):
        ema_diff = abs(row['p.ema_OUR'] - row['p.ema_PROD']) if pd.notna(row['p.ema_OUR']) and pd.notna(row['p.ema_PROD']) else 0
        if ema_diff > 1e-4 and not found_first:
            # 顯示差異前的 context
            start_idx = max(0, idx - context_before)
            for j, (_, r) in enumerate(strike_data.iloc[start_idx:idx].iterrows()):
                d = r['p.ema_OUR'] - r['p.ema_PROD'] if pd.notna(r['p.ema_OUR']) and pd.notna(r['p.ema_PROD']) else 0
                print(f"  {int(r['time']):>8} | {r['p.ema_PROD']:>12.6f} | {r['p.ema_OUR']:>12.6f} | {d:>12.6f} | {r['p.bid_PROD']:>10} | {r['p.bid_OUR']:>10} | {r['p.ask_PROD']:>10} | {r['p.ask_OUR']:>10}")
            found_first = True
            after_count = 0
        
        if found_first and after_count < context_after:
            d = row['p.ema_OUR'] - row['p.ema_PROD'] if pd.notna(row['p.ema_OUR']) and pd.notna(row['p.ema_PROD']) else 0
            marker = " <<<" if abs(d) > 1e-4 else ""
            print(f"  {int(row['time']):>8} | {row['p.ema_PROD']:>12.6f} | {row['p.ema_OUR']:>12.6f} | {d:>12.6f} | {row['p.bid_PROD']:>10} | {row['p.bid_OUR']:>10} | {row['p.ask_PROD']:>10} | {row['p.ask_OUR']:>10}{marker}")
            after_count += 1
    
    # 看差異是否隨著時間增大（滾雪球效應）
    print(f"\n  差異隨時間變化:")
    time_groups = p_ema_diff_rows.groupby('time').size()
    print(f"    首個差異時間: {time_groups.index[0]}")
    print(f"    最後差異時間: {time_groups.index[-1]}")
    print(f"    差異筆數趨勢 (前10個時間點):")
    for t in time_groups.index[:10]:
        t_data = p_ema_diff_rows[p_ema_diff_rows['time'] == t]
        avg_diff = (t_data['p.ema_OUR'] - t_data['p.ema_PROD']).abs().mean()
        print(f"      time={t}: {len(t_data)} 個 strike, 平均差={avg_diff:.6f}")

# ============================================================
# 4. bid/ask 最終報價差異分析
# ============================================================
print("\n" + "=" * 70)
print("4. bid/ask 最終報價差異分析")
print("=" * 70)

for prefix in ['c', 'p']:
    bid_our = f'{prefix}.bid_OUR'
    bid_prod = f'{prefix}.bid_PROD'
    ask_our = f'{prefix}.ask_OUR'
    ask_prod = f'{prefix}.ask_PROD'
    
    diff_bid = (merged[bid_our].fillna(-999) - merged[bid_prod].fillna(-999)).abs() > 0.01
    diff_ask = (merged[ask_our].fillna(-999) - merged[ask_prod].fillna(-999)).abs() > 0.01
    
    # bid/ask 的差異是否跟 EMA 差異有關？
    ema_our = f'{prefix}.ema_OUR'
    ema_prod = f'{prefix}.ema_PROD'
    ema_diff = (merged[ema_our].fillna(-999) - merged[ema_prod].fillna(-999)).abs() > 1e-4
    
    bid_diff_rows = merged[diff_bid].sort_values('time')
    ask_diff_rows = merged[diff_ask].sort_values('time')
    
    print(f"\n  {prefix}.bid: {len(bid_diff_rows)} 筆不一致")
    print(f"  {prefix}.ask: {len(ask_diff_rows)} 筆不一致")
    
    if len(bid_diff_rows) > 0:
        # 看 bid 差異中有多少也有 EMA 差異
        bid_with_ema_diff = (diff_bid & ema_diff).sum()
        bid_without_ema_diff = (diff_bid & ~ema_diff).sum()
        print(f"    bid 差異中:")
        print(f"      同時有 EMA 差異: {bid_with_ema_diff} 筆")
        print(f"      EMA 一致但 bid 不同: {bid_without_ema_diff} 筆")
        
        # 前5筆
        print(f"    前5筆 bid 差異:")
        for i, (_, r) in enumerate(bid_diff_rows.head(5).iterrows()):
            ema_ok = "EMA一致" if abs(r[ema_our] - r[ema_prod]) < 1e-4 else f"EMA差={r[ema_our]-r[ema_prod]:.4f}"
            print(f"      [{i+1}] time={int(r['time'])}, strike={int(r['strike'])}, "
                  f"PROD={r[bid_prod]:.1f}, 我們={r[bid_our]:.1f}, {ema_ok}")

# ============================================================
# 5. 差異 Strike 的分佈統計
# ============================================================
print("\n" + "=" * 70)
print("5. 差異最集中的 Strike (前10)")
print("=" * 70)

all_diff = pd.Series(False, index=merged.index)
for col in NUM_COLS:
    our_c = col + '_OUR'
    prod_c = col + '_PROD'
    if our_c in merged.columns and prod_c in merged.columns:
        tol = 1e-4 if 'ema' in col else 0.01
        all_diff |= (merged[our_c].fillna(-999) - merged[prod_c].fillna(-999)).abs() > tol

strike_counts = merged[all_diff].groupby('strike').size().sort_values(ascending=False)
print(f"  有差異的 strike: {len(strike_counts)} / {merged['strike'].nunique()}")
for s, cnt in strike_counts.head(10).items():
    total = len(merged[merged['strike'] == s])
    print(f"    strike={s}: {cnt}/{total} ({cnt/total*100:.1f}%)")

print("\n" + "=" * 70)
print("分析完成")
print("=" * 70)
