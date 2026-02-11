"""
檢查 Next Term (Put) Strike 32500 在 09:01:00 ~ 09:01:15 的原始 ticks
檔案: J002-11300041_20251231_TXON6.csv (假設 N 是 Next Month)
"""
import pandas as pd
import glob
import os

# 找出 Put 的 CSV
# 搜尋所有 CSV
target_files = glob.glob(r'資料來源\J002-11300041_20251231\temp\*.csv')
target_prod = "32500" 

print(f"=== Raw Ticks Search (Prod: {target_prod}) ===")

for f in target_files:
    print(f"Checking {os.path.basename(f)}...")
    try:
        df = pd.read_csv(f, sep='\t')
        df.columns = [c.strip() for c in df.columns]
        
        # Filter
        df_target = df[df['svel_i081_prod_id'].astype(str).str.contains(target_prod)].copy()
        df_target['time'] = df_target['svel_i081_time'].astype(int)
        
        # 時間區間
        mask = (df_target['time'] >= 90050) & (df_target['time'] <= 90130)
        final_df = df_target[mask]
        
        if len(final_df) > 0:
            print(f"  Found {len(final_df)} ticks in {os.path.basename(f)}")
            for i, row in final_df.iterrows():
                print(f"  Time: {row['time']}")
                print(f"    Prod: {row['svel_i081_prod_id']}")
                print(f"    Bid: {row['svel_i081_best_buy_price1']}")
                print(f"    Ask: {row['svel_i081_best_sell_price1']}")
                print(f"    Seq: {row['svel_i081_seqno']}")
                print("-" * 20)
    except Exception as e:
        print(f"Error reading {f}: {e}")

