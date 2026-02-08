"""
全面驗證 Gamma 值是否與 PROD 一致
比較前10個時間點的所有序列
"""
import pandas as pd
pd.set_option('display.width', 400)
pd.set_option('display.max_columns', None)

# 載入 PROD 資料
prod = pd.read_csv(r'c:\AGY\VIX\VIX\資料來源\20251231\NearPROD_20251231.tsv', sep='\t', dtype=str)

# 載入我們的計算結果
calc = pd.read_csv('step0_full_output_Near_前10個.csv')

# 取得前10個時間點
times_to_check = ['084500', '084515', '084530', '084545', '084600', 
                  '084615', '084630', '084645', '084700', '084715']

print("=" * 80)
print("全面驗證 Gamma 值")
print("=" * 80)

# 統計結果
total_compared = 0
total_matched = 0
mismatches = []

for time_str in times_to_check:
    time_int = int(time_str)
    
    # 取得該時間點的 PROD 資料
    prod_time = prod[prod['time'] == time_str]
    calc_time = calc[calc['Time'] == time_int]
    
    print(f"\n--- 時間: {time_str} ---")
    print(f"PROD 筆數: {len(prod_time)}, 我們的筆數: {len(calc_time)}")
    
    # 比較 Call 選項的 gamma
    for _, prod_row in prod_time.iterrows():
        strike = prod_row['strike']
        prod_gamma = float(prod_row['c.gamma']) if pd.notna(prod_row['c.gamma']) else None
        
        # 找對應的計算結果
        calc_row = calc_time[(calc_time['Strike'] == int(strike)) & (calc_time['CP'] == 'Call')]
        
        if not calc_row.empty and prod_gamma is not None:
            our_gamma = calc_row.iloc[0]['Q_Last_Valid_Gamma']
            total_compared += 1
            
            if abs(prod_gamma - our_gamma) < 0.01:
                total_matched += 1
            else:
                mismatches.append({
                    'Time': time_str,
                    'Strike': strike,
                    'CP': 'Call',
                    'PROD_gamma': prod_gamma,
                    'Our_gamma': our_gamma
                })
    
    # 比較 Put 選項的 gamma
    for _, prod_row in prod_time.iterrows():
        strike = prod_row['strike']
        prod_gamma = float(prod_row['p.gamma']) if pd.notna(prod_row['p.gamma']) else None
        
        # 找對應的計算結果
        calc_row = calc_time[(calc_time['Strike'] == int(strike)) & (calc_time['CP'] == 'Put')]
        
        if not calc_row.empty and prod_gamma is not None:
            our_gamma = calc_row.iloc[0]['Q_Last_Valid_Gamma']
            total_compared += 1
            
            if abs(prod_gamma - our_gamma) < 0.01:
                total_matched += 1
            else:
                mismatches.append({
                    'Time': time_str,
                    'Strike': strike,
                    'CP': 'Put',
                    'PROD_gamma': prod_gamma,
                    'Our_gamma': our_gamma
                })

print("\n" + "=" * 80)
print("驗證結果總結")
print("=" * 80)

print(f"\n總比較筆數: {total_compared}")
print(f"完全一致: {total_matched}")
print(f"不一致: {len(mismatches)}")
print(f"正確率: {total_matched/total_compared*100:.2f}%")

if mismatches:
    print(f"\n不一致的案例 (前20筆):")
    mismatch_df = pd.DataFrame(mismatches)
    print(mismatch_df.head(20).to_string(index=False))
    
    # 分析不一致的模式
    print(f"\n不一致的 PROD gamma 分布:")
    print(mismatch_df['PROD_gamma'].value_counts())
    print(f"\n不一致的 Our gamma 分布:")
    print(mismatch_df['Our_gamma'].value_counts())
else:
    print("\n所有 Gamma 值完全一致! ")
