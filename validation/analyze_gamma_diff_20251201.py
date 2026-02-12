# -*- coding: utf-8 -*-
"""
分析 20251201 Near Term Gamma 差異原因
"""
import pandas as pd
import numpy as np

df = pd.read_csv('output/validation_diff_20251201.csv')

# 只看 Near term Gamma
near_gamma = df[(df['Term'] == 'Near') & (df['Column'] == 'Gamma')]
print(f'=== Near Term Gamma Total Diffs: {len(near_gamma)} ===')
print()

# Ours vs PROD 值分布
print('--- Ours value distribution ---')
print(near_gamma['Ours'].value_counts(dropna=False).head(20))
print()
print('--- PROD value distribution ---')
print(near_gamma['PROD'].value_counts(dropna=False).head(20))
print()

# CP 分布
print('--- Call/Put distribution ---')
print(near_gamma['CP'].value_counts())
print()

# Time 分布
unique_times = sorted(near_gamma['Time'].unique())
print(f'--- Unique time points with diff: {len(unique_times)} ---')
print(f'First 10: {unique_times[:10]}')
print(f'Last 10: {unique_times[-10:]}')
print()

# Strike 分布
print(f'--- Unique strikes with diff: {near_gamma["Strike"].nunique()} ---')
print()

# Ours=NaN vs Both have value
ours_nan = near_gamma[near_gamma['Ours'].isna()]
both_have = near_gamma[near_gamma['Ours'].notna()]
print(f'Ours=NaN (we have no gamma output): {len(ours_nan)}')
print(f'Both have value but different: {len(both_have)}')
print()

if len(both_have) > 0:
    print('=== Both have value samples ===')
    print(both_have[['Time','Strike','CP','Ours','PROD']].head(20).to_string())
    print()
    # 分析差異值
    diff = both_have['Ours'] - both_have['PROD']
    print(f'Diff stats: mean={diff.mean():.4f}, min={diff.min():.4f}, max={diff.max():.4f}')
    print(f'Diff distribution:')
    print(diff.value_counts().head(10))

if len(ours_nan) > 0:
    print()
    print('=== Ours=NaN samples ===')
    print(ours_nan[['Time','Strike','CP','Ours','PROD','SysID']].head(20).to_string())
    print()
    # PROD gamma 分布 (when Ours=NaN)
    print('PROD gamma values when Ours=NaN:')
    print(ours_nan['PROD'].value_counts())
    print()
    # 時間分布
    print(f'Time range: {ours_nan["Time"].min()} to {ours_nan["Time"].max()}')
    # 每個時間有多少 NaN
    time_counts = ours_nan.groupby('Time').size()
    print(f'Avg diff per time: {time_counts.mean():.1f}')
    print(f'Max diff at a time: {time_counts.max()} (at time {time_counts.idxmax()})')

# 也看看全部差異 (不只 gamma)
print()
print('=== All diff columns for Near term ===')
near_all = df[df['Term'] == 'Near']
print(near_all['Column'].value_counts())
