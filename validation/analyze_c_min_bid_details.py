"""分析 c.min_bid 差異的詳細資訊"""
import pandas as pd

# 讀取 step1
step1 = pd.read_csv('output/驗證20251231_Near_step1.csv', low_memory=False)
step1_call = step1[step1['CP'] == 'Call'].copy()

# 差異案例
cases = [
    (92630, 32400),
    (93045, 31400),
    (102045, 31600),
    (110215, 32000),
    (111945, 32000),
    (112415, 31900),
    (134500, 31400),
    (134500, 31600),
    (134500, 32100),
]

print("=== c.min_bid 差異詳細分析 ===\n")

for time, strike in cases:
    row = step1_call[(step1_call['Time'] == time) & (step1_call['Strike'] == strike)]
    if len(row) > 0:
        r = row.iloc[0]
        print(f"time={time}, strike={strike}")
        print(f"  Q_Last_Valid: bid={r['Q_Last_Valid_Bid']}, ask={r['Q_Last_Valid_Ask']}")
        print(f"  Q_Min_Valid:  bid={r['Q_Min_Valid_Bid']}, ask={r['Q_Min_Valid_Ask']}")
        
        # 計算 spread
        if not pd.isna(r['Q_Last_Valid_Bid']) and not pd.isna(r['Q_Min_Valid_Bid']):
            last_spread = r['Q_Last_Valid_Ask'] - r['Q_Last_Valid_Bid']
            min_spread = r['Q_Min_Valid_Ask'] - r['Q_Min_Valid_Bid']
            print(f"  Q_Last spread: {last_spread:.2f}, Q_Min spread: {min_spread:.2f}")
            print(f"  Spread 相同? {abs(last_spread - min_spread) < 1e-9}")
        print()
