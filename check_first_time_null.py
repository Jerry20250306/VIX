import pandas as pd

# 檢查第一個時間點 084515，無報價的情況下 outlier 是什麼
df = pd.read_csv('資料來源/20251201/NearPROD_20251201.tsv', sep='\t', dtype=str)

# 找第一個時間點
first_time = df[df['time'] == '084515']

# 找無報價的 (c.last_bid = 0 且 c.last_ask = 0)
no_quote = first_time[(first_time['c.last_bid'] == '0') & (first_time['c.last_ask'] == '0')]

if not no_quote.empty:
    print(f"找到 {len(no_quote)} 筆第一個時間點無 Call 報價的資料")
    print("\n前 5 筆範例:")
    for idx, row in no_quote.head(5).iterrows():
        print(f"Strike {row['strike']}: c.last_outlier = '{row['c.last_outlier']}'")
else:
    print("084515 所有 Strike 都有 Call 報價")

# 同樣檢查 Put
no_quote_put = first_time[(first_time['p.last_bid'] == '0') & (first_time['p.last_ask'] == '0')]

if not no_quote_put.empty:
    print(f"\n找到 {len(no_quote_put)} 筆第一個時間點無 Put 報價的資料")
    print("\n前 5 筆範例:")
    for idx, row in no_quote_put.head(5).iterrows():
        print(f"Strike {row['strike']}: p.last_outlier = '{row['p.last_outlier']}'")
else:
    print("084515 所有 Strike 都有 Put 報價")
