import os
import argparse
from datetime import datetime, timedelta
import subprocess

def run_command(cmd, desc):
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 執行: {desc}")
    print(f"> {cmd}")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"[!] {desc} 執行失敗 (Exit Code: {result.returncode})")
        return False
    return True

def main():
    parser = argparse.ArgumentParser(description="VIX Step 1 批次計算與驗證")
    parser.add_argument("--start", type=str, required=True, help="開始日期 (YYYYMMDD)")
    parser.add_argument("--end", type=str, required=True, help="結束日期 (YYYYMMDD)")
    args = parser.parse_args()
    
    start_date = datetime.strptime(args.start, "%Y%m%d")
    end_date = datetime.strptime(args.end, "%Y%m%d")
    
    current_date = start_date
    summary = []
    
    while current_date <= end_date:
        date_str = current_date.strftime("%Y%m%d")
        
        prod_path = os.path.join("資料來源", date_str)
        if not os.path.exists(prod_path):
            print(f"[SKIP] {date_str}: 找不到 PROD 資料夾")
            summary.append((date_str, "Skipped"))
            current_date += timedelta(days=1)
            continue
            
        print(f"\n{'='*60}")
        print(f"處理日期: {date_str}")
        print(f"{'='*60}")
        
        success = True
        
        # 1. 執行 Step 1
        cmd_step1 = f"python -u step1_vix_calc.py --date {date_str}"
        if not run_command(cmd_step1, f"Step 1 計算 ({date_str})"):
            success = False
            
        # 2. 執行 驗證
        verify_ok = False
        if success:
            cmd_verify = f"python validation/verify_step1.py {date_str}"
            result = subprocess.run(cmd_verify, shell=True, capture_output=True, text=True)
            print(result.stdout)
            if result.returncode == 0 and "[PASS]" in result.stdout:
                verify_ok = True
                
        if verify_ok:
            summary.append((date_str, "Passed"))
        else:
            summary.append((date_str, "Failed"))
            
        current_date += timedelta(days=1)
        
    print("\n" + "="*60)
    print("批次執行完成: Step 1 總結報告")
    print("="*60)
    for row in summary:
        print(f"{row[0]} | Status: {row[1]}")

if __name__ == "__main__":
    main()
