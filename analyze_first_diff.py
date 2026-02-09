"""
VIX 差異分析腳本
依照時間順序找出第一筆差異並詳細分析
"""
import pandas as pd
import numpy as np

pd.set_option('display.width', 400)
pd.set_option('display.max_columns', None)

def main():
    print("=" * 80)
    print("VIX Step 0 差異分析 - 找出第一筆差異")
    print("=" * 80)
    
    # 載入資料
    print("\n>>> 載入資料...")
    
    # PROD 資料
    near_prod = pd.read_csv(r'資料來源\20251231\NearPROD_20251231.tsv', sep='\t', dtype=str)
    
    # 我們的計算結果
    near_calc = pd.read_csv('step0_full_output_Near_測試前30個.csv')
    
    print(f"    PROD: {len(near_prod)} 筆")
    print(f"    我們: {len(near_calc)} 筆")
    
    # 準備 PROD 資料（展開 Call/Put）
    prod_valid = near_prod[near_prod['strike'].notna() & (near_prod['strike'] != '')].copy()
    prod_valid['time_int'] = prod_valid['time'].astype(int)
    prod_valid['strike_int'] = prod_valid['strike'].astype(int)
    
    # 取得我們有的時間點
    our_times = sorted(near_calc['Time'].unique())
    print(f"\n    我們的時間點: {our_times[:5]} ... (共 {len(our_times)} 個)")
    
    # 依時間順序分析
    print("\n" + "=" * 80)
    print("依時間順序分析差異")
    print("=" * 80)
    
    for time_int in our_times:
        print(f"\n>>> 分析時間點: {time_int}")
        
        # 取出該時間點的所有資料
        prod_at_time = prod_valid[prod_valid['time_int'] == time_int]
        calc_at_time = near_calc[near_calc['Time'] == time_int]
        
        if len(prod_at_time) == 0:
            print(f"    PROD 無此時間點資料")
            continue
            
        print(f"    PROD 有 {len(prod_at_time)} 個 Strike")
        print(f"    我們有 {len(calc_at_time)} 筆（含 Call/Put）")
        
        # 找出第一個不匹配的 (Strike, CP) 組合
        found_mismatch = False
        
        for _, prod_row in prod_at_time.iterrows():
            strike = int(prod_row['strike'])
            
            for cp, prefix in [('Call', 'c'), ('Put', 'p')]:
                # 找對應的計算結果
                calc_row = calc_at_time[(calc_at_time['Strike'] == strike) & 
                                        (calc_at_time['CP'] == cp)]
                
                if calc_row.empty:
                    continue
                    
                calc_row = calc_row.iloc[0]
                
                # 比較各個欄位
                mismatches = []
                
                # Q_hat Bid
                prod_bid = prod_row[f'{prefix}.bid']
                our_bid = calc_row['Q_hat_Bid']
                if pd.notna(prod_bid) and prod_bid != '':
                    try:
                        if int(float(prod_bid)) != int(float(our_bid)):
                            mismatches.append(('Q_hat_Bid', prod_bid, our_bid))
                    except:
                        pass
                
                # Q_hat Ask
                prod_ask = prod_row[f'{prefix}.ask']
                our_ask = calc_row['Q_hat_Ask']
                if pd.notna(prod_ask) and prod_ask != '':
                    try:
                        if int(float(prod_ask)) != int(float(our_ask)):
                            mismatches.append(('Q_hat_Ask', prod_ask, our_ask))
                    except:
                        pass
                
                # EMA
                prod_ema = prod_row[f'{prefix}.ema']
                our_ema = calc_row['EMA']
                if pd.notna(prod_ema) and prod_ema != '':
                    try:
                        diff = abs(float(prod_ema) - float(our_ema))
                        if diff >= 1e-4:
                            mismatches.append(('EMA', prod_ema, our_ema))
                    except:
                        pass
                
                # Gamma
                prod_gamma = prod_row[f'{prefix}.gamma']
                our_gamma = calc_row['Q_Last_Valid_Gamma']
                if pd.notna(prod_gamma) and prod_gamma != '':
                    try:
                        if abs(float(prod_gamma) - float(our_gamma)) >= 0.01:
                            mismatches.append(('Gamma', prod_gamma, our_gamma))
                    except:
                        pass
                
                # Outlier
                prod_outlier = prod_row[f'{prefix}.last_outlier']
                our_outlier = calc_row['Q_Last_Valid_Is_Outlier']
                if prod_outlier == 'V' and our_outlier != True:
                    mismatches.append(('Outlier', prod_outlier, our_outlier))
                elif prod_outlier not in ['V', '-', '', None] and not pd.isna(prod_outlier) and our_outlier != False:
                    mismatches.append(('Outlier', prod_outlier, our_outlier))
                
                if mismatches:
                    found_mismatch = True
                    print(f"\n    [差異] Strike={strike}, CP={cp}")
                    print(f"    " + "-" * 60)
                    
                    for field, prod_val, our_val in mismatches:
                        print(f"    {field}:")
                        print(f"        PROD: {prod_val}")
                        print(f"        我們: {our_val}")
                    
                    # 列印完整比較資訊
                    print(f"\n    【完整 PROD 資料】")
                    print(f"        {prefix}.bid = {prod_row[f'{prefix}.bid']}")
                    print(f"        {prefix}.ask = {prod_row[f'{prefix}.ask']}")
                    print(f"        {prefix}.last_bid = {prod_row[f'{prefix}.last_bid']}")
                    print(f"        {prefix}.last_ask = {prod_row[f'{prefix}.last_ask']}")
                    print(f"        {prefix}.last_outlier = {prod_row[f'{prefix}.last_outlier']}")
                    print(f"        {prefix}.min_bid = {prod_row[f'{prefix}.min_bid']}")
                    print(f"        {prefix}.min_ask = {prod_row[f'{prefix}.min_ask']}")
                    print(f"        {prefix}.min_outlier = {prod_row[f'{prefix}.min_outlier']}")
                    print(f"        {prefix}.ema = {prod_row[f'{prefix}.ema']}")
                    print(f"        {prefix}.gamma = {prod_row[f'{prefix}.gamma']}")
                    
                    print(f"\n    【我們的計算結果】")
                    print(f"        Q_hat_Bid = {calc_row['Q_hat_Bid']}")
                    print(f"        Q_hat_Ask = {calc_row['Q_hat_Ask']}")
                    print(f"        Q_hat_Source = {calc_row['Q_hat_Source']}")
                    print(f"        Q_Last_Valid_Bid = {calc_row['Q_Last_Valid_Bid']}")
                    print(f"        Q_Last_Valid_Ask = {calc_row['Q_Last_Valid_Ask']}")
                    print(f"        Q_Last_Valid_Is_Outlier = {calc_row['Q_Last_Valid_Is_Outlier']}")
                    print(f"        Q_Min_Valid_Bid = {calc_row['Q_Min_Valid_Bid']}")
                    print(f"        Q_Min_Valid_Ask = {calc_row['Q_Min_Valid_Ask']}")
                    print(f"        Q_Min_Valid_Is_Outlier = {calc_row['Q_Min_Valid_Is_Outlier']}")
                    print(f"        EMA = {calc_row['EMA']}")
                    print(f"        Q_Last_Valid_Gamma = {calc_row['Q_Last_Valid_Gamma']}")
                    
                    print("\n" + "=" * 80)
                    print("分析結束：已找到第一筆差異")
                    print("=" * 80)
                    return  # 找到第一筆差異就停止
        
        if not found_mismatch:
            print(f"    [OK] 此時間點無差異")

if __name__ == "__main__":
    main()
