# -*- coding: utf-8 -*-
"""
Deep analysis: Why are gamma values NaN for Near term at early time points?
Cross-reference with our PROD output and original PROD data
"""
import pandas as pd
import numpy as np

# Read our PROD output
our_df = pd.read_csv('output/validation_diff_20251201.csv')
near_gamma = our_df[(our_df['Term'] == 'Near') & (our_df['Column'] == 'Gamma')]

# Read our full Near PROD output
our_near = pd.read_csv('output/驗證20251201_NearPROD.csv')

# Read original PROD
orig_near = pd.read_csv('資料來源/20251201/NearPROD_20251201.tsv', sep='\t', dtype=str)

print("=== Our Near PROD output shape ===")
print(f"Rows: {len(our_near)}, Cols: {len(our_near.columns)}")
print(f"Columns: {our_near.columns.tolist()}")
print()

# Check all gamma values for time 84515
t1 = our_near[our_near['time'] == 84515]
print(f"=== Our output at time=84515: {len(t1)} rows ===")
# Get strikes that have diff
diff_strikes_84515 = near_gamma[near_gamma['Time'] == 84515]['Strike'].tolist()
print(f"Diff strikes at 84515: {diff_strikes_84515}")
print()

# Get our data for those strikes
for s in diff_strikes_84515[:5]:
    row = t1[t1['strike'] == s]
    if len(row) > 0:
        r = row.iloc[0]
        print(f"Strike={s}: c.gamma={r.get('c.gamma')}, p.gamma={r.get('p.gamma')}, "
              f"c.ema={r.get('c.ema')}, p.ema={r.get('p.ema')}, "
              f"c.bid={r.get('c.bid')}, c.ask={r.get('c.ask')}, "
              f"c.last_bid={r.get('c.last_bid')}, c.last_ask={r.get('c.last_ask')}, "
              f"c.source={r.get('c.source')}")
    else:
        print(f"Strike={s}: NOT FOUND in our output")

print()

# Check original PROD for same strikes at 84515
orig_near['time_int'] = pd.to_numeric(orig_near['time'], errors='coerce').fillna(0).astype(int)
orig_near['strike_int'] = pd.to_numeric(orig_near['strike'], errors='coerce').fillna(0).astype(int)
orig_t1 = orig_near[orig_near['time_int'] == 84515]

print(f"=== PROD at time=84515: {len(orig_t1)} rows ===")
for s in diff_strikes_84515[:5]:
    row = orig_t1[orig_t1['strike_int'] == s]
    if len(row) > 0:
        r = row.iloc[0]
        print(f"Strike={s}: c.gamma={r.get('c.gamma')}, p.gamma={r.get('p.gamma')}, "
              f"c.ema={r.get('c.ema')}, p.ema={r.get('p.ema')}, "
              f"c.bid={r.get('c.bid')}, c.ask={r.get('c.ask')}, "
              f"c.last_bid={r.get('c.last_bid')}, c.last_ask={r.get('c.last_ask')}")
    else:
        print(f"Strike={s}: NOT FOUND in PROD")

print()

# Key question: Are the NaN gammas in CALL or PUT or both?
# Let's look at which column (c.gamma vs p.gamma) is NaN for diff strikes
print("=== Checking c.gamma and p.gamma for diff strikes ===")
for _, dr in near_gamma[near_gamma['Time'] == 84515].iterrows():
    s = dr['Strike']
    cp = dr['CP']
    row = t1[t1['strike'] == s]
    if len(row) > 0:
        r = row.iloc[0]
        gamma_col = 'c.gamma' if cp == 'Call' else 'p.gamma'
        ema_col = 'c.ema' if cp == 'Call' else 'p.ema'
        last_bid_col = 'c.last_bid' if cp == 'Call' else 'p.last_bid'
        last_ask_col = 'c.last_ask' if cp == 'Call' else 'p.last_ask'
        source_col = 'c.source' if cp == 'Call' else 'p.source'
        print(f"Strike={s} {cp}: gamma={r[gamma_col]}, ema={r[ema_col]}, "
              f"last_bid={r[last_bid_col]}, last_ask={r[last_ask_col]}, source={r[source_col]}")

print()
# Check: are ALL gammas NaN at 84515 or just some?
print("=== All c.gamma values at 84515 ===")
print(t1['c.gamma'].value_counts(dropna=False).head(10))
print()
print("=== All p.gamma values at 84515 ===")
print(t1['p.gamma'].value_counts(dropna=False).head(10))
