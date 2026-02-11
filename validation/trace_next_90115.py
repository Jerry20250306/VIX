"""
追蹤 Next Term 90115, 32500 (Put) 的 p.min_ask 差異
"""
import pandas as pd
import numpy as np

# 讀取 step1 (Next Term)
# 注意：之前跑的是 verify_next_term.py 沒產生 step1 csv? 
# step0_valid_quotes.py 會產生 step1 csv
# 檔名: output/驗證20251231_Next_step1.csv

step1_file = 'output/驗證20251231_Next_step1.csv'
step1 = pd.read_csv(step1_file, low_memory=False)

time = 90115
strike = 32500
cp = 'Put'

target_rows = step1[(step1['Strike'] == strike) & (step1['CP'] == cp) & (step1['Time'] <= time)].sort_values('Time').tail(5)

print(f"=== 追蹤 Next Term {time}, {strike} ({cp}) ===\n")
for i, row in target_rows.iterrows():
    print(f"Time: {int(row['Time'])}")
    print(f"  Q_Min: {row['Q_Min_Valid_Bid']} / {row['Q_Min_Valid_Ask']} (Spread={row['Q_Min_Valid_Spread']})")
    print(f"  Q_Last: {row['Q_Last_Valid_Bid']} / {row['Q_Last_Valid_Ask']}")
    print("-" * 20)

print("\n比較 PROD:")
print("PROD p.min_ask = 3640.0")
print("OUR  p.min_ask = 3650.0")

# 檢查原始 ticks (如果有保存的話，但現在沒有直接保存 raw ticks for debugging this specific case)
# 可以推測：min_ask 3640 vs 3650
# 3650 - 3640 = 10.
# 可能是選到了不同的 tick.
