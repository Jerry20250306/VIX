import os
import sys

def main():
    print("Building step0_process_quotes.py...")
    # Read first file
    with open('step0_valid_quotes.py', 'r', encoding='utf-8') as f:
        src1 = f.read()
    # Read second file
    with open('step0_2_ema_calculation.py', 'r', encoding='utf-8') as f:
        src2 = f.read()

    # Extract useful parts from 1
    # We want everything except generate_integrated_html_report, AND replace the bottom part 
    parts = src1.split('def generate_integrated_html_report(')
    part1_header = parts[0]
    
    parts_main = src1.split('def main(')
    main_func_body = 'def main(' + parts_main[1]
    
    # Extract useful parts from 2
    part2_body = src2.replace('import pandas as pd', '#')
    part2_body = part2_body.replace('import numpy as np', '#')
    part2_funcs = part2_body.split('if __name__ ==')[0]
    
    with open('step0_process_quotes.py', 'w', encoding='utf-8') as f:
        f.write("# 合併處理腳本: step0_process_quotes.py\n")
        f.write(part1_header)
        f.write("\n")
        f.write("# 原 step0_2_ema_calculation.py 的函數\n")
        f.write(part2_funcs)
        f.write("\n")
        # Write modified main function logic
        
        main_mod = """
def main(target_date=None, process_all_times=True, target_time=None, max_time_points=None, end_time=None):
    from vix_utils import get_vix_config
    config = get_vix_config(target_time if (target_time and len(target_time) == 8) else target_date)
    final_date = config["target_date"]
    raw_dir, prod_dir = config["raw_dir"], config["prod_dir"]
    
    if not raw_dir or not prod_dir:
        print("錯誤: 無法解析資料路徑")
        return
        
    loader = RawDataLoader(raw_dir, final_date)
    near_ticks, next_ticks, terms = loader.load_and_filter()
    if near_ticks is None: return
    
    tasks = [('Near', near_ticks, f"NearPROD_{final_date}.tsv"),
             ('Next', next_ticks, f"NextPROD_{final_date}.tsv")]
             
    for term_name, ticks, prod_filename in tasks:
        print(f"\\n>>> 處理 {term_name} Term")
        prod_path = os.path.join(prod_dir, prod_filename)
        scheduler = SnapshotScheduler(prod_path)
        schedule, initial_sys_id, prod_strikes = scheduler.load_schedule()
        
        time_points = schedule['orig_time_str'].tolist()
        print(f"  共 {len(time_points)} 個時間點")
        
        schedule_times = []
        for time_str in time_points:
            target_row = schedule[schedule['orig_time_str'] == time_str].iloc[0]
            schedule_times.append((target_row['time_obj'], target_row['sys_id'], time_str))
            
        reconstructor = SnapshotReconstructor(ticks)
        snapshot_df = reconstructor.reconstruct_all(schedule_times, initial_sys_id, prod_strikes=prod_strikes)
        
        # Mapping rules
        snapshot_df['Term'] = term_name
        snapshot_df = snapshot_df.rename(columns={
            'My_Last_Bid': 'Q_last_Bid', 'My_Last_Ask': 'Q_last_Ask',
            'My_Last_SysID': 'Q_last_SysID', 'My_Last_Time': 'Q_last_Time',
            'My_Min_Bid': 'Q_min_Bid', 'My_Min_Ask': 'Q_min_Ask',
            'My_Min_Spread': 'Q_min_Spread', 'My_Min_SysID': 'Q_min_SysID',
        })
        
        snapshot_df['Q_last_Spread'] = np.where(snapshot_df['Q_last_Bid'].notna() & snapshot_df['Q_last_Ask'].notna(), snapshot_df['Q_last_Ask'] - snapshot_df['Q_last_Bid'], np.nan)
        
        qlast_valid = snapshot_df['Q_last_Bid'].notna() & snapshot_df['Q_last_Ask'].notna() & (snapshot_df['Q_last_Bid'] >= 0) & (snapshot_df['Q_last_Ask'] > 0) & (snapshot_df['Q_last_Ask'] > snapshot_df['Q_last_Bid'])
        qmin_valid = snapshot_df['Q_min_Bid'].notna() & snapshot_df['Q_min_Ask'].notna() & (snapshot_df['Q_min_Bid'] >= 0) & (snapshot_df['Q_min_Ask'] > 0) & (snapshot_df['Q_min_Ask'] > snapshot_df['Q_min_Bid'])
        
        snapshot_df['Q_last_Valid'] = qlast_valid
        snapshot_df['Q_min_Valid'] = qmin_valid
        
        snapshot_df['Q_Last_Valid_Bid'] = np.where(qlast_valid, snapshot_df['Q_last_Bid'], "null")
        snapshot_df['Q_Last_Valid_Ask'] = np.where(qlast_valid, snapshot_df['Q_last_Ask'], "null")
        snapshot_df['Q_Last_Valid_Spread'] = np.where(qlast_valid, snapshot_df['Q_last_Ask'] - snapshot_df['Q_last_Bid'], "null")
        snapshot_df['Q_Last_Valid_Mid'] = np.where(qlast_valid, (snapshot_df['Q_last_Bid'] + snapshot_df['Q_last_Ask']) / 2, "null")
        
        snapshot_df['Q_Min_Valid_Bid'] = np.where(qmin_valid, snapshot_df['Q_min_Bid'], "null")
        snapshot_df['Q_Min_Valid_Ask'] = np.where(qmin_valid, snapshot_df['Q_min_Ask'], "null")
        snapshot_df['Q_Min_Valid_Spread'] = np.where(qmin_valid, snapshot_df['Q_min_Ask'] - snapshot_df['Q_min_Bid'], "null")
        snapshot_df['Q_Min_Valid_Mid'] = np.where(qmin_valid, (snapshot_df['Q_min_Bid'] + snapshot_df['Q_min_Ask']) / 2, "null")
        
        report_cols = [
            'Term', 'Time', 'Snapshot_SysID', 'Strike', 'CP',
            'Q_last_Bid', 'Q_last_Ask', 'Q_last_Spread', 'Q_last_SysID', 'Q_last_Time', 'Q_last_Valid',
            'Q_Last_Valid_Bid', 'Q_Last_Valid_Ask', 'Q_Last_Valid_Spread', 'Q_Last_Valid_Mid',
            'Q_min_Bid', 'Q_min_Ask', 'Q_min_Spread', 'Q_min_SysID', 'Q_min_Valid',
            'Q_Min_Valid_Bid', 'Q_Min_Valid_Ask', 'Q_Min_Valid_Spread', 'Q_Min_Valid_Mid',
        ]
        combined_df = snapshot_df[[c for c in report_cols if c in snapshot_df.columns]]
        
        # == 合併運算: 呼叫 EMA & Outlier ==
        result_with_ema = add_ema_and_outlier_detection(combined_df, term_name)
        
        out_path = os.path.join("output", f"驗證{final_date}_{term_name}PROD.csv")
        save_prod_format(result_with_ema, out_path, snapshot_sysid_col='Snapshot_SysID', date_val=final_date)

if __name__ == '__main__':
    import sys
    args = {}
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        args['target_date'] = sys.argv[1]
    main(**args)
"""
        f.write(main_mod)

if __name__ == "__main__":
    main()
