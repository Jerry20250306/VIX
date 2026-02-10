"""
診斷 time=92845 的 21 個 strike 缺失問題
"""
import pandas as pd
import numpy as np

# 讀取 step1 的原始輸出（在 EMA 之前）
step1 = pd.read_csv('output/驗證20251231_Near_step1.csv', low_memory=False)
print(f"step1 總筆數: {len(step1)}")
print(f"時間點數: {step1['Time'].nunique()}")
print(f"每個時間點的 strike 數:")
time_counts = step1.groupby('Time').size()
print(time_counts.describe())

# 哪些時間點的 strike 數不是 218？
abnormal = time_counts[time_counts != time_counts.mode()[0]]
print(f"\n非標準 strike 數的時間點:")
for t, cnt in abnormal.items():
    print(f"  time={t}: {cnt} 個 strike (標準={time_counts.mode()[0]})")

# 看 92845 有多少 strike
t92845 = step1[step1['Time'] == 92845]
print(f"\ntime=92845: {len(t92845)} 個 strike")

# 缺少哪些 strike？
all_strikes = step1['Strike'].unique()
t92845_strikes = t92845['Strike'].unique()
missing = set(all_strikes) - set(t92845_strikes)
print(f"缺少的 strike: {sorted(missing)}")

# 看這些缺少的 strike 在前後時間點有沒有
t92830 = step1[step1['Time'] == 92830]
t92900 = step1[step1['Time'] == 92900]

for s in sorted(missing)[:5]:
    in_830 = s in t92830['Strike'].values
    in_900 = s in t92900['Strike'].values
    print(f"  strike={s}: 在 92830={in_830}, 在 92900={in_900}")

# 看 PROD 在 92845 有沒有這些 strike
prod_df = pd.read_csv(r'資料來源\20251231\NearPROD_20251231.tsv', sep='\t', dtype=str)
prod_valid = prod_df[prod_df['strike'].notna() & (prod_df['strike'] != '')].copy()
prod_valid['time'] = prod_valid['time'].astype(int)
prod_valid['strike'] = prod_valid['strike'].astype(int)

prod_92845 = prod_valid[prod_valid['time'] == 92845]
print(f"\nPROD time=92845: {len(prod_92845)} strike")

# 看 PROD 的 last_bid 在 92845 對這些 strike 的值
for s in sorted(missing)[:5]:
    row = prod_92845[prod_92845['strike'] == s]
    if len(row) > 0:
        r = row.iloc[0]
        print(f"  strike={s}: PROD c.last_bid={r['c.last_bid']}, c.last_ask={r['c.last_ask']}")

# 看 schedule 中 92845 對應的 SysID
print("\n=== 檢查 schedule ===")
schedule_df = pd.read_csv(r'資料來源\20251231\NearPROD_20251231.tsv', sep='\t', dtype=str)
sched = schedule_df[schedule_df['strike'].isna() | (schedule_df['strike'] == '')]
print(f"Schedule 行數: {len(sched)}")
sched_92845 = sched[sched['time'] == '92845']
if len(sched_92845) > 0:
    print(f"time=92845 的 schedule: sys_id={sched_92845.iloc[0].get('sys_id', 'N/A')}")
    print(sched_92845.iloc[0].to_dict())

# 看 reconstruct_all 輸出的 Snapshot_SysID
if 'Snapshot_SysID' in step1.columns:
    t_data = step1[step1['Time'] == 92845]
    if len(t_data) > 0:
        print(f"\nstep1 中 time=92845 的 Snapshot_SysID: {t_data['Snapshot_SysID'].unique()}")

# 看看 step1 中 strike=22400 在所有時間點的資料
s22400 = step1[step1['Strike'] == 22400]
print(f"\nstrike=22400 出現的時間點數: {s22400['Time'].nunique()}")
missing_times = set(step1['Time'].unique()) - set(s22400['Time'].values)
if missing_times:
    print(f"strike=22400 缺失的時間點: {sorted(missing_times)}")
else:
    print("strike=22400 在所有時間點都有資料")
