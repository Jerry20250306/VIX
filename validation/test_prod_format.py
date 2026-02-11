"""
測試 PROD 格式輸出轉換
"""
import pandas as pd
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 載入 step0_2_ema_calculation 模組
from step0_2_ema_calculation import convert_to_prod_format, save_prod_format

print("=" * 60)
print("測試 PROD 格式輸出轉換")
print("=" * 60)

# 讀取已有的全天計算結果
near_csv = "step0_full_output_Near_全天.csv"
next_csv = "step0_full_output_Next_全天.csv"

if not os.path.exists(near_csv):
    print(f"錯誤: 找不到 {near_csv}")
    print("請先執行完整計算流程")
    sys.exit(1)

print(f"\n>>> 讀取計算結果...")
near_df = pd.read_csv(near_csv)
next_df = pd.read_csv(next_csv)

print(f"    Near Term: {len(near_df)} 筆")
print(f"    Next Term: {len(next_df)} 筆")

# 只取前 30 個時間點測試
unique_times = sorted(near_df['Time'].unique())[:30]
near_df_30 = near_df[near_df['Time'].isin(unique_times)]
next_df_30 = next_df[next_df['Time'].isin(unique_times)]

print(f"\n>>> 測試前 {len(unique_times)} 個時間點...")
print(f"    Near Term: {len(near_df_30)} 筆")
print(f"    Next Term: {len(next_df_30)} 筆")

# 轉換為 PROD 格式
print(f"\n>>> 轉換為 PROD 格式...")

# 建立 output 目錄
os.makedirs("output", exist_ok=True)

# Near Term
near_prod = convert_to_prod_format(near_df_30)
near_prod.to_csv("output/step0_Near_PROD格式_前30時點.csv", index=False, encoding="utf-8-sig")
print(f"    Near Term 轉換完成: {len(near_prod)} 筆")

# Next Term
next_prod = convert_to_prod_format(next_df_30)
next_prod.to_csv("output/step0_Next_PROD格式_前30時點.csv", index=False, encoding="utf-8-sig")
print(f"    Next Term 轉換完成: {len(next_prod)} 筆")

# 顯示欄位
print(f"\n>>> PROD 格式欄位:")
print(near_prod.columns.tolist())

# 顯示範例資料
print(f"\n>>> Near Term 範例 (前 3 筆):")
print(near_prod.head(3).to_string())

# 驗證 Outlier 格式
print(f"\n>>> Outlier 標記格式驗證:")
print(f"    c.last_outlier 唯一值: {near_prod['c.last_outlier'].unique()[:10]}")
print(f"    p.last_outlier 唯一值: {near_prod['p.last_outlier'].unique()[:10]}")

print(f"\n>>> 輸出檔案:")
print(f"    output/step0_Near_PROD格式_前30時點.csv")
print(f"    output/step0_Next_PROD格式_前30時點.csv")

print("\n" + "=" * 60)
print("測試完成!")
print("=" * 60)
