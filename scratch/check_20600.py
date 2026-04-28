import pandas as pd
df = pd.read_csv('output/驗證20251201_NearPROD.csv')
for t in [84615, 84630, 84645, 84700]:
    target = df[(df['time'] == t) & (df['strike'] == 20600)]
    if not target.empty:
        row = target.iloc[0]
        print(f"Time: {t}")
        print(f"  c.min_bid: {row['c.min_bid']}, c.min_ask: {row['c.min_ask']}, sysID: {row['c.min_sysID']}")
        print(f"  c.last_bid: {row['c.last_bid']}, c.last_ask: {row['c.last_ask']}, sysID: {row['c.last_sysID']}")
