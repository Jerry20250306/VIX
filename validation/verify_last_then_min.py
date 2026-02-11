"""
驗證假設：PROD 是否「先用 last，如果異常再用 min」
"""
import pandas as pd
pd.set_option('display.width', 400)
pd.set_option('display.max_columns', None)

# 載入 PROD
prod = pd.read_csv(r'../資料來源/20251231/NearPROD_20251231.tsv', sep='\t', dtype=str)

print("=" * 80)
print("驗證假設：先用 last 判斷，如果異常再用 min")
print("=" * 80)

# 看 Strike=28900 的資料
prod_28900 = prod[prod['strike'] == '28900'].sort_values('time').head(15)

print("\nStrike=28900 Call 的 outlier 標記和最終報價:")
print()

for _, row in prod_28900.iterrows():
    time = row['time']
    
    # 異常值標記
    last_outlier = row['c.last_outlier']
    min_outlier = row['c.min_outlier']
    
    # last 和 min 的報價
    last_bid = row['c.last_bid']
    last_ask = row['c.last_ask']
    min_bid = row['c.min_bid']
    min_ask = row['c.min_ask']
    
    # 最終報價 (c.bid, c.ask)
    final_bid = row['c.bid']
    final_ask = row['c.ask']
    
    # 判斷最終報價來源
    if final_bid == last_bid and final_ask == last_ask:
        source = "來自 Last"
    elif final_bid == min_bid and final_ask == min_ask:
        source = "來自 Min"
    else:
        source = "來自 Replacement"
    
    # 是否為異常值
    last_is_outlier = (last_outlier == 'V')
    min_is_outlier = (min_outlier == 'V')
    
    gamma = row['c.gamma']
    
    print(f"Time={time}:")
    print(f"  c.last_outlier={last_outlier:>3}, c.min_outlier={min_outlier:>3}, c.gamma={gamma}")
    print(f"  last=({last_bid}, {last_ask}), min=({min_bid}, {min_ask})")
    print(f"  final=({final_bid}, {final_ask}) → {source}")
    print()

print("=" * 80)
print("分析")
print("=" * 80)
print("""
觀察 PROD 的邏輯：

1. 如果 c.last_outlier = 數字 (非 V)：
   - Q_Last 不是異常值
   - 最終報價 = Q_Last
   - 不需要看 Q_Min

2. 如果 c.last_outlier = V：
   - Q_Last 是異常值
   - 需要檢查 Q_Min
   - 如果 c.min_outlier = V：最終報價 = Replacement（前值）
   - 如果 c.min_outlier = 數字：最終報價 = Q_Min

3. c.gamma 可能是：
   - 用於判斷 Q_Last 的 gamma
   - 或者是「最終採用的報價」對應的 gamma
""")

# 統計
print("\n" + "=" * 80)
print("統計：最終報價來源 vs 異常值標記")
print("=" * 80)

# 對所有 PROD 資料做統計
prod_with_strike = prod[prod['strike'].notna()].copy()

# 計數
count_last_ok = 0
count_last_outlier_min_ok = 0
count_both_outlier = 0
count_other = 0

for _, row in prod_with_strike.iterrows():
    last_outlier = row['c.last_outlier']
    min_outlier = row['c.min_outlier']
    
    final_bid = row['c.bid']
    final_ask = row['c.ask']
    last_bid = row['c.last_bid']
    last_ask = row['c.last_ask']
    min_bid = row['c.min_bid']
    min_ask = row['c.min_ask']
    
    last_is_outlier = (last_outlier == 'V')
    min_is_outlier = (min_outlier == 'V')
    
    from_last = (final_bid == last_bid and final_ask == last_ask)
    from_min = (final_bid == min_bid and final_ask == min_ask)
    
    if not last_is_outlier and from_last:
        count_last_ok += 1
    elif last_is_outlier and not min_is_outlier and from_min:
        count_last_outlier_min_ok += 1
    elif last_is_outlier and min_is_outlier:
        count_both_outlier += 1
    else:
        count_other += 1

print(f"\n情況 1: Last 不是異常值，使用 Last: {count_last_ok} 筆")
print(f"情況 2: Last 是異常值，Min 不是異常值，使用 Min: {count_last_outlier_min_ok} 筆")
print(f"情況 3: Last 和 Min 都是異常值（使用 Replacement）: {count_both_outlier} 筆")
print(f"其他情況: {count_other} 筆")
