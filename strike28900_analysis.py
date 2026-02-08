"""
Strike=28900 詳細計算過程分析
"""
import pandas as pd

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 300)
pd.set_option('display.max_colwidth', 60)

# 載入完整計算結果
calc_df = pd.read_csv('step0_full_output_Near_前10個.csv')

# 篩選 Strike=28900 的 Call
call_28900 = calc_df[(calc_df['Strike']==28900) & (calc_df['CP']=='Call')].copy()

# 載入 PROD 資料
prod_df = pd.read_csv(r'c:\AGY\VIX\VIX\資料來源\20251231\NearPROD_20251231.tsv', sep='\t', dtype=str)
prod_df = prod_df[prod_df['strike'].notna() & (prod_df['strike'] != '')]

# 選擇要顯示的欄位
cols = [
    'Time', 
    'Q_Last_Valid_Bid', 'Q_Last_Valid_Ask', 'Q_Last_Valid_Spread',
    'Q_Min_Valid_Bid', 'Q_Min_Valid_Ask', 'Q_Min_Valid_Spread',
    'EMA',
    'Q_Last_Valid_Gamma', 'Q_Min_Valid_Gamma',
    'Q_Last_Valid_Is_Outlier', 'Q_Min_Valid_Is_Outlier',
    'Q_hat_Bid', 'Q_hat_Ask', 'Q_hat_Source'
]

result = call_28900[cols].copy()

# 加入 PROD 資料
result['PROD_C_Bid'] = None
result['PROD_C_Ask'] = None

for i, row in result.iterrows():
    time_val = str(int(row['Time'])).zfill(6)
    prod_match = prod_df[(prod_df['time']==time_val) & (prod_df['strike']=='28900')]
    if not prod_match.empty:
        result.loc[i, 'PROD_C_Bid'] = prod_match.iloc[0]['c.bid']
        result.loc[i, 'PROD_C_Ask'] = prod_match.iloc[0]['c.ask']

# 比對結果
result['Bid_Match'] = result.apply(
    lambda r: '✓' if pd.notna(r['Q_hat_Bid']) and pd.notna(r['PROD_C_Bid']) and 
              abs(float(r['Q_hat_Bid']) - float(r['PROD_C_Bid'])) < 0.01 else '✗', axis=1
)
result['Ask_Match'] = result.apply(
    lambda r: '✓' if pd.notna(r['Q_hat_Ask']) and pd.notna(r['PROD_C_Ask']) and 
              abs(float(r['Q_hat_Ask']) - float(r['PROD_C_Ask'])) < 0.01 else '✗', axis=1
)

print('=' * 120)
print('Strike=28900, CP=Call 計算過程與 PROD 比對')
print('=' * 120)
print()

# 逐行顯示詳細資訊
for idx, row in result.iterrows():
    time_val = int(row['Time'])
    if time_val == 84500:
        continue  # 跳過第一個時間點
    
    print(f"【時間: {str(time_val).zfill(6)}】")
    print(f"  Q_Last_Valid: Bid={row['Q_Last_Valid_Bid']}, Ask={row['Q_Last_Valid_Ask']}, Spread={row['Q_Last_Valid_Spread']}")
    print(f"  Q_Min_Valid:  Bid={row['Q_Min_Valid_Bid']}, Ask={row['Q_Min_Valid_Ask']}, Spread={row['Q_Min_Valid_Spread']}")
    print(f"  EMA: {row['EMA']}")
    print(f"  Gamma: Q_Last={row['Q_Last_Valid_Gamma']}, Q_Min={row['Q_Min_Valid_Gamma']}")
    print(f"  Is_Outlier: Q_Last={row['Q_Last_Valid_Is_Outlier']}, Q_Min={row['Q_Min_Valid_Is_Outlier']}")
    print(f"  >>> 計算結果 Q_hat: Bid={row['Q_hat_Bid']}, Ask={row['Q_hat_Ask']} (來源: {row['Q_hat_Source']})")
    print(f"  >>> PROD 結果:      Bid={row['PROD_C_Bid']}, Ask={row['PROD_C_Ask']}")
    print(f"  >>> 比對: Bid={row['Bid_Match']}, Ask={row['Ask_Match']}")
    print()

print('=' * 120)
