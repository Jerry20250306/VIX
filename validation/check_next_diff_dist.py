"""
分析 Next Term 差異的時間分佈
"""
import pandas as pd

prod_df = pd.read_csv(r'資料來源\20251231\NextPROD_20251231.tsv', sep='\t', dtype=str)
our_df = pd.read_csv('output/驗證20251231_NextPROD.csv')

# 格式化
prod_valid = prod_df[prod_df['strike'].notna() & (prod_df['strike'] != '')].copy()
prod_valid['time'] = prod_valid['time'].astype(int)
prod_valid['strike'] = prod_valid['strike'].astype(int)
prod_valid['c.min_bid'] = pd.to_numeric(prod_valid['c.min_bid'], errors='coerce')

our_df['time'] = our_df['time'].astype(int)
our_df['strike'] = our_df['strike'].astype(int)

# 合併
merged = pd.merge(
    our_df, prod_valid[['time', 'strike', 'c.min_bid']],
    on=['time', 'strike'], how='inner', suffixes=('_OUR', '_PROD')
)

# 找差異
diff = (merged['c.min_bid_OUR'].fillna(-999) - merged['c.min_bid_PROD'].fillna(-999)).abs() > 0.01
diff_rows = merged[diff].copy()

print(f"總差異筆數: {len(diff_rows)}")
print("\n時間分佈:")
print(diff_rows['time'].value_counts().head(10))

# 檢查是否所有 0.0/NaN 差異都來自 84515
init_diff = diff_rows[
    (diff_rows['time'] == 84515) & 
    (diff_rows['c.min_bid_PROD'] == 0) & 
    (diff_rows['c.min_bid_OUR'].isna())
]
print(f"\n84515 的 0.0 vs NaN 差異筆數: {len(init_diff)}")
