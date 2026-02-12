"""
VIX 計算批次執行與驗證腳本 (Batch Runner)
=========================================
功能：
1. 指定日期範圍，逐日執行 Near/Next Term 的 VIX 計算 (Step 0 ~ Step 2)
2. 每日跑完後自動進行數值驗證 (Verify Parity)
3. 紀錄每一步驟的執行狀態與一致率

使用方式：
    python run_batch.py --start 20251201 --end 20251231

相依性：
    - step0_valid_quotes.py (Step 0 & 1)
    - step0_2_ema_calculation.py (Step 2)
    - validation/quick_verify_numeric.py (Verification)
"""
import subprocess
import os
import sys
import argparse
from datetime import datetime, timedelta
import pandas as pd

def run_command(cmd, desc):
    """執行外部指令並檢查回傳值"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {desc}...")
    try:
        # 使用 subprocess.run capture_output=False 讓輸出直接顯示在螢幕上
        # check=True 會在 exit code != 0 時拋出 CalledProcessError
        subprocess.run(cmd, shell=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"[Error] {desc} 失敗 (Exit Code: {e.returncode})")
        return False

def verify_date_full(date_str):
    """呼叫 verify_full_day.py 進行全天驗證"""
    # verify_full_day.py 一次驗證 Near 和 Next
    cmd = f"python validation/verify_full_day.py {date_str}"
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 驗證 {date_str} (Near & Next)...")
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        output = result.stdout
        
        # 檢查關鍵字
        if "恭喜！未發現任何差異" in output:
            print(f"[PASS] {date_str} 全天驗證通過 (100% 一致)")
            return True, True, output # success, near_ok, next_ok
        else:
            print(f"[FAIL] {date_str} 驗證失敗/有差異")
            # 嘗試列出差異摘要
            summary_lines = []
            for line in output.splitlines():
                if "發現差異" in line or "錯誤" in line:
                    print(f"   {line.strip()}")
            return False, False, output
            
    except Exception as e:
        print(f"[Error] 驗證腳本執行錯誤: {e}")
        return False, False, str(e)

def main():
    parser = argparse.ArgumentParser(description="VIX 批次計算與驗證")
    parser.add_argument("--start", type=str, required=True, help="開始日期 (YYYYMMDD)")
    parser.add_argument("--end", type=str, required=True, help="結束日期 (YYYYMMDD)")
    parser.add_argument("--stop-on-error", action="store_true", help="遇到錯誤是否停止 (預設: 繼續跑下一天)")
    
    args = parser.parse_args()
    
    start_date = datetime.strptime(args.start, "%Y%m%d")
    end_date = datetime.strptime(args.end, "%Y%m%d")
    
    current_date = start_date
    summary = []
    
    while current_date <= end_date:
        date_str = current_date.strftime("%Y%m%d")
        print(f"\n{'='*60}")
        print(f"[START] 開始處理日期: {date_str}")
        print(f"{'='*60}")
        
        # 檢查該日期的資料是否存在
        # 簡單檢查 PROD 目錄是否存在即可 (雖然程式會自己 check)
        prod_path = os.path.join("資料來源", date_str)
        if not os.path.exists(prod_path):
            print(f"[SKIP] 跳過 {date_str}: 找不到 PROD 資料夾 ({prod_path})")
            summary.append({"date": date_str, "status": "Skipped (No Data)"})
            current_date += timedelta(days=1)
            continue
            
        success = True
        
        # 1. 執行 Step 0 & 1 (Near + Next)
        cmd_step0 = f"python step0_valid_quotes.py ALL {date_str}"
        if not run_command(cmd_step0, f"Step 0: 有效報價篩選 ({date_str})"):
            success = False
        
        # 2. 執行 Step 2 (EMA Calculation)
        if success:
            cmd_step2 = f"python step0_2_ema_calculation.py {date_str}"
            # 注意: 如果你的 script 支援參數，可能需要調整
            if not run_command(cmd_step2, f"Step 2: EMA 計算 ({date_str})"):
                success = False
                
        # 3. 驗證 (Near & Next 一併驗證)
        verify_success = False
        if success:
            verify_success, _, _ = verify_date_full(date_str)
            
            if not verify_success:
                success = False
        
        # 紀錄結果
        status = "Passed" if verify_success else "Failed"
        if not success and not verify_success:
            status = "Mismatch" # 執行成功但驗證失敗或執行失敗
        
        summary.append({
            "date": date_str, 
            "status": status,
            "near": "OK" if verify_success else "Check",
            "next": "OK" if verify_success else "Check"
        })
        
        if not success and args.stop_on_error:
            print(f"\n[STOP] 因錯誤停止於 {date_str}")
            break
            
        current_date += timedelta(days=1)

    print(f"\n{'='*60}")
    print("[SUMMARY] 批次執行摘要")
    print(f"{'='*60}")
    print(f"{'Date':<10} | {'Status':<10} | {'Near':<6} | {'Next':<6}")
    print("-" * 40)
    for s in summary:
        print(f"{s['date']:<10} | {s['status']:<10} | {s['near']:<6} | {s['next']:<6}")
    print("-" * 40)

if __name__ == "__main__":
    main()
