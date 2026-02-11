"""
驗證 PROD 格式輸出一致性
比對我們計算的 PROD 格式結果與原始 PROD 資料
"""
import pandas as pd
import numpy as np
from datetime import datetime

pd.set_option('display.width', 400)
pd.set_option('display.max_columns', None)

def verify_term(our_prod_path, original_prod_path, term_name):
    """驗證單一Term的結果"""
    print(f"\n{'='*80}")
    print(f"驗證 {term_name} Term")
    print(f"{'='*80}")
    
    # 讀取資料
    our_df = pd.read_csv(our_prod_path)
    orig_df = pd.read_csv(original_prod_path, sep='\t', dtype=str)
    
    print(f"  我們的資料: {len(our_df)} 筆")
    print(f"  原始PROD:  {len(orig_df)} 筆")
    
    # 對齊欄位 - 將原始PROD的time轉換為整數,先處理空值
    orig_df_valid = orig_df[orig_df['strike'].notna() & (orig_df['strike'] != '')].copy()
    orig_df_valid['time_int'] = pd.to_numeric(orig_df_valid['time'], errors='coerce').fillna(0).astype(int)
    orig_df_valid['strike_int'] = pd.to_numeric(orig_df_valid['strike'], errors='coerce').fillna(0).astype(int)
    
    # 合併資料進行比對
    merged = pd.merge(
        our_df,
        orig_df_valid,
        left_on=['time', 'strike'],
        right_on=['time_int', 'strike_int'],
        how='inner',
        suffixes=('_ours', '_orig')
    )
    
    print(f"  成功配對: {len(merged)} 筆")
    
    if len(merged) == 0:
        print("  ❌ 無法配對任何資料!")
        return
    
    # 定義要比對的數值欄位
    compare_fields = [
        ('c.ema', 'c.ema', 1e-4, 'Call EMA'),
        ('p.ema', 'p.ema', 1e-4, 'Put EMA'),
        ('c.bid', 'c.bid', 0.1, 'Call 最終買價'),
        ('c.ask', 'c.ask', 0.1, 'Call 最終賣價'),
        ('p.bid', 'p.bid', 0.1, 'Put 最終買價'),
        ('p.ask', 'p.ask', 0.1, 'Put 最終賣價'),
    ]
    
    results = {}
    
    for our_col, orig_col, tolerance, description in compare_fields:
        # 轉換為數值
        our_vals = pd.to_numeric(merged[our_col + '_ours'], errors='coerce')
        orig_vals = pd.to_numeric(merged[orig_col + '_orig'], errors='coerce')
        
        # 計算差異
        diff = (our_vals - orig_vals).abs()
        valid_mask = our_vals.notna() & orig_vals.notna()
        
        if valid_mask.sum() == 0:
            continue
            
        matches = (diff <= tolerance) | ~valid_mask
        match_count = matches.sum()
        total_count = len(merged)
        match_rate = match_count / total_count * 100
        
        results[description] = {
            'match_count': match_count,
            'total_count': total_count,
            'match_rate': match_rate,
            'mismatches': total_count - match_count
        }
    
    # 輸出結果
    print(f"\n  數值比對結果:")
    for field, result in results.items():
        print(f"    【{field}】")
        print(f"      正確率: {result['match_count']}/{result['total_count']} = {result['match_rate']:.2f}%")
        if result['mismatches'] > 0:
            print(f"      不一致: {result['mismatches']} 筆")
    
    # 比對Outlier標記
    print(f"\n  Outlier標記比對:")
    for prefix in ['c', 'p']:
        cp_name = 'Call' if prefix == 'c' else 'Put'
                # Last Outlier
        our_col = f'{prefix}.last_outlier_ours'
        orig_col = f'{prefix}.last_outlier_orig'
        
        if our_col in merged.columns and orig_col in merged.columns:
            our_last_outlier = merged[our_col].fillna('-')
            orig_last_outlier = merged[orig_col].fillna('-')
            
            # 轉換V和數字都視為已判定
            last_match = (our_last_outlier == orig_last_outlier) | \
                         ((our_last_outlier != '-') & (orig_last_outlier != '-'))
            last_match_count = last_match.sum()
            last_total = len(merged)
            
            print(f"    【{cp_name} Last Outlier】: {last_match_count}/{last_total} = {last_match_count/last_total*100:.2f}%")
        
        # Min Outlier
        our_min_col = f'{prefix}.min_outlier_ours'
        orig_min_col = f'{prefix}.min_outlier_orig'
        
        if our_min_col in merged.columns and orig_min_col in merged.columns:
            our_min_outlier = merged[our_min_col].fillna('-')
            orig_min_outlier = merged[orig_min_col].fillna('-')
            
            min_match = (our_min_outlier == orig_min_outlier) | \
                        ((our_min_outlier != '-') & (orig_min_outlier != '-'))
            min_match_count = min_match.sum()
            min_total = len(merged)
            
            print(f"    【{cp_name} Min Outlier】: {min_match_count}/{min_total} = {min_match_count/min_total*100:.2f}%")
    
    # 統計最終報價來源分布
    print(f"\n  報價來源分布:")
    if 'c.source_ours' in merged.columns:
        print(f"    Call:")
        print(f"      {merged['c.source_ours'].value_counts().to_string(name=False)}")
    if 'p.source_ours' in merged.columns:
        print(f"    Put:")
        print(f"      {merged['p.source_ours'].value_counts().to_string(name=False)}")
    
    return results

def main():
    print("="*80)
    print("VIX PROD 格式驗證")
    print(f"執行時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    target_date = "20251231"
    
    # 驗證 Near Term
    near_results = verify_term(
        f'output/驗證{target_date}_NearPROD.csv',
        f'資料來源/{target_date}/NearPROD_{target_date}.tsv',
        'Near'
    )
    
    # 驗證 Next Term  
    next_results = verify_term(
        f'output/驗證{target_date}_NextPROD.csv',
        f'資料來源/{target_date}/NextPROD_{target_date}.tsv',
        'Next'
    )
    
    print(f"\n{'='*80}")
    print("驗證完成")
    print("="*80)

if __name__ == "__main__":
    main()
