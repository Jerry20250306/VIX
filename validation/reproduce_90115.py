"""
重現 09:01:15 Strike 32500 (Put) 的 Q_Min 計算邏輯
"""
import pandas as pd
import numpy as np
import sys
import os
from datetime import datetime, timedelta

# Mock SnapshotReconstructor logic
class MockReconstructor:
    def __init__(self, ticks):
        self.ticks = ticks
        # Manually construct datetime with correct date
        base_str = "20251231"
        self.ticks['timestamp'] = pd.to_datetime(base_str + self.ticks['time'].astype(str), format='%Y%m%d%H%M%S%f')
        
    def check_valid_quote(self, bid, ask):
        try:
            bid = float(bid)
            ask = float(ask)
        except:
            return False
            
        if bid < 0: return False
        if ask <= bid: return False
        return True

    def reconstruct(self, target_time_str):
        # target_time_str like "090115"
        base_date = datetime(2025, 12, 31)
        target_time = datetime.strptime(target_time_str, "%H%M%S").replace(
            year=base_date.year, month=base_date.month, day=base_date.day)
            
        start_time = target_time - timedelta(seconds=15)
        
        # 1. Find Q_Last at start_time
        past_ticks = self.ticks[self.ticks['timestamp'] <= start_time]
        q_last_start = None
        q_last_start_valid = False
        
        # Replay to find last validity
        for _, row in past_ticks.iterrows():
            valid = self.check_valid_quote(row['bid'], row['ask'])
            if valid:
                q_last_start = row
                q_last_start_valid = True
            else:
                # If invalid, does it clear previous valid?
                # YES. In step0, we maintain current state.
                q_last_start = row
                q_last_start_valid = False
                
        # 2. Find ticks in window
        window_ticks = self.ticks[
            (self.ticks['timestamp'] > start_time) & 
            (self.ticks['timestamp'] <= target_time)
        ]
        
        candidates = []
        
        # Add start state if valid
        if q_last_start_valid and q_last_start is not None:
            bid = float(q_last_start['bid'])
            ask = float(q_last_start['ask'])
            candidates.append({
                'bid': bid,
                'ask': ask,
                'spread': ask - bid,
                'seq': q_last_start['seq'],
                'source': 'Initial'
            })
            
        # Add window ticks
        for _, row in window_ticks.iterrows():
            valid = self.check_valid_quote(row['bid'], row['ask'])
            if valid:
                bid = float(row['bid'])
                ask = float(row['ask'])
                candidates.append({
                    'bid': bid,
                    'ask': ask,
                    'spread': ask - bid,
                    'seq': row['seq'],
                    'source': 'Window'
                })
        
        # Determine Q_Min
        if not candidates:
            return None
            
        # Sort by Spread (ASC), then Seq (DESC - newest first) (?)
        # Wait, tie-breaking: "若 Q_Latest 價差等於 Q_Min 價差，優先使用 Q_Latest"
        # Q_Latest here means "Latest VALID quote in window OR initial"
        
        # Current logic in reconstruct_order_book.py might be diff.
        # Let's see what we find here.
        
        # Find min spread
        min_spread = min(c['spread'] for c in candidates)
        
        # Filter min spread candidates
        best_candidates = [c for c in candidates if abs(c['spread'] - min_spread) < 1e-9]
        
        # Select winner
        # If Q_Last (at target_time) is in best_candidates, pick it.
        # Who is Q_Last at target_time?
        # It is the last valid quote processed.
        
        # Let's deduce Q_Last at target_time
        # Replay window ticks on top of start state
        current_valid_q = q_last_start if q_last_start_valid else None
        
        for _, row in window_ticks.iterrows():
            valid = self.check_valid_quote(row['bid'], row['ask'])
            if valid:
                current_valid_q = row
            else:
                current_valid_q = None # Invalid clears it?
                
        # If current_valid_q is not None, checking if it is in candidates
        # ... matches min_spread
        
        print(f"Time: {target_time_str}")
        print(f"Start Time: {start_time}")
        print(f"Q_Last @ Start: {q_last_start['bid']}/{q_last_start['ask']} (Valid={q_last_start_valid}, Seq={q_last_start['seq']})")
        
        print(f"Window Ticks: {len(window_ticks)}")
        for _, row in window_ticks.iterrows():
            print(f"  Tick: {row['timestamp'].time()} {row['bid']}/{row['ask']} (Seq={row['seq']})")
            
        print(f"Candidates: {len(candidates)}")
        for c in candidates:
            print(f"  Can: {c['bid']}/{c['ask']} Spread={c['spread']} Src={c['source']} Seq={c['seq']}")
            
        print(f"Min Spread: {min_spread}")
        
        return best_candidates

# Ticks data
data = [
    {'time': '090050476000', 'bid': 0.0, 'ask': 3640.0, 'seq': 1151106},
    {'time': '090101189000', 'bid': 0.0, 'ask': 0.0, 'seq': 1185058},
    {'time': '090114307000', 'bid': 0.0, 'ask': 3650.0, 'seq': 1214277},
    {'time': '090115100000', 'bid': 3580.0, 'ask': 3650.0, 'seq': 1215532},
]
df = pd.DataFrame(data)

rec = MockReconstructor(df)
rec.reconstruct("090115")
