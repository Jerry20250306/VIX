"""
查看 084530 和 084715 的 PROD 詳細資訊
"""
import pandas as pd
pd.set_option('display.width', 300)
pd.set_option('display.max_columns', None)

# 載入 PROD
prod = pd.read_csv(r'c:\AGY\VIX\VIX\資料來源\20251231\NearPROD_20251231.tsv', sep='\t', dtype=str)
prod = prod[prod['strike'].notna()]

# 084530 和 084715 的 Strike=28900 詳情
times = ['084530', '084715']
for t in times:
    row = prod[(prod['time']==t) & (prod['strike']=='28900')]
    if not row.empty:
        r = row.iloc[0]
        print(f'=== 時間: {t}, Strike=28900 ===')
        print(f'  snapshot_sysID: {r.get("snapshot_sysID", "N/A")}')
        print(f'  PROD篩選結果: c.bid={r["c.bid"]}, c.ask={r["c.ask"]}')
        print(f'  c.last: bid={r["c.last_bid"]}, ask={r["c.last_ask"]}, sysID={r["c.last_sysID"]}, outlier={r.get("c.last_outlier","N/A")}')
        print(f'  c.min:  bid={r["c.min_bid"]}, ask={r["c.min_ask"]}, sysID={r["c.min_sysID"]}, outlier={r.get("c.min_outlier","N/A")}')
        print(f'  c.ema={r.get("c.ema","N/A")}, c.gamma={r.get("c.gamma","N/A")}')
        print()

# 載入我們的計算結果
calc = pd.read_csv('step0_full_output_Near_前10個.csv')
calc_28900 = calc[(calc['Strike']==28900) & (calc['CP']=='Call')]

print('=== 我們的計算結果 (Strike=28900, Call) ===')
for t in [84530, 84715]:
    row = calc_28900[calc_28900['Time']==t]
    if not row.empty:
        r = row.iloc[0]
        print(f'時間: {t}')
        print(f'  Q_Last_Valid: Bid={r["Q_Last_Valid_Bid"]}, Ask={r["Q_Last_Valid_Ask"]}, Spread={r["Q_Last_Valid_Spread"]}')
        print(f'  Q_Min_Valid:  Bid={r["Q_Min_Valid_Bid"]}, Ask={r["Q_Min_Valid_Ask"]}, Spread={r["Q_Min_Valid_Spread"]}')
        print(f'  EMA={r["EMA"]}, γ_Last={r["Q_Last_Valid_Gamma"]}, γ_Min={r["Q_Min_Valid_Gamma"]}')
        print(f'  Is_Outlier: Q_Last={r["Q_Last_Valid_Is_Outlier"]}, Q_Min={r["Q_Min_Valid_Is_Outlier"]}')
        print(f'  Q_hat: Bid={r["Q_hat_Bid"]}, Ask={r["Q_hat_Ask"]} (來源: {r["Q_hat_Source"]})')
        print()
