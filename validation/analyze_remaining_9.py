"""分析剩餘 9 筆 c.min_bid 差異的 SeqNo"""
import pandas as pd

# 讀取資料
our_df = pd.read_csv('output/驗證20251231_NearPROD.csv')
prod_df = pd.read_csv(r'資料來源\20251231\NearPROD_20251231.tsv', sep='\t', dtype=str)

# PROD 資料處理
prod_valid = prod_df[prod_df['strike'].notna() & (prod_df['strike'] != '')].copy()
prod_valid['time'] = prod_valid['time'].astype(int)
prod_valid['strike'] = prod_valid['strike'].astype(int)
for c in ['c.min_bid', 'c.min_ask']:
    prod_valid[c] = pd.to_numeric(prod_valid[c], errors='coerce')

# 合併
merged = pd.merge(
    our_df[['time', 'strike', 'c.min_bid', 'c.min_ask']],
    prod_valid[['time', 'strike', 'c.min_bid', 'c.min_ask']],
    on=['time', 'strike'], suffixes=('_OUR', '_PROD')
)

# 找出差異
diff_mask = (merged['c.min_bid_OUR'].fillna(-999) - merged['c.min_bid_PROD'].fillna(-999)).abs() > 0.01
bad = merged[diff_mask].copy()

print(f"剩餘 {len(bad)} 筆 c.min_bid 差異\n")

# 讀取 step1 看原始資料
step1 = pd.read_csv('output/驗證20251231_Near_step1.csv', low_memory=False)

# 看前 3 個案例
for idx, r in bad.head(3).iterrows():
    t = int(r['time'])
    s = int(r['strike'])
    
    print(f"=== time={t}, strike={s} ===")
    print(f"PROD: bid={r['c.min_bid_PROD']:.1f}, ask={r['c.min_ask_PROD']:.1f}")
    print(f"我們: bid={r['c.min_bid_OUR']:.1f}, ask={r['c.min_ask_OUR']:.1f}")
    
    # 看 step1
    row = step1[(step1['Time'] == t) & (step1['Strike'] == s) & (step1['CP'] == 'Call')]
    if len(row) > 0:
        r1 = row.iloc[0]
        print(f"\nstep1:")
        print(f"  Q_Last: bid={r1['Q_Last_Valid_Bid']}, ask={r1['Q_Last_Valid_Ask']}, spread={r1['Q_Last_Valid_Spread']}")
        print(f"  Q_Min:  bid={r1['Q_Min_Valid_Bid']}, ask={r1['Q_Min_Valid_Ask']}, spread={r1['Q_Min_Valid_Spread']}")
        
        # 計算 spread
        q_last_spread = float(r1['Q_Last_Valid_Spread'])
        q_min_spread = float(r1['Q_Min_Valid_Spread'])
        
        print(f"\nSpread 比較:")
        print(f"  Q_Last spread: {q_last_spread:.2f}")
        print(f"  Q_Min spread:  {q_min_spread:.2f}")
        
        if abs(q_last_spread - q_min_spread) < 0.01:
            print(f"  → Spread 相同，應該選 Q_Last")
            print(f"  → 但我們選了 Q_Min ({r1['Q_Min_Valid_Bid']})")
            print(f"  → PROD 選了 {r['c.min_bid_PROD']:.1f}")
        else:
            print(f"  → Spread 不同 (Q_Last={q_last_spread:.2f} vs Q_Min={q_min_spread:.2f})")
            print(f"  → Q_Min 應該是 spread 最小的")
    print()
