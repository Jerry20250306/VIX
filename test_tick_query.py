import sys
import os
import json

# Add Viewer directory to path
sys.path.append(os.path.join(os.getcwd(), 'Viewer'))

from tick_parser import TickLoader

def main():
    loader = TickLoader(os.path.join(os.getcwd(), '資料來源'))
    
    # 測試 20251202, 13800 Put
    # SysID: 4867710
    # Prev_SysID: 4822162
    
    result = loader.query(
        date='20251202',
        term='Near', 
        strike=13800,
        cp='Put',
        sys_id='4867710',
        prev_sys_id='4822162'
    )
    
    if 'error' in result:
        print("Error:", result['error'])
    else:
        print(f"Prod ID: {result['prod_id']}")
        print(f"Current Range: {result['current_interval']['sys_id_range']}")
        print(f"Current Count: {result['current_interval']['count']}")
        print("Ticks (first 3):")
        for t in result['current_interval']['ticks'][:3]:
            print(t)

if __name__ == "__main__":
    main()
