# -*- coding: utf-8 -*-
"""
Root cause verification: Do these diff strikes actually exist in our step1/step2 calculation?
Check if they are in the pre-merge PROD data (before Call/Put join)
"""
import pandas as pd
import numpy as np

# Read the diff data
diff_df = pd.read_csv('output/validation_diff_20251201.csv')
near_gamma = diff_df[(diff_df['Term'] == 'Near') & (diff_df['Column'] == 'Gamma')]

# Read our final output
our_near = pd.read_csv('output/驗證20251201_NearPROD.csv')

# Focus on time=84515, the time with most diffs
t = 84515
diff_at_t = near_gamma[near_gamma['Time'] == t]

print(f"=== Time={t}: {len(diff_at_t)} gamma diffs ===")
print()

# These strikes have gamma=NaN in Call side
call_diff_strikes = set(diff_at_t[diff_at_t['CP'] == 'Call']['Strike'].tolist())
put_diff_strikes = set(diff_at_t[diff_at_t['CP'] == 'Put']['Strike'].tolist())

print(f"Call gamma NaN strikes: {sorted(call_diff_strikes)}")
print(f"Put gamma NaN strikes: {sorted(put_diff_strikes)}")
print()

# Check our PROD output for one of these strikes
# For strike 15400 at 84515 - c.gamma=NaN, p.gamma=1.2
row = our_near[(our_near['time'] == t) & (our_near['strike'] == 15400)].iloc[0]
print(f"=== Strike=15400 at {t} ===")
print(f"Call side: ema={row['c.ema']}, gamma={row['c.gamma']}, source={row['c.source']}, "
      f"bid={row['c.bid']}, ask={row['c.ask']}, "
      f"last_bid={row['c.last_bid']}, last_ask={row['c.last_ask']}, "
      f"last_outlier={row.get('c.last_outlier')}")
print(f"Put side:  ema={row['p.ema']}, gamma={row['p.gamma']}, source={row['p.source']}, "
      f"bid={row['p.bid']}, ask={row['p.ask']}, "
      f"last_bid={row['p.last_bid']}, last_ask={row['p.last_ask']}, "
      f"last_outlier={row.get('p.last_outlier')}")
print()

# Check: how many total strikes at 84515 in our output vs PROD
orig = pd.read_csv('資料來源/20251201/NearPROD_20251201.tsv', sep='\t', dtype=str)
orig['time_int'] = pd.to_numeric(orig['time'], errors='coerce').fillna(0).astype(int)
orig['strike_int'] = pd.to_numeric(orig['strike'], errors='coerce').fillna(0).astype(int)
orig_t = orig[orig['time_int'] == t]

our_strikes = set(our_near[our_near['time'] == t]['strike'].tolist())
prod_strikes = set(orig_t['strike_int'].tolist())

# Strikes only in PROD, not in ours
only_prod = prod_strikes - our_strikes
only_ours = our_strikes - prod_strikes
print(f"Our strikes at {t}: {len(our_strikes)}")
print(f"PROD strikes at {t}: {len(prod_strikes)}")
print(f"Only in PROD: {sorted(only_prod)}")
print(f"Only in ours: {sorted(only_ours)}")
print()

# The question: are gamma diffs caused by the merge (outer join) bringing in NaN for missing sides?
# Let's verify: for strikes where c.source is NaN, does Call even exist in our calculation?
# If c.source is NaN, it means Call was never calculated OR was lost in merge

# Check how many rows have NaN source
print("=== c.source distribution at 84515 ===")
our_t = our_near[our_near['time'] == t]
print(our_t['c.source'].value_counts(dropna=False))
print()
print("=== p.source distribution at 84515 ===")
print(our_t['p.source'].value_counts(dropna=False))
print()

# So the key question: WHY does c.source become NaN for these strikes?
# It should be one of: Q_Last_Valid, Q_Min_Valid, Replacement
# NaN means the Call side never existed for this strike at this time

# Verification: check one specific strike in PROD - what does PROD have?
print("=== PROD Strike 15400 at 84515 ===")
prod_row = orig_t[orig_t['strike_int'] == 15400]
if len(prod_row) > 0:
    for col in prod_row.columns:
        print(f"  {col}: {prod_row.iloc[0][col]}")
