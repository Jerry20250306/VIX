"""列出所有 c.min_bid 差異案例"""
import pandas as pd
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from step0_2_ema_calculation import calculate_ema_and_output

# 執行 step0_2
print(">>> 執行 EMA 計算...")
calculate_ema_and_output('Near', '20251231')

# 讀取結果
result_df = pd.read_csv('output/驗證20251231_NearPROD.csv', low_memory=False)

# 找出 c.min_bid 差異
result_df['c_min_bid_diff'] = abs(result_df['c.min_bid'] - result_df['c.min_bid_prod'])
diff_rows = result_df[result_df['c_min_bid_diff'] > 1e-6].copy()

print(f"\n=== c.min_bid 差異：共 {len(diff_rows)} 筆 ===\n")

for idx, row in diff_rows.iterrows():
    print(f"time={row['time']}, strike={row['strike']}")
    print(f"  PROD: bid={row['c.min_bid_prod']:.1f}, ask={row['c.min_ask_prod']:.1f}")
    print(f"  我們: bid={row['c.min_bid']:.1f}, ask={row['c.min_ask']:.1f}")
    print(f"  差異: {row['c_min_bid_diff']:.1f}")
    print()
