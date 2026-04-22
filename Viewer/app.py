from flask import Flask, render_template, jsonify, request
import os
import sys
import pandas as pd
from data_loader import DiffLoader, ProdLoader, SigmaDiffLoader
from tick_parser import TickLoader
from alert_loader import AlertLoader


# 設定 template 和 static 資料夾路徑
# 為了將來打包 exe，需要動態判斷路徑
if getattr(sys, 'frozen', False):
    template_folder = os.path.join(sys._MEIPASS, 'templates')
    static_folder = os.path.join(sys._MEIPASS, 'static')
    app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
else:
    app = Flask(__name__)

# 專案根目錄 (VIX/)
if getattr(sys, 'frozen', False):
    import os
    BASE_DIR = os.path.dirname(sys.executable)
else:
    PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__)) # Viewer/
    BASE_DIR = os.path.dirname(PROJECT_ROOT) # VIX/

# 初始化 Loader
diff_loader = DiffLoader(os.path.join(BASE_DIR, "output"))
prod_loader = ProdLoader(os.path.join(BASE_DIR, "output"), os.path.join(BASE_DIR, "資料來源"))
tick_loader = TickLoader(os.path.join(BASE_DIR, "資料來源"))
sigma_diff_loader = SigmaDiffLoader(os.path.join(BASE_DIR, "資料來源"), os.path.join(BASE_DIR, "output"))
alert_loader = AlertLoader(os.path.join(BASE_DIR, "資料來源"))

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
        
        column = request.args.get("column") # 新增篩選參數
        
        # 取得摘要（快速，不分頁）
        summary_data = diff_loader.get_summary(date, prod_loader=prod_loader)
        
        # 取得分頁資料
        page_data = diff_loader.get_page(date, page, per_page, column=column)
        
        return jsonify({
            "date": date,
            **summary_data,
            **page_data
        })
    except FileNotFoundError:
        return jsonify({"error": "找不到該日期的差異報告"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/diff_full/<date>")
def get_diff_full(date):
    """取得完整計算資料（每筆含差異標記），用於差異清單頁底部的完整資料表"""
    try:
        term     = request.args.get("term", "Near")
        page     = request.args.get("page", 1, type=int)
        per_page = min(request.args.get("per_page", 200, type=int), 1000)
        filter_cp     = request.args.get("cp")        # "Call" / "Put" / None
        filter_strike = request.args.get("strike")    # "28000" / None
        filter_time   = request.args.get("time_int")  # "84515" / None

        # 嘗試載入差異 df，若不存在則傳 None（仍回傳完整資料，只是不標記差異）
        try:
            diff_df = diff_loader._load_df(date)
        except FileNotFoundError:
            diff_df = None

        result = prod_loader.get_full_data(
            date=date, term=term, page=page, per_page=per_page,
            diff_df=diff_df,
            filter_cp=filter_cp,
            filter_strike=int(filter_strike) if filter_strike else None,
            filter_time=int(filter_time) if filter_time else None,
        )
        return jsonify(result)
    except Exception as e:
        import traceback
        traceback.print_exc()
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
    
    # 手動指定 SysID 範圍 (可選)
    curr_start = request.args.get("curr_start")
    curr_end = request.args.get("curr_end")
    prev_start = request.args.get("prev_start")
    prev_end = request.args.get("prev_end")
    
    if not all([date, term, strike, cp]):
        return jsonify({"error": "缺少參數"}), 400
    
    try:
        result = tick_loader.query(
            date=date,
            term=term,
            strike=int(strike),
            cp=cp,
            sys_id=sys_id or "0",
            prev_sys_id=prev_sys_id if prev_sys_id else None,
            curr_start=curr_start if curr_start else None,
            curr_end=curr_end if curr_end else None,
            prev_start=prev_start if prev_start else None,
            prev_end=prev_end if prev_end else None
        )
        return jsonify(result)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# ===================================================================
# 自由探勘面板專用 API
# ===================================================================

@app.route("/api/explore/options")
def api_explore_options():
    """根據 date+term 動態回傳所有可用的履約價與時間點
    供前端下拉選單使用，避免使用者手動輸入錯誤。
    回傳: {strikes: [20000, 20100, ...], times: [84515, 84530, ...]}
    """
    date = request.args.get("date")
    term = request.args.get("term")
    if not all([date, term]):
        return jsonify({"error": "缺少參數"}), 400
    try:
        sysid_map = prod_loader.build_sysid_map(date, term)
        if not sysid_map:
            return jsonify({"strikes": [], "times": []})

        # 取出所有時間點（已在 sysid_map 中）
        times = sorted(sysid_map.keys())

        # 從 PROD TSV 讀出所有履約價
        import os
        path = os.path.join(prod_loader.source_dir, date, f"{term}PROD_{date}.tsv")
        strikes = []
        if os.path.exists(path):
            df_s = pd.read_csv(path, sep="\t", usecols=["strike"])
            strikes = sorted(df_s["strike"].dropna().astype(int).unique().tolist())

        return jsonify({"strikes": strikes, "times": times})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/explore/sysid_map")
def api_explore_sysid_map():
    """取得 Time→SysID 對照表，供前端將時間轉換為 SysID"""
    date = request.args.get("date")
    term = request.args.get("term")
    if not all([date, term]):
        return jsonify({"error": "缺少參數"}), 400
    try:
        sysid_map = prod_loader.build_sysid_map(date, term)
        # key 轉為 str（JSON 限制）
        return jsonify({"sysid_map": {str(k): v for k, v in sysid_map.items()}})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/explore/ticks_stream")
def api_explore_ticks_stream():
    """連續河流 Tick 查詢，毎筆附帶 LAST/MIN 標記與 E-code"""
    date        = request.args.get("date")
    term        = request.args.get("term")
    strike      = request.args.get("strike")
    cp          = request.args.get("cp")
    time_int    = request.args.get("time_int")  # HMMSS  或 HHMMSS
    prepend_sysid = request.args.get("prepend_sysid")
    append_sysid  = request.args.get("append_sysid")
    lookback      = request.args.get("lookback", 1)
    lookforward   = request.args.get("lookforward", 1)

    if not all([date, term, strike, cp, time_int]):
        return jsonify({"error": "缺少參數: date/term/strike/cp/time_int"}), 400

    try:
        # 建立 SysID 對照表
        sysid_map = prod_loader.build_sysid_map(date, term)
        if not sysid_map:
            return jsonify({"error": f"找不到 {term}PROD_{date}.tsv 或 snapshot_sysID 欄位"}), 404

        # 將 time_int 轉為 center_sysid
        center_sysid = sysid_map.get(int(time_int))
        if center_sysid is None:
            # 找最接近的
            closest = min(sysid_map.keys(), key=lambda k: abs(k - int(time_int)))
            center_sysid = sysid_map[closest]

        result = tick_loader.query_stream(
            date=date,
            term=term,
            strike=int(strike),
            cp=cp,
            sysid_map=sysid_map,
            center_sysid=center_sysid,
            lookback=int(lookback),
            lookforward=int(lookforward),
            prepend_sysid=int(prepend_sysid) if prepend_sysid else None,
            append_sysid=int(append_sysid)   if append_sysid  else None,
        )
        
        # 標記 each snapshot 的 source 與 Outlier 判定結果
        if "snapshots" in result:
            for snap in result["snapshots"]:
                try:
                    ours = prod_loader.get_ours_row(date, term, snap["time_int"], int(strike))
                    prefix = "c." if cp == "Call" else "p."
                    snap["source"] = ours.get(f"{prefix}source")
                    snap["last_outlier"] = ours.get(f"{prefix}last_outlier")
                    snap["min_outlier"] = ours.get(f"{prefix}min_outlier")
                    snap["last_sysID"] = ours.get(f"{prefix}last_sysID")
                    snap["min_sysID"] = ours.get(f"{prefix}min_sysID")
                except Exception:
                    snap["source"] = None
                    snap["last_outlier"] = None
                    snap["min_outlier"] = None
                    snap["last_sysID"] = None
                    snap["min_sysID"] = None

        return jsonify(result)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/vix_trend")
def api_vix_trend():
    """取得特定日期的 VIX 走勢 (09:00:00 以後)"""
    date = request.args.get("date")
    if not date:
        return jsonify({"error": "缺少參數 date"}), 400

    try:
        # 直接利用 sigma_diff_loader 或自行讀取 sigma_YYYYMMDD.tsv
        path = os.path.join(prod_loader.source_dir, date, f"sigma_{date}.tsv")
        if not os.path.exists(path):
             return jsonify({"error": "找不到 sigma 檔案"}), 404

        df = pd.read_csv(path, sep="\t", dtype={"time": str})
        
        # 過濾 090000 以後的資料
        df["time_int"] = df["time"].astype(str).str.zfill(6).astype(int)
        df = df[df["time_int"] >= 90000].copy()
        
        # 只保留需要的欄位
        df = df[["time", "vix", "ori_vix"]].copy()
        df = df.astype(object).where(pd.notnull(df), None)
        
        
        return jsonify({"rows": df.to_dict(orient="records")})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/api/alerts")
def get_alerts():
    """取得特定日期所有 Alert 的時間點列表及解析後的完整內容"""
    date = request.args.get("date")
    if not date:
        return jsonify({"error": "缺少參數 date"}), 400

    try:
        alerts = alert_loader.get_alerts_by_date(date)
        return jsonify({
            "date": date,
            "alerts": alerts
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/api/snapshot")
def api_snapshot():
    """取得特定日期與時間點的 Call/Put 快照與貢獻度 (Left/Right 分開)"""
    date = request.args.get("date")
    time_int = request.args.get("time_int")
    
    if not all([date, time_int]):
        return jsonify({"error": "缺少參數"}), 400
        
    try:
        result = prod_loader.get_snapshot_with_contrib(date, time_int)
        return jsonify(result)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/explore/calc_trace")
def api_explore_calc_trace():
    """算式還原：取得指定時間點的 EMA 計算中間參數"""
    date     = request.args.get("date")
    term     = request.args.get("term")
    time_int = request.args.get("time_int")
    strike   = request.args.get("strike")

    if not all([date, term, time_int, strike]):
        return jsonify({"error": "缺少參數"}), 400

    try:
        trace = prod_loader.get_calc_trace(date, term, int(time_int), int(strike))
        return jsonify(trace)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/explore/find_diff")
def api_explore_find_diff():
    """在指定商品中，左右指定時間點尋找上/一個差異"""
    date         = request.args.get("date")
    term         = request.args.get("term")
    strike       = request.args.get("strike")
    cp           = request.args.get("cp")
    current_time = request.args.get("current_time")  # HMMSS
    direction    = request.args.get("direction", "next")  # next 或 prev

    if not all([date, term, strike, cp, current_time]):
        return jsonify({"error": "缺少參數"}), 400

    try:
        # 讀入 diff CSV
        df = diff_loader._load_df(date)

        # 筛選指定商品
        mask = (
            (df["Term"].astype(str) == term) &
            (df["Strike"].astype(str) == str(strike)) &
            (df["CP"].astype(str) == cp)
        )
        item_df = df[mask].copy()
        if item_df.empty:
            return jsonify({"found": False, "message": "未找到該商品的差異記錄"})

        item_df["Time"] = pd.to_numeric(item_df["Time"], errors="coerce")
        item_df = item_df.dropna(subset=["Time"]).sort_values("Time")

        cur = int(current_time)
        if direction == "next":
            found = item_df[item_df["Time"] > cur]
            if found.empty:
                return jsonify({"found": False})
            row = found.iloc[0]
        else:
            found = item_df[item_df["Time"] < cur]
            if found.empty:
                return jsonify({"found": False})
            row = found.iloc[-1]

        return jsonify({
            "found": True,
            "time_int": int(row["Time"]),
            "column": str(row["Column"]),
            "ours": row.get("Ours"),
            "prod": row.get("PROD"),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/sigma_diff")
def get_sigma_diff():
    """取得 Sigma/VIX 的比對結果"""
    date = request.args.get("date")
    if not date:
        return jsonify({"error": "缺少 date 參數"}), 400
    
    try:
        result = sigma_diff_loader.get_diff(date)
        return jsonify(result)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    import socket
    import threading
    import webbrowser
    import time
    
    def find_free_port(start=8080, end=8100):
        for p in range(start, end):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                if s.connect_ex(('localhost', p)) != 0:
                    return p
        raise RuntimeError("找不到可用的 port（8080-8099）")
        
    host = os.environ.get("FLASK_HOST", "127.0.0.1")
    port = find_free_port(start=8080)
    
    url = f"http://{host if host != '0.0.0.0' else 'localhost'}:{port}"
    
    print(f"專案根目錄: {BASE_DIR}")
    print(f"啟動 Viewer... 請用瀏覽器開啟 {url}")
    if host == "0.0.0.0":
        print(f"提示：目前綁定 0.0.0.0，同網域的其他電腦可透過您的 IP 連入。")
        
    def open_browser():
        time.sleep(1.5)
        webbrowser.open(url)
        
    threading.Thread(target=open_browser, daemon=True).start()
    app.run(host=host, debug=False, port=port)
