"""
深入查 seqno=4102077 為何沒被 Q_Min 選中
可能原因：valid_mask 判定無效、或程式碼邏輯問題
"""
import pandas as pd
import numpy as np

# 讀取原始 tick 資料（全部商品）
raw = pd.read_csv(
    r'資料來源\J002-11300041_20251231\temp\J002-11300041_20251231_TXOA6.csv',
    sep='\t', dtype=str
)

# 找 seqno=4102077 的完整資料
raw['seqno'] = pd.to_numeric(raw['svel_i081_seqno'], errors='coerce')
target_tick = raw[raw['seqno'] == 4102077]

print("=== seqno=4102077 的完整原始資料 ===\n")
if len(target_tick) > 0:
    t = target_tick.iloc[0]
    for col in t.index:
        print(f"  {col}: {t[col]}")

# 檢查有效報價判斷的每個條件
print("\n=== 有效報價判斷 ===\n")
if len(target_tick) > 0:
    t = target_tick.iloc[0]
    bid = float(t['svel_i081_best_buy_price1']) if pd.notna(t.get('svel_i081_best_buy_price1')) else np.nan
    ask = float(t['svel_i081_best_sell_price1']) if pd.notna(t.get('svel_i081_best_sell_price1')) else np.nan
    
    print(f"bid = {bid}")
    print(f"ask = {ask}")
    print(f"bid >= 0: {bid >= 0}")
    print(f"ask > 0: {ask > 0}")
    print(f"ask > bid: {ask > bid}")
    print(f"有效? {bid >= 0 and ask > 0 and ask > bid}")

# 也檢查 reconstruct_order_book.py 中的 valid_mask 建構方式
# 讀取 step1 檢查該 tick 的狀態
step1 = pd.read_csv('output/驗證20251231_Near_step1.csv', low_memory=False)

# 找 time=93045, strike=31400, Call
row_93045 = step1[(step1['Time'] == 93045) & (step1['Strike'] == 31400) & (step1['CP'] == 'Call')]

if len(row_93045) > 0:
    r = row_93045.iloc[0]
    print("\n=== step1 的 time=93045, strike=31400, Call ===\n")
    # 印出所有欄位
    for col in r.index:
        print(f"  {col}: {r[col]}")

# 對比：也看看程式碼中 valid_mask 是怎麼建構的
print("\n\n=== 檢查 seqno=4102077 在「該商品(TXO31400A6)」的陣列中的位置 ===\n")

# 篩選 TXO31400A6
target_prod = raw[raw['svel_i081_prod_id'].str.contains('TXO31400A6', na=False)].copy()
target_prod['bid'] = pd.to_numeric(target_prod['svel_i081_best_buy_price1'], errors='coerce')
target_prod['ask'] = pd.to_numeric(target_prod['svel_i081_best_sell_price1'], errors='coerce')
target_prod['spread'] = target_prod['ask'] - target_prod['bid']
target_prod = target_prod.sort_values('seqno').reset_index(drop=True)

# 找 seqno=4102077 的位置
idx = target_prod[target_prod['seqno'] == 4102077].index
if len(idx) > 0:
    i = idx[0]
    print(f"在 TXO31400A6 陣列中的位置: index={i}")
    print(f"bid={target_prod.loc[i, 'bid']:.1f}, ask={target_prod.loc[i, 'ask']:.1f}, spread={target_prod.loc[i, 'spread']:.1f}")
    
    # 顯示前後幾筆
    start = max(0, i - 2)
    end = min(len(target_prod), i + 3)
    print(f"\n前後幾筆：")
    for j in range(start, end):
        marker = " <<<" if j == i else ""
        print(f"  [{j}] seqno={target_prod.loc[j, 'seqno']}, bid={target_prod.loc[j, 'bid']:.1f}, ask={target_prod.loc[j, 'ask']:.1f}, spread={target_prod.loc[j, 'spread']:.1f}{marker}")

# 重要：檢查 reconstruct_order_book.py 中的 new_ticks_by_product
# 理論上，區間 [4087963, 4140093) 中屬於 TXO31400A6 的 ticks 應該包含 seqno=4102077
print(f"\n=== 確認 seqno=4102077 是否在區間 [4087963, 4140093) 中 ===")
print(f"4087963 <= 4102077 < 4140093: {4087963 <= 4102077 < 4140093}")
