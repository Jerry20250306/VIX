"""
查看 Next Term Strike 32500 (Put) 在 09:01:00 ~ 09:01:15 的原始 ticks
"""
import pandas as pd

# 讀取 PROD 原始檔 (Next Term)
# 注意: 雖然 step0_valid_quotes.py 會讀取原始檔，但變數名為 NextPROD_20251231.tsv
prod_file = r'資料來源\20251231\NextPROD_20251231.tsv'

# 為了讀取特定區間，我們得讀全部或分塊讀。這裡檔案不大，直接讀。
df = pd.read_csv(prod_file, sep='\t', dtype=str)

df['time'] = df['time'].astype(int)
df['strike'] = pd.to_numeric(df['strike'], errors='coerce')

# 篩選
target = df[
    (df['strike'] == 32500) & 
    (df['prod_type'] == 'P') & 
    (df['time'] >= 90050) & 
    (df['time'] <= 90130)
]

print(f"=== Raw Ticks (32500 Put) ===")
for i, row in target.iterrows():
    print(f"Index: {i}")
    print(f"  Time: {row['time']}")
    print(f"  Bid: {row['bid']}")
    print(f"  Ask: {row['ask']}")
    print(f"  Seq: {row['seq']}") # 假設有 seq 欄位
    print("-" * 20)
