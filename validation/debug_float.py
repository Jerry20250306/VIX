"""驗證浮點數精度問題"""
import numpy as np

# q_last_at_prev: bid=7.4, ask=7.8
prev_spread = 7.8 - 7.4
print(f"q_last_at_prev spread: {prev_spread}")
print(f"repr: {repr(prev_spread)}")

# 區間 tick: bid=7.3, ask=7.7
tick_spread = 7.7 - 7.3
print(f"\n區間 tick spread: {tick_spread}")
print(f"repr: {repr(tick_spread)}")

# 比較
print(f"\nprev_spread == tick_spread: {prev_spread == tick_spread}")
print(f"prev_spread < tick_spread: {prev_spread < tick_spread}")
print(f"prev_spread - tick_spread: {prev_spread - tick_spread}")
print(f"abs差: {abs(prev_spread - tick_spread)}")

# 模擬 Q_Min 邏輯
min_spread = prev_spread  # 初始化為 prev
min_seqno = 3882456
s = tick_spread  # 區間 tick
seq = 4102077

print(f"\n=== 模擬 Q_Min 邏輯 ===")
print(f"s = {repr(s)}")
print(f"min_spread = {repr(min_spread)}")
print(f"s < min_spread: {s < min_spread}")
print(f"s == min_spread: {s == min_spread}")
print(f"seq > min_seqno: {seq > min_seqno}")

if s < min_spread or (s == min_spread and seq > min_seqno):
    print("→ 會更新！")
else:
    print("→ 不會更新！")
    if s > min_spread:
        print(f"  原因: s ({s}) > min_spread ({min_spread})，spread 更大")
    elif s == min_spread:
        print(f"  原因: spread 相同但 seqno 不大（不應該發生）")
    else:
        print(f"  原因: 不明")
