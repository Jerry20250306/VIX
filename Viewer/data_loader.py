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
    
    # 驗證腳本 verify_full_day.py 中定義的所有比對欄位
    ALL_COMPARED_COLUMNS = ['EMA', 'Gamma', 'Q_hat_Bid', 'Q_hat_Ask', 'Q_Last_Bid', 'Q_Last_Ask', 'Last_Outlier']
    
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
        if key not in self._cache:
            path = os.path.join(self.source_dir, date, f"{term}PROD_{date}.tsv")
            if os.path.exists(path):
                self._cache[key] = pd.read_csv(path, sep="\t")
            else:
                return {}
        
        df = self._cache[key]
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

class SigmaDiffLoader:
    """讀取 PROD 的 sigma_YYYYMMDD.tsv 與我們產出的 my_sigma_YYYYMMDD.tsv 進行差異比對"""
    def __init__(self, prod_dir, my_dir):
        self.prod_dir = prod_dir  # 資料來源目錄
        self.my_dir = my_dir      # output 目錄
        self._cache = {}

    def get_diff(self, date):
        if date in self._cache:
            return self._cache[date]

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
        self._cache[date] = result
        return result
