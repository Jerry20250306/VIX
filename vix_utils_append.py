
def get_vix_config(target_date=None):
    """
    取得 VIX 計算的相關設定 (統一管理入口)
    
    邏輯：
    1. 日期優先順序: 傳入參數 > 命令列參數 (--date) > 預設值 (20251231)
    2. 路徑優先順序: DataPathManager 會自動依序嘗試 環境變數 > 預設相對路徑
    
    Args:
        target_date (str, optional): 指定日期 (YYYYMMDD). Defaults to None.
        
    Returns:
        dict: 包含以下鍵值的設定字典
            - target_date: 目標日期
            - raw_dir: 原始資料目錄路徑
            - prod_dir: PROD 資料目錄路徑
            - raw_base_dir: 原始資料基礎目錄
            - prod_base_dir: PROD 資料基礎目錄
    """
    import argparse
    
    # 1. 決定日期
    final_date = "20251231" # Default
    
    if target_date:
        final_date = target_date
    else:
        # 嘗試從命令列讀取 (簡單解析，避免干擾主程式的其他參數)
        # 這裡只檢查是否有 --date 參數，不使用 argparse 以免搶走主程式的 help
        if "--date" in sys.argv:
            try:
                idx = sys.argv.index("--date")
                if idx + 1 < len(sys.argv):
                    final_date = sys.argv[idx + 1]
            except:
                pass
        # 或者是位置參數? 暫時不支援位置參數以免混淆，統一用 --date 或函式呼叫
        
    # 2. 初始化路徑管理器 (它會自動讀取環境變數)
    manager = DataPathManager()
    
    # 3. 解析路徑
    print(f"[Config] Target Date: {final_date}")
    try:
        raw_dir = manager.resolve_raw_path(final_date)
        print(f"[Config] Raw Data Dir: {raw_dir}")
    except Exception as e:
        print(f"[Config] Warning: Raw path resolution failed: {e}")
        raw_dir = None
        
    try:
        prod_dir = manager.resolve_prod_path(final_date)
        print(f"[Config] PROD Data Dir: {prod_dir}")
    except Exception as e:
        print(f"[Config] Warning: PROD path resolution failed: {e}")
        prod_dir = None
        
    return {
        "target_date": final_date,
        "raw_dir": raw_dir,
        "prod_dir": prod_dir,
        "raw_base_dir": manager.raw_base_dir,
        "prod_base_dir": manager.prod_base_dir
    }
