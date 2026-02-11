"""
追查 EMA 在 time=90000 的行為差異
看 PROD 在 09:00 是否有 EMA 重置邏輯
"""
import pandas as pd
import numpy as np

# 讀取 PROD 原始資料
prod_df = pd.read_csv(r'資料來源\20251231\NearPROD_20251231.tsv', sep='\t', dtype=str)
prod_valid = prod_df[prod_df['strike'].notna() & (prod_df['strike'] != '')].copy()
prod_valid['time'] = prod_valid['time'].astype(int)
prod_valid['strike'] = prod_valid['strike'].astype(int)
prod_valid['c.ema'] = pd.to_numeric(prod_valid['c.ema'], errors='coerce')
prod_valid['p.ema'] = pd.to_numeric(prod_valid['p.ema'], errors='coerce')
prod_valid['c.last_bid'] = pd.to_numeric(prod_valid['c.last_bid'], errors='coerce')
prod_valid['p.last_bid'] = pd.to_numeric(prod_valid['p.last_bid'], errors='coerce')
prod_valid['c.min_bid'] = pd.to_numeric(prod_valid['c.min_bid'], errors='coerce')
prod_valid['p.min_bid'] = pd.to_numeric(prod_valid['p.min_bid'], errors='coerce')
prod_valid['c.min_ask'] = pd.to_numeric(prod_valid['c.min_ask'], errors='coerce')
prod_valid['p.min_ask'] = pd.to_numeric(prod_valid['p.min_ask'], errors='coerce')

# ============================================
# 1. 看 strike=22400 (Put) 在 09:00 前後的 EMA
# ============================================
print("=" * 70)
print("1. strike=22400 的 p.ema 在 09:00 前後 (PROD)")
print("=" * 70)

s22400 = prod_valid[prod_valid['strike'] == 22400].sort_values('time')
# 顯示 85900~90100 的值
mask = (s22400['time'] >= 85800) & (s22400['time'] <= 90200)
for _, r in s22400[mask].iterrows():
    min_bid = r.get('p.min_bid', 'N/A')
    min_ask = r.get('p.min_ask', 'N/A')
    min_spread = float(min_ask) - float(min_bid) if pd.notna(min_bid) and pd.notna(min_ask) else 'N/A'
    print(f"  time={int(r['time'])}, p.ema={r['p.ema']:.6f}, "
          f"p.min_bid={min_bid}, p.min_ask={min_ask}, min_spread={min_spread}")

# ============================================
# 2. 看多個 strike 在 time=90000 的 EMA 值
# ============================================
print("\n" + "=" * 70)
print("2. 多個 strike 在 time=90000 與 85945 的 p.ema 比較 (PROD)")
print("=" * 70)

t85945 = prod_valid[prod_valid['time'] == 85945].sort_values('strike')
t90000 = prod_valid[prod_valid['time'] == 90000].sort_values('strike')

merged_t = pd.merge(
    t85945[['strike', 'p.ema']].rename(columns={'p.ema': 'ema_85945'}),
    t90000[['strike', 'p.ema']].rename(columns={'p.ema': 'ema_90000'}),
    on='strike'
)

# 找出 90000 的 EMA 跟 85945 差異很大的
merged_t['diff'] = (merged_t['ema_90000'] - merged_t['ema_85945']).abs()
merged_t['ratio'] = merged_t['ema_90000'] / merged_t['ema_85945']

print(f"  85945 → 90000 的 EMA 變化:")
print(f"  平均比率: {merged_t['ratio'].mean():.4f}")
print(f"  比率 < 0.9 的: {(merged_t['ratio'] < 0.9).sum()} / {len(merged_t)}")
print(f"  比率 = ~0.95 (正常衰減): {((merged_t['ratio'] > 0.94) & (merged_t['ratio'] < 0.96)).sum()} / {len(merged_t)}")

# 顯示差異最大的前10個
print(f"\n  差異最大的前10 (按 ratio 排序):")
for _, r in merged_t.nsmallest(10, 'ratio').iterrows():
    print(f"    strike={int(r['strike'])}, ema_85945={r['ema_85945']:.4f}, "
          f"ema_90000={r['ema_90000']:.4f}, ratio={r['ratio']:.4f}")

# ============================================
# 3. 是不是 09:00 時 Q_Min 的 spread 很小導致 EMA 重算？
# ============================================
print("\n" + "=" * 70)
print("3. PROD 在 time=90000 的 p.min spread 分佈")
print("=" * 70)

