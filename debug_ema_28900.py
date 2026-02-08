"""
分析 Strike=28900, Call 在 084530 的 EMA 差異來源
比較 PROD 的 EMA 計算與我們的計算
"""
import pandas as pd
pd.set_option('display.width', 400)
pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', 50)

# 載入 PROD 資料 (標準答案)
print("=" * 80)
print("載入 PROD 資料...")
print("=" * 80)

prod = pd.read_csv(r'c:\AGY\VIX\VIX\資料來源\20251231\NearPROD_20251231.tsv', sep='\t', dtype=str)

# 篩選 Strike=28900, Call (c.開頭的欄位)
prod_28900 = prod[(prod['strike'] == '28900') & (prod['strike'].notna())].copy()
prod_28900['time_int'] = prod_28900['time'].astype(int)
prod_28900 = prod_28900.sort_values('time_int')

# 找出 084530 之前（含）的時間點
target_time = 84530
prod_before = prod_28900[prod_28900['time_int'] <= target_time]

print(f"\n084530 之前（含）的時間點數量: {len(prod_before)}")
print(f"時間範圍: {prod_before['time'].iloc[0]} → {prod_before['time'].iloc[-1]}")

# 顯示 PROD 的 EMA 相關欄位演進
print("\n" + "=" * 80)
print("PROD 中 Strike=28900, Call 的 EMA 演進")
print("=" * 80)

cols_to_show = ['time', 'c.min_bid', 'c.min_ask', 'c.ema', 'c.gamma', 'c.bid', 'c.ask', 'c.last_outlier', 'c.min_outlier']
print(prod_before[cols_to_show].head(10).to_string(index=False))

# 手動計算前面幾個時間點的 Spread
print("\n" + "=" * 80)
print("手動計算 Spread 並追蹤 EMA")
print("=" * 80)

print("\n【PROD EMA 公式回顧】")
print("  EMA_t = 0.05 × EMA_t-1 + 0.95 × Q_Min_Valid_Spread_t")
print("  ALPHA = 0.95\n")

prev_ema = None
for i, row in prod_before.head(10).iterrows():
    time_str = row['time']
    min_bid = row['c.min_bid']
    min_ask = row['c.min_ask']
    prod_ema = row['c.ema']
    
    # 計算 spread
    if pd.notna(min_bid) and pd.notna(min_ask) and min_bid != '' and min_ask != '':
        try:
            spread = float(min_ask) - float(min_bid)
        except:
            spread = None
    else:
        spread = None
    
    # 手動計算 EMA
    if prev_ema is None:
        calc_ema = spread if spread is not None else None
        calc_process = f"初始值: EMA = Spread = {spread}"
    elif prev_ema is not None and spread is not None:
        calc_ema = 0.05 * prev_ema + 0.95 * spread
        calc_process = f"正常: 0.05×{prev_ema:.4f} + 0.95×{spread:.1f} = {calc_ema:.4f}"
    elif prev_ema is not None and spread is None:
        calc_ema = prev_ema
        calc_process = f"維持: EMA = EMA_t-1 = {prev_ema:.4f}"
    else:
        calc_ema = None
        calc_process = "無資料"
    
    print(f"Time={time_str}: min_bid={min_bid:>5}, min_ask={min_ask:>5}, Spread={spread!s:>6}, PROD_EMA={prod_ema:>10}, 計算EMA={str(calc_ema if calc_ema else 'N/A'):>10}")
    print(f"  {calc_process}")
    
    if calc_ema is not None:
        prev_ema = calc_ema

# 現在載入我們的計算結果查看
print("\n" + "=" * 80)
print("我們的計算結果 (step0_full_output_Near_前10個.csv)")
print("=" * 80)

calc = pd.read_csv('step0_full_output_Near_前10個.csv')
calc_28900 = calc[(calc['Strike'] == 28900) & (calc['CP'] == 'Call')]
calc_28900 = calc_28900.sort_values('Time')

cols_calc = ['Time', 'Q_Min_Valid_Bid', 'Q_Min_Valid_Ask', 'Q_Min_Valid_Spread', 'EMA', 'Q_Last_Valid_Gamma', 'Q_Min_Valid_Gamma']
print(calc_28900[cols_calc].head(10).to_string(index=False))

# 關鍵比較
print("\n" + "=" * 80)
print("關鍵比較: 084530 時間點")
print("=" * 80)

prod_084530 = prod_28900[prod_28900['time'] == '084530'].iloc[0]
calc_084530 = calc_28900[calc_28900['Time'] == 84530].iloc[0]

print(f"\n【PROD 084530】")
print(f"  c.min_bid={prod_084530['c.min_bid']}, c.min_ask={prod_084530['c.min_ask']}")
print(f"  c.ema = {prod_084530['c.ema']}")
print(f"  c.gamma = {prod_084530['c.gamma']}")
print(f"  c.last_outlier = {prod_084530['c.last_outlier']}")

print(f"\n【我們的計算 084530】")
print(f"  Q_Min_Valid_Bid={calc_084530['Q_Min_Valid_Bid']}, Q_Min_Valid_Ask={calc_084530['Q_Min_Valid_Ask']}")
print(f"  EMA = {calc_084530['EMA']}")
print(f"  Q_Min_Valid_Gamma = {calc_084530['Q_Min_Valid_Gamma']}")
print(f"  Q_Min_Valid_Is_Outlier = {calc_084530['Q_Min_Valid_Is_Outlier']}")

# 比較 Spread
prod_spread = float(prod_084530['c.min_ask']) - float(prod_084530['c.min_bid'])
calc_spread = calc_084530['Q_Min_Valid_Spread']
print(f"\n【Spread 比較】")
print(f"  PROD Spread = {float(prod_084530['c.min_ask'])} - {float(prod_084530['c.min_bid'])} = {prod_spread}")
print(f"  我們 Spread = {calc_spread}")
