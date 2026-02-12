from flask import Flask, render_template, jsonify, request
import os
import glob
import re
import sys
from data_loader import DiffLoader, ProdLoader
from tick_parser import TickLoader


# 設定 template 和 static 資料夾路徑
# 為了將來打包 exe，需要動態判斷路徑
if getattr(sys, 'frozen', False):
    template_folder = os.path.join(sys._MEIPASS, 'templates')
    static_folder = os.path.join(sys._MEIPASS, 'static')
    app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
else:
    app = Flask(__name__)

# 專案根目錄 (VIX/)
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__)) # Viewer/
BASE_DIR = os.path.dirname(PROJECT_ROOT) # VIX/

# 初始化 Loader
diff_loader = DiffLoader(os.path.join(BASE_DIR, "output"))
prod_loader = ProdLoader(os.path.join(BASE_DIR, "output"), os.path.join(BASE_DIR, "資料來源"))
tick_loader = TickLoader(os.path.join(BASE_DIR, "資料來源"))

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/dates")
def get_dates():
    """取得 output/ 目錄下所有 validation_diff_YYYYMMDD.csv 的日期"""
    dates = diff_loader.list_available_dates()
    return jsonify({"dates": dates})

@app.route("/api/diff/<date>")
def get_diff(date):
    """取得指定日期的差異報告（分頁）"""
    try:
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 100, type=int)
        
        # 限制 per_page 最大值，避免前端傳入過大值
        per_page = min(per_page, 500)
        
        # 取得摘要（快速，不分頁）
        summary_data = diff_loader.get_summary(date, prod_loader=prod_loader)
        
        # 取得分頁資料
        page_data = diff_loader.get_page(date, page, per_page)
        
        return jsonify({
            "date": date,
            **summary_data,
            **page_data
        })
    except FileNotFoundError:
        return jsonify({"error": "找不到該日期的差異報告"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/prod_row")
def get_prod_row():
    """取得 Ours vs PROD 的差異列細節"""
    date = request.args.get("date")
    time_val = request.args.get("time") # HMMSS
    strike = request.args.get("strike")
    term = request.args.get("term")
    
    if not all([date, time_val, strike, term]):
        return jsonify({"error": "缺少參數"}), 400
        
    try:
        ours = prod_loader.get_ours_row(date, term, time_val, strike)
        prod = prod_loader.get_prod_row(date, term, time_val, strike)
        
        # 比對差異欄位
        diffs = []
        all_keys = set(ours.keys()) | set(prod.keys())
        for col in all_keys:
            val_ours = str(ours.get(col, ""))
            val_prod = str(prod.get(col, ""))
            
            # 簡單比對: 轉字串後不相等
            # 注意: 浮點數精度問題可能導致误判，這裡先做簡單比對
            # 實際應用可能需要 float tolerance
            if col in ours and col in prod:
                try:
                    f_ours = float(val_ours)
                    f_prod = float(val_prod)
                    if abs(f_ours - f_prod) > 1e-5:
                        diffs.append(col)
                except:
                    if val_ours != val_prod:
                        diffs.append(col)
        
        return jsonify({"ours": ours, "prod": prod, "diffs": diffs})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/ticks")
def get_ticks():
    """取得原始 Tick 資料"""
    date = request.args.get("date")
    term = request.args.get("term")
    strike = request.args.get("strike")
    cp = request.args.get("cp")
    sys_id = request.args.get("sys_id")
    prev_sys_id = request.args.get("prev_sys_id")
    
    if not all([date, term, strike, cp, sys_id]):
        return jsonify({"error": "缺少參數"}), 400
    
    try:
        result = tick_loader.query(
            date=date,
            term=term,
            strike=int(strike),
            cp=cp,
            sys_id=sys_id,
            prev_sys_id=prev_sys_id if prev_sys_id else None
        )
        return jsonify(result)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    print(f"專案根目錄: {BASE_DIR}")
    print("啟動 Viewer... 請用瀏覽器開啟 http://localhost:5000")
    app.run(debug=True, port=5000)
