
import pandas as pd
import numpy as np

def check_gamma_diff(term_name, our_path, orig_path):
    print(f"\nChecking {term_name} Term Gamma Differences...")
    
    # Read files
    try:
        our_df = pd.read_csv(our_path)
        orig_df = pd.read_csv(orig_path, sep='\t', dtype=str)
    except FileNotFoundError as e:
        print(f"Error reading files: {e}")
        return

    # Preprocess Original PROD data
    # Filter valid strikes
    orig_df_valid = orig_df[orig_df['strike'].notna() & (orig_df['strike'] != '')].copy()
    
    # Convert join keys to integer for matching
    orig_df_valid['time_int'] = pd.to_numeric(orig_df_valid['time'], errors='coerce').fillna(0).astype(int)
    orig_df_valid['strike_int'] = pd.to_numeric(orig_df_valid['strike'], errors='coerce').fillna(0).astype(int)
    
    # Merge
    merged = pd.merge(
        our_df,
        orig_df_valid,
        left_on=['time', 'strike'],
        right_on=['time_int', 'strike_int'],
        how='inner',
        suffixes=('_ours', '_orig')
    )
    
    # Columns to check
    check_cols = [('c.gamma', 'Call'), ('p.gamma', 'Put')]
    
    diff_list = []
    
    for col, cp_label in check_cols:
        our_col = f"{col}_ours"
        orig_col = f"{col}_orig"
        
        if our_col not in merged.columns or orig_col not in merged.columns:
            print(f"Column {col} not found in merged data.")
            continue
            
        # Convert to numeric, forcing errors to NaN
        our_vals = pd.to_numeric(merged[our_col], errors='coerce')
        orig_vals = pd.to_numeric(merged[orig_col], errors='coerce')
        
        # Compare (with a small tolerance for floating point)
        # Assuming PROD gamma might be integer-like (1, 2, 3) or float
        # Gamma in our code is 1.2, 1.5, 2.0 (floats)
        
        # Determine differences
        # We consider it a diff if abs diff > 0.01
        is_diff = (our_vals - orig_vals).abs() > 0.01
        
        diff_rows = merged[is_diff]
        
        if len(diff_rows) > 0:
            for idx, row in diff_rows.iterrows():
                diff_data = {
                    'nearnext': term_name,
                    'time': row['time'],
                    'strike': row['strike'],
                    'cp': cp_label, # row['cp'] doesn't exist in PROD format typically, we use column name
                    'our_val': row[our_col],
                    'orig_val': row[orig_col]
                }
                diff_list.append(diff_data)

    if diff_list:
        print(f"Found {len(diff_list)} discrepancies in {term_name}.")
        # Print first few and summary
        print(f"{'Term':<6} | {'Time':<6} | {'Strike':<6} | {'CP':<4} | {'Our Gamma':<10} | {'Orig Gamma':<10}")
        print("-" * 60)
        for item in diff_list:
             print(f"{item['nearnext']:<6} | {item['time']:<6} | {item['strike']:<6} | {item['cp']:<4} | {item['our_val']:<10} | {item['orig_val']:<10}")
    else:
        print(f"No discrepancies found for {term_name}.")

def main():
    target_date = "20251231"
    
    # Paths (adjust as needed based on file system)
    near_our = f'output/驗證{target_date}_NearPROD.csv'
    near_orig = f'資料來源/{target_date}/NearPROD_{target_date}.tsv'
    
    next_our = f'output/驗證{target_date}_NextPROD.csv'
    next_orig = f'資料來源/{target_date}/NextPROD_{target_date}.tsv'
    
    check_gamma_diff('Near', near_our, near_orig)
    check_gamma_diff('Next', next_our, next_orig)

if __name__ == "__main__":
    main()
