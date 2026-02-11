"""
追蹤 Next Term 09:01:15, Strike 32500, Put 的 Q_Min 選擇過程
"""
import pandas as pd
import numpy as np

# 讀取 step1 (Next Term)
step1 = pd.read_csv('output/驗證20251231_Next_step1.csv', low_memory=False)

time = 90115
strike = 32500
cp = 'Put'

# 列出前後時間點
target = step1[(step1['Strike'] == strike) & (step1['CP'] == cp)].copy()
target = target.sort_values('Time')

# 顯示 09:00:45 ~ 09:01:30 的資料
mask = (target['Time'] >= 90045) & (target['Time'] <= 90130)
rows = target[mask]

print(f"=== Next Term, Strike={strike}, CP={cp} ===\n")
for _, row in rows.iterrows():
    t = int(row['Time'])
    print(f"Time: {t}")
    print(f"  Q_Last: Bid={row.get('Q_last_Bid', 'N/A')}, Ask={row.get('Q_last_Ask', 'N/A')}")
    print(f"  Q_Last Valid: {row.get('Q_last_Valid', 'N/A')}")
    print(f"  Q_Last_Valid Bid/Ask: {row.get('Q_Last_Valid_Bid', 'N/A')} / {row.get('Q_Last_Valid_Ask', 'N/A')}")
    print(f"  Q_Min: Bid={row.get('Q_min_Bid', 'N/A')}, Ask={row.get('Q_min_Ask', 'N/A')}")
    print(f"  Q_Min Valid: {row.get('Q_min_Valid', 'N/A')}")
    print(f"  Q_Min_Valid Bid/Ask: {row.get('Q_Min_Valid_Bid', 'N/A')} / {row.get('Q_Min_Valid_Ask', 'N/A')}")
    print(f"  Q_Min Spread: {row.get('Q_min_Spread', 'N/A')}")
    print(f"  Q_Min SysID: {row.get('Q_min_SysID', 'N/A')}")
    print("-" * 40)
