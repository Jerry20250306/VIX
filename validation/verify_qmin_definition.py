"""驗證 Q_Min 的定義：是「spread 最小」還是「spread 最小且最新」"""
import pandas as pd

# 讀取 step1
step1 = pd.read_csv('output/驗證20251231_Near_step1.csv', low_memory=False)

# 找一個 Q_Last 價差不是最小的案例
# 先找 Q_Last_Spread != Q_Min_Spread 的案例
step1['Q_Last_Spread_f'] = pd.to_numeric(step1['Q_Last_Valid_Spread'], errors='coerce')
step1['Q_Min_Spread_f'] = pd.to_numeric(step1['Q_Min_Valid_Spread'], errors='coerce')

diff = step1[
    (step1['Q_Last_Spread_f'].notna()) & 
    (step1['Q_Min_Spread_f'].notna()) &
    ((step1['Q_Last_Spread_f'] - step1['Q_Min_Spread_f']).abs() > 0.01)
].copy()

print(f"=== Q_Last 價差不是最小的案例數：{len(diff)} ===\n")

if len(diff) > 0:
    # 看前 3 個案例
    for idx, r in diff.head(3).iterrows():
        print(f"time={int(r['Time'])}, strike={int(r['Strike'])}, CP={r['CP']}")
        print(f"  Q_Last: bid={r['Q_Last_Valid_Bid']}, ask={r['Q_Last_Valid_Ask']}, spread={r['Q_Last_Spread_f']:.2f}")
        print(f"  Q_Min:  bid={r['Q_Min_Valid_Bid']}, ask={r['Q_Min_Valid_Ask']}, spread={r['Q_Min_Spread_f']:.2f}")
        print(f"  Q_Min SeqNo: {r['Q_Min_Valid_SeqNo']}")
        print(f"  Q_Last SeqNo: {r['Q_Last_Valid_SeqNo']}")
        
        # 比較 SeqNo
        min_seq = pd.to_numeric(r['Q_Min_Valid_SeqNo'], errors='coerce')
        last_seq = pd.to_numeric(r['Q_Last_Valid_SeqNo'], errors='coerce')
        
        if pd.notna(min_seq) and pd.notna(last_seq):
            if min_seq > last_seq:
                print(f"  → Q_Min 的 SeqNo ({min_seq}) > Q_Last ({last_seq})，Q_Min 更新")
            elif min_seq < last_seq:
                print(f"  → Q_Min 的 SeqNo ({min_seq}) < Q_Last ({last_seq})，Q_Last 更新")
            else:
                print(f"  → Q_Min 和 Q_Last 的 SeqNo 相同")
        print()

# 讀取 PROD 驗證
print("\n=== 驗證 PROD 的 Q_Min 是否總是最新 ===")
prod_df = pd.read_csv(r'資料來源\20251231\NearPROD_20251231.tsv', sep='\t', dtype=str)
prod_valid = prod_df[prod_df['strike'].notna() & (prod_df['strike'] != '')].copy()
prod_valid['time'] = prod_valid['time'].astype(int)
prod_valid['strike'] = prod_valid['strike'].astype(int)

# 看第一個案例在 PROD 的情況
if len(diff) > 0:
    first = diff.iloc[0]
    t = int(first['Time'])
    s = int(first['Strike'])
    cp_map = {'Call': 'c', 'Put': 'p'}
    cp_prefix = cp_map[first['CP']]
    
    prod_row = prod_valid[(prod_valid['time'] == t) & (prod_valid['strike'] == s)]
    if len(prod_row) > 0:
        p = prod_row.iloc[0]
        print(f"\ntime={t}, strike={s}, CP={first['CP']}")
        print(f"PROD:")
        print(f"  {cp_prefix}.last: bid={p[f'{cp_prefix}.last_bid']}, ask={p[f'{cp_prefix}.last_ask']}")
        print(f"  {cp_prefix}.min:  bid={p[f'{cp_prefix}.min_bid']}, ask={p[f'{cp_prefix}.min_ask']}")
        
        # 比較 PROD 的 min 和我們的 Q_Min
        our_min_bid = first['Q_Min_Valid_Bid']
        prod_min_bid = p[f'{cp_prefix}.min_bid']
        
        print(f"\n我們的 Q_Min: {our_min_bid}")
        print(f"PROD 的 min: {prod_min_bid}")
        
        if str(our_min_bid) == str(prod_min_bid):
            print("→ 一致！")
        else:
            print("→ 不一致")
