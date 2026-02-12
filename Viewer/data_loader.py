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
    
    def get_page(self, date, page=1, per_page=100):
        """取得分頁資料"""
        df = self._load_df(date)
        
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
            # PROD 路徑: 資料來源/20251201/NearPROD_20251201.tsv
            # 注意: term 可能是 "Near" 或 "Next"
            path = os.path.join(self.source_dir, date, f"{term}PROD_{date}.tsv")
            if os.path.exists(path):
                self._cache[key] = pd.read_csv(path, sep="\t")
            else:
                return {}
        
        df = self._cache[key]
        # PROD time 可能是 int (HMMSS)
        # 確保型別一致
        row = df[(df["time"] == int(time_val)) & (df["strike"] == int(strike))]
        if row.empty:
            return {}
        return row.astype(object).where(pd.notnull(row), None).iloc[0].to_dict()
