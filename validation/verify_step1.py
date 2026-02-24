import pandas as pd
import numpy as np
import os
import argparse
from datetime import datetime

def check_sigma_diff(date_str, source_dir="資料來源", output_dir="output"):
    # PROD
    prod_path = os.path.join(source_dir, date_str, f"sigma_{date_str}.tsv")
    my_path = os.path.join(output_dir, f"my_sigma_{date_str}.tsv")

    if not os.path.exists(prod_path):
        print(f"找不到 PROD 資料: {prod_path}")
        return False
    if not os.path.exists(my_path):
        print(f"找不到我們算出的資料: {my_path}")
        return False

    df_prod = pd.read_csv(prod_path, sep="\t", dtype={"time": str})
    df_my = pd.read_csv(my_path, sep="\t", dtype={"time": str})

    df_prod["time"] = df_prod["time"].astype(str).str.zfill(6)
    df_my["time"] = df_my["time"].astype(str).str.zfill(6)

    df = pd.merge(df_prod, df_my, on=["date", "time"], suffixes=("_prod", "_my"), how="outer")

    errors = []
    
    # 比較項目
    cols_to_check = ["nearSigma2", "nextSigma2", "vix", "ori_vix"]
    for col in cols_to_check:
        my_col = f"{col}_my"
        prod_col = f"{col}_prod"
        
        diff = np.abs(pd.to_numeric(df[my_col], errors='coerce') - pd.to_numeric(df[prod_col], errors='coerce'))
        
        # 找出大於 1e-4 的差異 (而且不能是 NaN)
        is_err = (diff > 1e-4) & pd.notnull(diff)
        
        if is_err.any():
            max_diff = diff[is_err].max()
            err_count = is_err.sum()
            errors.append(f"{col} 最大差異: {max_diff:.6f} (共 {err_count} 筆不符)")

    if errors:
        print(f"[FAIL] {date_str} Step 1 驗證失敗:")
        for err in errors:
            print(f"  - {err}")
        return False
    else:
        print(f"[PASS] {date_str} Step 1 驗證成功 (比對 {len(df)} 筆時間點)")
        return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('date', type=str, help='YYYYMMDD')
    args = parser.parse_args()
    
    check_sigma_diff(args.date)
