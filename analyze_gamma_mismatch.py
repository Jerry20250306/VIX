"""
深入分析 Gamma 不一致的案例
"""
import pandas as pd
pd.set_option('display.width', 400)
pd.set_option('display.max_columns', None)

# 載入資料
prod = pd.read_csv(r'c:\AGY\VIX\VIX\資料來源\20251231\NearPROD_20251231.tsv', sep='\t', dtype=str)
calc = pd.read_csv('step0_full_output_Near_前10個.csv')

print("=" * 80)
print("分析 084515 時間點的 Gamma 不一致案例")
print("=" * 80)

# 找一個不一致的例子: Strike=28300, Call, Time=084515
# PROD gamma=2.0, 我們的 gamma=1.5

# 先看 084500 的資料 (前一個時間點)
prod_084500 = prod[prod['time'] == '084500']
print(f"\n084500 時間點 PROD 有多少筆: {len(prod_084500)}")

# 找 Strike=28300 的 084500 資料
prod_28300_084500 = prod_084500[prod_084500['strike'] == '28300']
print(f"084500 Strike=28300 的 PROD 資料: {len(prod_28300_084500)} 筆")

if len(prod_28300_084500) > 0:
    print("有資料:")
    print(prod_28300_084500[['time', 'strike', 'c.bid', 'c.ask', 'c.gamma']].to_string(index=False))
else:
    print("沒有資料! 這可能是 PROD 第一次出現的序列")

# 看 084515 的資料
prod_084515 = prod[prod['time'] == '084515']
prod_28300_084515 = prod_084515[prod_084515['strike'] == '28300']
print(f"\n084515 Strike=28300 的 PROD 資料:")
print(prod_28300_084515[['time', 'strike', 'c.bid', 'c.ask', 'c.last_bid', 'c.last_ask', 'c.gamma']].to_string(index=False))

# 分析: 對於 PROD 而言，如果這是某個序列第一次出現的時間點，gamma 邏輯可能不同
print("\n" + "=" * 80)
print("假設分析")
print("=" * 80)
print("""
可能的情況:
1. 對 PROD 而言，084515 是每個序列的「第一筆」
2. 第一筆時，PROD 使用 gamma=2.0（不管價格變化）
3. 而我們的程式在 084515 已經有 Q_hat_Mid_t-1（來自 084500）

但實際上 084500 在 PROD 中沒有任何 strike 資料！
這表示 084515 是 PROD 的「第一個快照時間點」
""")

# 確認一下 084500 是否真的沒有資料
print("\n" + "=" * 80)
print("確認 084500 在 PROD 中的狀態")
print("=" * 80)

print(f"PROD 084500 的筆數: {len(prod_084500)}")
print(f"PROD 084500 有 strike 的筆數: {len(prod_084500[prod_084500['strike'].notna()])}")

# 查看我們在 084500 的資料
calc_084500 = calc[calc['Time'] == 84500]
print(f"\n我們的 084500 筆數: {len(calc_084500)}")
print(f"我們的 084500 有 Q_hat_Mid 的筆數: {len(calc_084500[calc_084500['Q_hat_Mid'].notna()])}")

# 查看我們 Strike=28300 Call 在 084500 和 084515 的狀態
print("\n" + "=" * 80)
print("Strike=28300 Call 的計算狀態")
print("=" * 80)

calc_28300_call = calc[(calc['Strike'] == 28300) & (calc['CP'] == 'Call')].sort_values('Time')
print(calc_28300_call[['Time', 'Q_hat_Bid', 'Q_hat_Ask', 'Q_hat_Mid', 'Q_Last_Valid_Mid', 'Q_Last_Valid_Gamma', 'Gamma_Process']].head(5).to_string(index=False))

print("\n" + "=" * 80)
print("結論")
print("=" * 80)
print("""
問題根源:
- PROD 在 084500 沒有輸出資料，084515 是 PROD 的「第一筆」
- 所以 PROD 在 084515 使用 gamma=2.0（第一筆的預設值）

- 但我們的程式在 084500 就開始計算了
- 所以 084515 時我們已經有 Q_hat_Mid_t-1
- 因此我們根據 Mid 比較結果來決定 gamma

解決方案:
- 需要確認 PROD 的「第一筆」判斷邏輯
- 可能需要檢查 Q_hat_t-1 是否有實際值（不只是看是否為 null）
""")
