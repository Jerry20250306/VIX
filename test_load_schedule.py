# -*- coding: utf-8 -*-
"""Quick test for load_schedule with prod_strikes"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from reconstruct_order_book import SnapshotScheduler

prod_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                         '資料來源', '20251201', 'NearPROD_20251201.tsv')

print(f"Testing: {os.path.basename(prod_path)}")
scheduler = SnapshotScheduler(prod_path)
result = scheduler.load_schedule()

print(f"\nReturn tuple length: {len(result)}")
schedule, init_id, prod_strikes = result

print(f"Schedule rows (time points): {len(schedule)}")
print(f"Initial SysID: {init_id}")
print(f"Prod Strikes count: {len(prod_strikes)}")
print(f"Expected rows per time: {len(prod_strikes) * 2}")
print(f"First 5 strikes: {prod_strikes[:5]}")
print(f"Last 5 strikes: {prod_strikes[-5:]}")

# Verify: total PROD data rows should be time_points * strikes
expected_data_rows = len(schedule) * len(prod_strikes)
print(f"\nExpected total PROD rows (time_points * strikes): {expected_data_rows}")
# File has 180003 lines: 1 header + 1 start row + data rows
# data rows = 180001, time_points * strikes should match
print(f"Actual PROD file data rows (180003 - 2 = 180001): 180001")
if expected_data_rows == 180001:
    print("PASS: Row count matches!")
else:
    print(f"MISMATCH: expected {expected_data_rows}, actual 180001")

print("\nDone!")
