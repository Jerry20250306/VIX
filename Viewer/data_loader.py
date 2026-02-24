import pandas as pd
import os
import glob
import re

class DiffLoader:

    """讀取 validation_diff_*.csv，帶快取與分頁"""
    
    def __init__(self, output_dir):
        self.output_dir = output_dir
        self._cache = {}  # {date: DataFrame}
    
    def list_available_dates(self):
        """掃描所有可用日期"""
        pattern = os.path.join(self.output_dir, "validation_diff_*.csv")
        files = glob.glob(pattern)
        dates = []
        for f in files:
            match = re.search(r"validation_diff_(\d{8})\.csv", os.path.basename(f))
            if match:
                dates.append(match.group(1))
        return sorted(dates, reverse=True)
    
    def _load_df(self, date):
        """讀取並快取 DataFrame（只讀一次）"""
        if date in self._cache:
            return self._cache[date]
        
        path = os.path.join(self.output_dir, f"validation_diff_{date}.csv")
        if not os.path.exists(path):
            raise FileNotFoundError(f"找不到差異報告: {path}")
        
        # 使用 utf-8-sig 讀取，避免 BOM 問題
        # low_memory=False 避免 mixed type warning
        df = pd.read_csv(path, encoding="utf-8-sig", low_memory=False)
        
        # 處理 NaN → None（JSON 相容）
        # 先轉為 object 型別，避免 float 欄位無法存入 None (會變回 NaN)
        df = df.astype(object).where(pd.notnull(df), None)
        
        self._cache[date] = df
        return df
    
    # 驗證腳本 verify_full_day.py 中定義的所有比對欄位（Last_Outlier 目前未啟用驗證，故不列入）
    ALL_COMPARED_COLUMNS = ['EMA', 'Gamma', 'Q_hat_Bid', 'Q_hat_Ask', 'Q_Last_Bid', 'Q_Last_Ask']
    
    def get_summary(self, date, prod_loader=None):
        """取得摘要統計，包含有差異和無差異的欄位"""
        df = self._load_df(date)
        
        # 有差異的統計 (Term → {Column: count})
        diff_summary = {}
        if "Term" in df.columns:
            for term in df["Term"].unique():
                if term is None:
                    continue
                term_df = df[df["Term"] == term]
                diff_summary[term] = term_df["Column"].value_counts().to_dict()
        
        # 計算每個 Term 的總比對筆數（從 PROD CSV）
        total_per_term = {}
        if prod_loader:
            for term in ["Near", "Next"]:
                path = os.path.join(self.output_dir, f"驗證{date}_{term}PROD.csv")
                if os.path.exists(path):
                    try:
                        # 只讀行數，不需要全部欄位
                        row_count = sum(1 for _ in open(path, encoding="utf-8-sig")) - 1  # 扣掉 header
                        # 每行 = 1 個 strike，Call + Put 各算一筆
                        total_per_term[term] = row_count * 2
                    except:
                        total_per_term[term] = 0
        
        # 組合無差異摘要
        no_diff_summary = {}
        for term in diff_summary.keys():
            diff_cols = diff_summary.get(term, {})
            no_diff = {}
            total = total_per_term.get(term, 0)
            for col in self.ALL_COMPARED_COLUMNS:
                if col not in diff_cols:
                    no_diff[col] = total  # 該欄位完全沒差異
            no_diff_summary[term] = no_diff
        
        # 若有 Term 在 PROD 裡但 diff 裡沒有（表示完全沒差異）
        for term, total in total_per_term.items():
            if term not in diff_summary:
                no_diff_summary[term] = {col: total for col in self.ALL_COMPARED_COLUMNS}
        
        return {
            "total_diffs": len(df),
            "summary": diff_summary,
            "no_diff_summary": no_diff_summary,
            "total_per_term": total_per_term,
            "all_columns": self.ALL_COMPARED_COLUMNS
        }
    
    def get_page(self, date, page=1, per_page=100, column=None):
        """取得分頁資料 (可選篩選特定欄位)"""
        df = self._load_df(date)
        
        # 篩選欄位
        if column and column != "all":
            df = df[df["Column"].astype(str).str.strip() == column.strip()]
        
        total = len(df)
        total_pages = max(1, (total + per_page - 1) // per_page)
        
        # 確保 page 在有效範圍內
        page = max(1, min(page, total_pages))
        
        start = (page - 1) * per_page
        end = min(start + per_page, total)
        
        page_df = df.iloc[start:end]
        
        return {
            "rows": page_df.to_dict(orient="records"),
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": total_pages
        }

class ProdLoader:
    """讀取我們的計算結果和 PROD 資料 (Phase 3)"""
    
    def __init__(self, output_dir, source_dir):
        self.output_dir = output_dir
        self.source_dir = source_dir
        self._cache = {}
    
    def get_ours_row(self, date, term, time_val, strike):
        """取得我們的計算結果中特定 (time, strike) 的一列"""
        key = f"ours_{date}_{term}"
        if key not in self._cache:
            path = os.path.join(self.output_dir, f"驗證{date}_{term}PROD.csv")
            if os.path.exists(path):
                self._cache[key] = pd.read_csv(path, encoding="utf-8-sig")
            else:
                return {}  # 檔案不存在
        
        df = self._cache[key]
        # time_val 格式為 84500 (int) 或 "08:45:00" (str)
        # 我們的 CSV time 是 HH:MM:SS 格式 (str)，但 validation_diff 可能是 int (HMMSS)
        # 需要做轉換
        
        # 簡易轉換：將 CSV 的 "HH:MM:SS" 轉為 HMMSS int 做比對
        if "time_int" not in df.columns:
            df["time_int"] = df["time"].astype(str).str.replace(":", "").astype(int)
            
        row = df[(df["time_int"] == int(time_val)) & (df["strike"] == int(strike))]
        if row.empty:
            return {}
        # 轉為 dict，並將 None 轉為 null (for JSON)
        return row.astype(object).where(pd.notnull(row), None).iloc[0].to_dict()
    
    def get_prod_row(self, date, term, time_val, strike):
        """取得 PROD 中特定 (time, strike) 的一列"""
        key = f"prod_{date}_{term}"
        path = os.path.join(self.source_dir, date, f"{term}PROD_{date}.tsv")
        if os.path.exists(path):
            df = pd.read_csv(path, sep="\t")
        else:
            return {}
        
        row = df[(df["time"] == int(time_val)) & (df["strike"] == int(strike))]
        if row.empty:
            return {}
        return row.astype(object).where(pd.notnull(row), None).iloc[0].to_dict()

    def build_sysid_map(self, date, term):
        """從 PROD TSV 建立 Time→SysID 對照表，供探勘面板使用
        回傳: {time_int: snapshot_sysID, ...} 例如 {84515: 18505, 84530: 18600}
        """
        cache_key = f"sysid_map_{date}_{term}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        path = os.path.join(self.source_dir, date, f"{term}PROD_{date}.tsv")
        if not os.path.exists(path):
            return {}

        df = pd.read_csv(path, sep="\t")

        # 取唯一的 (time, snapshot_sysID) 組合（每個時間點只有一個 SysID）
        if "snapshot_sysID" not in df.columns:
            return {}

        # 只取首次出現（每個 time 的值是固定的）
        time_sysid = df[["time", "snapshot_sysID"]].dropna().drop_duplicates(subset="time")
        result = dict(zip(time_sysid["time"].astype(int), time_sysid["snapshot_sysID"].astype(int)))
        self._cache[cache_key] = result
        return result

    def get_calc_trace(self, date, term, time_int, strike):
        """取得 EMA 算式還原所需的完整中間參數
        回傳 dict，包含 alpha、Q_hat、EMA_prev、計算結果與算式字串。
        """
        time_int = int(time_int)
        strike = int(strike)

        ours = self.get_ours_row(date, term, time_int, strike)
        prod = self.get_prod_row(date, term, time_int, strike)

        # 計算前一個時間點的 EMA（往前推 15 秒）
        prev_time_int = self._prev_time(time_int)
        ours_prev = self.get_ours_row(date, term, prev_time_int, strike) if prev_time_int else {}

        def safe_float(d, key):
            try:
                v = d.get(key)
                return float(v) if v is not None else None
            except:
                return None

        trace = {
            "time": time_int,
            "strike": strike,
            # --- Call 側 EMA ---
            "c_q_hat":       safe_float(ours, "c.bid"),   # Q_hat = Q_hat_Bid (中點可能不同，暫用 bid)
            "c_q_hat_bid":   safe_float(ours, "c.bid"),
            "c_q_hat_ask":   safe_float(ours, "c.ask"),
            "c_ema":         safe_float(ours, "c.ema"),
            "c_ema_prod":    safe_float(prod, "c.ema"),
            "c_ema_prev":    safe_float(ours_prev, "c.ema"),
            "c_source":      ours.get("c.source"),
            "c_last_bid":    safe_float(ours, "c.last_bid"),
            "c_last_ask":    safe_float(ours, "c.last_ask"),
            "c_min_bid":     safe_float(ours, "c.min_bid"),
            "c_min_ask":     safe_float(ours, "c.min_ask"),
            # --- Put 側 EMA ---
            "p_q_hat":       safe_float(ours, "p.bid"),
            "p_q_hat_bid":   safe_float(ours, "p.bid"),
            "p_q_hat_ask":   safe_float(ours, "p.ask"),
            "p_ema":         safe_float(ours, "p.ema"),
            "p_ema_prod":    safe_float(prod, "p.ema"),
            "p_ema_prev":    safe_float(ours_prev, "p.ema"),
            "p_source":      ours.get("p.source"),
            # --- 共用參數 ---
            "alpha":         safe_float(ours, "alpha") or safe_float(prod, "alpha"),
            "snapshot_sysID": safe_float(ours, "snapshot_sysID"),
            "prev_time":     prev_time_int,
        }

        # 組合算式字串（以 Call 側為例）
        a = trace["alpha"]
        c_ema_prev = trace["c_ema_prev"]
        c_q = trace["c_q_hat"]
        if a is not None and c_ema_prev is not None and c_q is not None:
            c_result = c_ema_prev * (1 - a) + c_q * a
            trace["c_formula"] = (f"{c_ema_prev:.4f} × (1 - {a:.6f})"
                                   f" + {c_q:.4f} × {a:.6f} = {c_result:.4f}")
        else:
            trace["c_formula"] = "（參數不足，無法還原）"

        p_ema_prev = trace["p_ema_prev"]
        p_q = trace["p_q_hat"]
        if a is not None and p_ema_prev is not None and p_q is not None:
            p_result = p_ema_prev * (1 - a) + p_q * a
            trace["p_formula"] = (f"{p_ema_prev:.4f} × (1 - {a:.6f})"
                                   f" + {p_q:.4f} × {a:.6f} = {p_result:.4f}")
        else:
            trace["p_formula"] = "（參數不足，無法還原）"

        return trace

    def _prev_time(self, time_int):
        """回傳前一個 15 秒的 time_int（HMMSS / HHMMSS 格式）"""
        try:
            t = int(time_int)
            s = str(t).zfill(6)  # 確保至少 6 碼
            hh, mm, ss = int(s[:-4]), int(s[-4:-2]), int(s[-2:])
            from datetime import datetime, timedelta
            dt = datetime(2000, 1, 1, hh, mm, ss) - timedelta(seconds=15)
            prev = dt.hour * 10000 + dt.minute * 100 + dt.second
            return prev
        except:
            return None

    def get_full_data(self, date, term, page=1, per_page=200, diff_df=None,
                      filter_cp=None, filter_strike=None, filter_time=None):
        """取得完整計算資料（含差異標記），展開為 Call/Put Long format

        diff_df: DiffLoader 載入的差異 DataFrame，用來標記哪些列有差，可為 None
        回傳: {rows, total, total_pages, page}
        """
        path = os.path.join(self.output_dir, f"驗證{date}_{term}PROD.csv")
        if not os.path.exists(path):
            return {"rows": [], "total": 0, "total_pages": 0, "page": 1, "error": f"找不到 {path}"}

        cache_key = f"full_{date}_{term}"
        if cache_key not in self._cache:
            df = pd.read_csv(path, encoding="utf-8-sig", low_memory=False)
            self._cache[cache_key] = df
        df = self._cache[cache_key].copy()

        # time_int 欄位（用於比對）
        if "time_int" not in df.columns:
            df["time_int"] = df["time"].astype(str).str.replace(":", "").apply(
                lambda x: int(x) if x.replace(":", "").isdigit() else 0
            )

        # 展開成 Call / Put 兩列
        col_map_c = {
            "c.ema": "EMA", "c.gamma": "Gamma",
            "c.bid": "Q_hat_Bid", "c.ask": "Q_hat_Ask",
            "c.last_bid": "Q_Last_Bid", "c.last_ask": "Q_Last_Ask",
            "c.min_bid": "Min_Bid", "c.min_ask": "Min_Ask",
        }
        col_map_p = {
            "p.ema": "EMA", "p.gamma": "Gamma",
            "p.bid": "Q_hat_Bid", "p.ask": "Q_hat_Ask",
            "p.last_bid": "Q_Last_Bid", "p.last_ask": "Q_Last_Ask",
            "p.min_bid": "Min_Bid", "p.min_ask": "Min_Ask",
        }

        def make_side(side_map, cp_label):
            cols_needed = ["time_int", "time", "strike"] + [c for c in side_map if c in df.columns]
            side = df[cols_needed].copy()
            side = side.rename(columns=side_map)
            side["CP"] = cp_label
            side["Term"] = term
            return side

        long_df = pd.concat([make_side(col_map_c, "Call"), make_side(col_map_p, "Put")], ignore_index=True)
        long_df["strike"] = pd.to_numeric(long_df["strike"], errors="coerce").fillna(0).astype(int)

        # 篩選
        if filter_cp and filter_cp != "all":
            long_df = long_df[long_df["CP"] == filter_cp]
        if filter_strike:
            long_df = long_df[long_df["strike"] == int(filter_strike)]
        if filter_time:
            long_df = long_df[long_df["time_int"] == int(filter_time)]

        # 標記是否有差異
        long_df["has_diff"] = False
        long_df["diff_cols"] = ""
        if diff_df is not None and not diff_df.empty:
            term_diffs = diff_df[diff_df["Term"].astype(str) == term].copy()
            if not term_diffs.empty:
                term_diffs["Time"] = pd.to_numeric(term_diffs["Time"], errors="coerce").fillna(0).astype(int)
                term_diffs["Strike"] = pd.to_numeric(term_diffs["Strike"], errors="coerce").fillna(0).astype(int)
                diff_map = term_diffs.groupby(["Time", "Strike", "CP"])["Column"].apply(
                    lambda x: ",".join(x)
                ).to_dict()
                def _mark(row):
                    key = (int(row["time_int"]), int(row["strike"]), row["CP"])
                    return diff_map.get(key, "")
                long_df["diff_cols"] = long_df.apply(_mark, axis=1)
                long_df["has_diff"] = long_df["diff_cols"] != ""

        # 排序
        long_df = long_df.sort_values(["time_int", "strike", "CP"]).reset_index(drop=True)

        total = len(long_df)
        total_pages = max(1, (total + per_page - 1) // per_page)
        page = max(1, min(page, total_pages))
        start = (page - 1) * per_page
        page_df = long_df.iloc[start:start + per_page].copy()

        # NaN → None
        page_df = page_df.astype(object).where(pd.notnull(page_df), None)

        return {
            "rows": page_df.to_dict(orient="records"),
            "total": total,
            "total_pages": total_pages,
            "page": page,
        }

    def get_snapshot_with_contrib(self, date, time_int):
        """讀取 Near_Contrib 與 Next_Contrib 並組合為 T 字報價所需結構
        回傳: {"Near": [rows...], "Next": [rows...]}
        """
        result = {"Near": [], "Next": []}

        for term in ["Near", "Next"]:
            path = os.path.join(self.source_dir, date, f"{term}_Contrib_{date}.tsv")
            if not os.path.exists(path):
                continue
            
            df = pd.read_csv(path, sep="\t")
            # 篩選特定時間
            df_time = df[df["time"] == int(time_int)].copy()
            if df_time.empty:
                continue
                
            # 尋找全空(只含 strike 等基本資訊) 的 row 來取得 ATM Strike
            # 我們可以觀察 contrib 欄位是否為空 (NaN) 或 'X'
            atm_mask = df_time['contrib'].isna() | (df_time['contrib'] == 'X') | (df_time['contrib'] == '') | (df_time['contrib'] == ' ')
            atm_rows = df_time[atm_mask]
            atm_strike = atm_rows.iloc[0]['strike'] if not atm_rows.empty else None
            
            # 標記 ATM，並過濾掉只用來標記 ATM 但是缺乏 contrib 和 mid 等報價的「空氣列」
            # 我們會保留該 strike 的其他正常列，這才是我們要畫的！
            df_time["is_atm"] = (df_time["strike"] == atm_strike)
            df_time = df_time[~df_time.index.isin(atm_rows.index)]
            
            # 確保有 contrib 欄位 (原本為科學記號字串或數值)
            df_time["contrib_num"] = pd.to_numeric(df_time["contrib"], errors="coerce").fillna(0)
            
            # NaN -> None
            df_time = df_time.astype(object).where(pd.notnull(df_time), None)
            
            # 依履約價排序
            df_time = df_time.sort_values("strike")
            
            result[term] = df_time.to_dict(orient="records")

        return result

class SigmaDiffLoader:
    """讀取 PROD 的 sigma_YYYYMMDD.tsv 與我們產出的 my_sigma_YYYYMMDD.tsv 進行差異比對"""
    def __init__(self, prod_dir, my_dir):
        self.prod_dir = prod_dir  # 資料來源目錄
        self.my_dir = my_dir      # output 目錄
        self._cache = {}

    def get_diff(self, date):
        # PROD 檔案預期在 資料來源/YYYYMMDD/sigma_YYYYMMDD.tsv
        prod_path = os.path.join(self.prod_dir, date, f"sigma_{date}.tsv")
        # 我們自算的檔案預期在 output/my_sigma_YYYYMMDD.tsv
        my_path = os.path.join(self.my_dir, f"my_sigma_{date}.tsv")

        if not os.path.exists(prod_path) or not os.path.exists(my_path):
            return {"error": "缺少 PROD 或是 My 的 sigma 檔案", "rows": []}

        df_prod = pd.read_csv(prod_path, sep="\t", dtype={"time": str})
        df_my = pd.read_csv(my_path, sep="\t", dtype={"time": str})

        # 確保 time 格式為 6 碼 (e.g. 084515)
        df_prod["time"] = df_prod["time"].astype(str).str.zfill(6)
        df_my["time"] = df_my["time"].astype(str).str.zfill(6)

        # Merge
        df = pd.merge(df_prod, df_my, on=["date", "time"], suffixes=("_prod", "_my"), how="outer")

        # 計算數值差異
        def calc_diff(col):
            my_col = f"{col}_my"
            prod_col = f"{col}_prod"
            if my_col in df.columns and prod_col in df.columns:
                df[f"{col}_diff"] = pd.to_numeric(df[my_col], errors='coerce') - pd.to_numeric(df[prod_col], errors='coerce')

        calc_diff("nearSigma2")
        calc_diff("nextSigma2")
        calc_diff("vix")
        calc_diff("ori_vix")

        df = df.astype(object).where(pd.notnull(df), None)
        
        # 依照時間排序
        df = df.sort_values(by="time").reset_index(drop=True)

        result = {
            "error": None,
            "rows": df.to_dict(orient="records")
        }
        return result