t90000_full = prod_valid[prod_valid['time'] == 90000].copy()
t90000_full['p.min_spread'] = t90000_full['p.min_ask'].astype(float) - t90000_full['p.min_bid'].astype(float)
t90000_full['c.min_spread'] = t90000_full['c.min_ask'].astype(float) - t90000_full['c.min_bid'].astype(float)

print(f"  p.min_spread 分佈:")
print(t90000_full['p.min_spread'].describe())
print(f"\n  c.min_spread 分佈:")
print(t90000_full['c.min_spread'].describe())

# ============================================
# 4. 看 PROD 的 EMA 在 90000 的值跟 min_spread 在 90000 的值的關係
# ============================================
print("\n" + "=" * 70)
print("4. 在 time=90000，PROD p.ema 是否等於 p.min_spread？")
print("=" * 70)

check = t90000_full[['strike', 'p.ema', 'p.min_spread']].copy()
check['ema_eq_spread'] = (check['p.ema'] - check['p.min_spread']).abs() < 0.01
print(f"  p.ema == p.min_spread: {check['ema_eq_spread'].sum()} / {len(check)}")

# 也看看差異
check['ema_vs_spread'] = check['p.ema'] - check['p.min_spread']
print(f"\n  p.ema - p.min_spread 分佈:")
print(check['ema_vs_spread'].describe())

# ============================================
# 5. 看看 EMA 是否在 90000 被重置為 min_spread（首次重置假說）
# ============================================
print("\n" + "=" * 70)
print("5. 檢查：90000 的 EMA 是否為 0.95*ema_85945 + 0.05*min_spread_90000")
print("=" * 70)

t85945_data = prod_valid[prod_valid['time'] == 85945][['strike', 'p.ema']].rename(columns={'p.ema': 'ema_prev'})
check2 = pd.merge(check, t85945_data, on='strike')
check2['expected_normal'] = 0.95 * check2['ema_prev'] + 0.05 * check2['p.min_spread']
check2['expected_reset'] = check2['p.min_spread']

check2['match_normal'] = (check2['p.ema'] - check2['expected_normal']).abs() < 0.001
check2['match_reset'] = (check2['p.ema'] - check2['expected_reset']).abs() < 0.001

print(f"  符合正常 EMA 公式: {check2['match_normal'].sum()} / {len(check2)}")
print(f"  符合 EMA 重置為 min_spread: {check2['match_reset'].sum()} / {len(check2)}")

# 不符合任何一個的
neither = check2[~check2['match_normal'] & ~check2['match_reset']]
print(f"  兩者都不符合: {len(neither)} / {len(check2)}")
if len(neither) > 0:
    print(f"\n  例子:")
    for _, r in neither.head(5).iterrows():
        print(f"    strike={int(r['strike'])}, "
              f"PROD_ema={r['p.ema']:.6f}, expected_normal={r['expected_normal']:.6f}, "
              f"expected_reset={r['expected_reset']:.6f}, ema_prev={r['ema_prev']:.6f}, "
              f"min_spread={r['p.min_spread']:.4f}")

# ============================================
# 6. 看 C 端 (Call) 在 90000 有沒有一樣的問題
# ============================================
print("\n" + "=" * 70)
print("6. Call 端 EMA 在 90000 的行為")
print("=" * 70)

our_df = pd.read_csv('output/驗證20251231_NearPROD.csv')
our_df['time'] = our_df['time'].astype(int)
our_df['strike'] = our_df['strike'].astype(int)

merged_full = pd.merge(
    our_df, prod_valid[['time', 'strike', 'c.ema', 'p.ema']],
    on=['time', 'strike'], how='inner', suffixes=('_OUR', '_PROD')
)

# Call 端 90000
c_ema_at_90000 = merged_full[merged_full['time'] == 90000]
c_diff = (c_ema_at_90000['c.ema_OUR'] - c_ema_at_90000['c.ema_PROD']).abs()
p_diff = (c_ema_at_90000['p.ema_OUR'] - c_ema_at_90000['p.ema_PROD']).abs()

print(f"  time=90000 的 EMA 差異:")
print(f"    Call: max diff = {c_diff.max():.6f}, 不一致 = {(c_diff > 0.01).sum()}")
print(f"    Put:  max diff = {p_diff.max():.6f}, 不一致 = {(p_diff > 0.01).sum()}")
