# -*- coding: utf-8 -*-
"""
Final verification: source=NaN root cause
Check if these strikes were in step0_valid_quotes output but lost in Call/Put merge
"""
import pandas as pd
import numpy as np

our_near = pd.read_csv('output/驗證20251201_NearPROD.csv')

# The Call source=NaN strikes at 84515
nan_call_strikes = [15400,17000,17200,17800,18200,18600,18800,20400,
                    21700,21900,22100,22300,23100,23500,23700,23900,24100,24300]

# For these strikes, c.source is NaN but the row exists (because Put side exists)
# This means: when we did the outer merge of Call and Put DataFrames,
# Call didn't have these strikes, but Put did, so the row got created with Call side = NaN

# PROD on the other hand, HAS both sides for these strikes
# PROD shows c.bid=0, c.ask=0, c.last_bid=0, c.last_ask=0, c.ema=0, c.gamma=1.2
# This means PROD creates an entry even when there's NO quote data (bid=0, ask=0, all zeros)
# PROD assigns gamma=1.2 (GAMMA_0 = bid==0 case)

# Our system: if a strike only has Put data and no Call data at all,
# the Call side won't even be in our calculation output
# When we do the Call/Put merge, Put creates the row, but Call side is all NaN

# Verify: For a working strike at 84515 (say 19000), both sides should exist
row_19000 = our_near[(our_near['time']==84515)&(our_near['strike']==19000)]
if len(row_19000) > 0:
    r = row_19000.iloc[0]
    print(f"Working strike 19000: c.source={r['c.source']}, p.source={r['p.source']}")
    print(f"  c.gamma={r['c.gamma']}, p.gamma={r['p.gamma']}")
    print()

# Check original PROD for these NaN strikes - what's their Call data?
orig = pd.read_csv('資料來源/20251201/NearPROD_20251201.tsv', sep='\t', dtype=str)
orig['time_int'] = pd.to_numeric(orig['time'], errors='coerce').fillna(0).astype(int)
orig['strike_int'] = pd.to_numeric(orig['strike'], errors='coerce').fillna(0).astype(int)

print("=== PROD Call data for NaN-gamma strikes at 84515 ===")
for s in nan_call_strikes[:5]:
    row = orig[(orig['time_int']==84515)&(orig['strike_int']==s)]
    if len(row)>0:
        r = row.iloc[0]
        print(f"Strike={s}: c.bid={r['c.bid']}, c.ask={r['c.ask']}, c.last_bid={r['c.last_bid']}, "
              f"c.last_ask={r['c.last_ask']}, c.sysID={r['c.sysID']}, c.time={r['c.time']}, c.gamma={r['c.gamma']}")

print()

# Summary: The gamma diffs happen because our system doesn't create entries for Call (or Put)
# when there's absolutely no quote data for that side. PROD always creates entries for all strikes.
# When PROD has c.bid=0, c.ask=0 with c.sysID=0 and c.time=0, it means "no data" but still outputs gamma=1.2

# Now let's check: are all 133 diffs of the same pattern?
diff_df = pd.read_csv('output/validation_diff_20251201.csv')
near_gamma = diff_df[(diff_df['Term']=='Near')&(diff_df['Column']=='Gamma')]

# For each diff, check if the corresponding source is NaN
source_check = []
for _, dr in near_gamma.iterrows():
    t, s, cp = dr['Time'], dr['Strike'], dr['CP']
    row = our_near[(our_near['time']==t)&(our_near['strike']==s)]
    if len(row)>0:
        r = row.iloc[0]
        source_col = 'c.source' if cp=='Call' else 'p.source'
        source_check.append(pd.isna(r[source_col]))
    else:
        source_check.append('ROW_MISSING')

print("=== All 133 gamma diffs have source=NaN? ===")
from collections import Counter
print(Counter(source_check))
# Expected: all True (meaning source=NaN for all diffs)

print()
# Also check time progression: does the same strike stop having NaN after some time?
# For strike 15400 Call, track source over time
print("=== Strike 15400 Call source over time ===")
s15400 = our_near[our_near['strike']==15400].sort_values('time')
for _, r in s15400.head(20).iterrows():
    print(f"time={r['time']}: c.source={r['c.source']}, c.gamma={r['c.gamma']}")

print()
# How does the diff count change over time?
print("=== Diff count by time ===")
print(near_gamma.groupby('Time').size().to_string())
