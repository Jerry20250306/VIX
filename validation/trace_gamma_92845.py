"""
修復 trace 腳本，正確匹配 c.source 並分析 92845 案例
"""
import pandas as pd
import numpy as np

# 讀取結果
df = pd.read_csv('output/驗證20251231_NearPROD.csv', low_memory=False)

# 篩選物件
time = 92845
strike = 31800

target_rows = df[(df['strike'] == strike) & (df['time'] <= time)].sort_values('time')

print(f"=== 追蹤 {time}, {strike} (Call) ===\n")

if len(target_rows) >= 2:
    prev_row = target_rows.iloc[-2]
    curr_row = target_rows.iloc[-1]
    
    source = str(prev_row['c.source'])
    print(f"前一個點 (Time={int(prev_row['time'])}):")
    print(f"  Source: {source}")
    
    prev_q_hat_mid = np.nan
    if 'Last' in source:
        prev_q_hat_mid = (prev_row['c.last_bid'] + prev_row['c.last_ask']) / 2
        print(f"  使用 Q_Last_Bid/Ask: {prev_row['c.last_bid']} / {prev_row['c.last_ask']}")
    elif 'Min' in source:
        prev_q_hat_mid = (prev_row['c.min_bid'] + prev_row['c.min_ask']) / 2
        print(f"  使用 Q_Min_Bid/Ask: {prev_row['c.min_bid']} / {prev_row['c.min_ask']}")
    elif 'Replacement' in source:
        # 如果是沿用之前的 Q_hat，則需要遞迴找前面的 Q_hat_Mid
        # 但這裡暫時簡化
        print("  Source 為 Replacement (沿用更之前的值)")
        
    print(f"  Q_hat_Mid: {prev_q_hat_mid}")
    
    print(f"\n當前點 (Time={int(curr_row['time'])}):")
    # 注意：Gamma 是為每個候選 Q 獨立計算的。Q_Min 被選為來源，所以看它的 Gamma。
    c_min_mid = (curr_row['c.min_bid'] + curr_row['c.min_ask']) / 2
    print(f"  c.min_bid/ask: {curr_row['c.min_bid']} / {curr_row['c.min_ask']} (Mid={c_min_mid})")
    print(f"  c.gamma (我們): {curr_row['c.gamma']}")
    
    print(f"\n--- Gamma 判斷模擬 ---")
    if pd.isna(prev_q_hat_mid):
        print("Prev Q_hat_Mid 為 NaN -> Gamma = 2.0")
    elif c_min_mid <= prev_q_hat_mid:
        print(f"Mid ({c_min_mid}) <= PrevMid ({prev_q_hat_mid}) -> Gamma = 1.5")
    else:
        print(f"Mid ({c_min_mid}) > PrevMid ({prev_q_hat_mid}) -> Gamma = 2.0")
else:
    print("找不到足夠資料")
