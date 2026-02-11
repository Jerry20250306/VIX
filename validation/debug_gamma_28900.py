"""
深入分析 PROD 的 Gamma 邏輯
"""
import pandas as pd
pd.set_option('display.width', 400)
pd.set_option('display.max_columns', None)

# 載入資料
prod = pd.read_csv(r'../資料來源/20251231/NearPROD_20251231.tsv', sep='\t', dtype=str)
prod_28900 = prod[(prod['strike'] == '28900')].copy()
prod_28900['time_int'] = prod_28900['time'].astype(int)
prod_28900 = prod_28900.sort_values('time_int')

print("=" * 80)
print("PROD Gamma 邏輯深入分析")
print("=" * 80)

# 建立分析資料
data = []
prev_c_mid = None

for i, (_, row) in enumerate(prod_28900.head(15).iterrows()):
    time = row['time']
    gamma = float(row['c.gamma']) if pd.notna(row['c.gamma']) else None
    
    # c.bid/c.ask = Q_hat (最終篩選後報價)
    c_bid = float(row['c.bid']) if pd.notna(row['c.bid']) and row['c.bid'] != '' else None
    c_ask = float(row['c.ask']) if pd.notna(row['c.ask']) and row['c.ask'] != '' else None
    c_mid = (c_bid + c_ask) / 2 if c_bid and c_ask else None
    
    # c.last_bid/c.last_ask = Q_Last_Valid
    c_last_bid = float(row['c.last_bid']) if pd.notna(row['c.last_bid']) and row['c.last_bid'] != '' else None
    c_last_ask = float(row['c.last_ask']) if pd.notna(row['c.last_ask']) and row['c.last_ask'] != '' else None
    c_last_mid = (c_last_bid + c_last_ask) / 2 if c_last_bid and c_last_ask else None
    
    # 判斷條件
    if prev_c_mid is not None and c_last_mid is not None:
        mid_change = c_last_mid - prev_c_mid
        mid_direction = "上漲" if mid_change > 0 else ("持平" if mid_change == 0 else "下跌")
    else:
        mid_change = None
        mid_direction = "N/A"
    
    data.append({
        'time': time,
        'gamma': gamma,
        'c_mid_prev': prev_c_mid,
        'c_last_mid': c_last_mid,
        'mid_change': mid_change,
        'direction': mid_direction
    })
    
    # 更新 prev_c_mid 為當前的 c.mid (Q_hat_mid)
    prev_c_mid = c_mid

# 列印分析結果
print("\n時間 | gamma | Q_hat_Mid(t-1) | Q_Last_Mid(t) | 變化 | 方向")
print("-" * 70)
for d in data:
    prev = f"{d['c_mid_prev']:.1f}" if d['c_mid_prev'] else "N/A"
    curr = f"{d['c_last_mid']:.1f}" if d['c_last_mid'] else "N/A"
    change = f"{d['mid_change']:+.1f}" if d['mid_change'] is not None else "N/A"
    print(f"{d['time']} | {d['gamma']} | {prev:>14} | {curr:>13} | {change:>6} | {d['direction']}")

print("\n" + "=" * 80)
print("規律分析")
print("=" * 80)

print("""
觀察:
- gamma=2 出現在: 第一筆 (084515), 以及中價上漲時 (084715, 084730, 084745, 084800)
- gamma=1.5 出現在: 中價下跌或持平時

推測 PROD 的 Gamma 邏輯:
- gamma = 1.5: 當 c.last_mid <= Q_hat_Mid(t-1) (中價下跌或持平)
- gamma = 2.0: 當 c.last_mid > Q_hat_Mid(t-1) (中價上漲) 或第一筆

這與我們的不同:
- 我們: gamma1=2.0 (下跌), gamma2=2.5 (上漲), gamma0=1.2 (Bid=0)
- PROD: gamma=1.5 (下跌), gamma=2.0 (上漲)
""")

# 驗證這個假設
print("\n" + "=" * 80)
print("驗證假設: gamma=1.5 下跌, gamma=2 上漲")
print("=" * 80)

correct = 0
total = 0
for d in data[1:]:  # 跳過第一筆
    if d['mid_change'] is not None and d['gamma'] is not None:
        total += 1
        expected_gamma = 2.0 if d['mid_change'] > 0 else 1.5
        if d['gamma'] == expected_gamma:
            correct += 1
            status = "OK"
        else:
            status = "MISMATCH"
        print(f"{d['time']}: 變化={d['mid_change']:+.1f}, 預期gamma={expected_gamma}, 實際gamma={d['gamma']} - {status}")

print(f"\n正確率: {correct}/{total} = {correct/total*100:.1f}%")
