import os
import tarfile
import pathlib

def extract_all_tar_xz(directory):
    # 轉換為絕對路徑
    dir_path = pathlib.Path(directory).resolve()
    print(f"正在處理目錄: {dir_path}")

    # 找出所有 .tar.xz 檔案
    tar_files = list(dir_path.glob("*.tar.xz"))
    
    if not tar_files:
        print("找不到任何 .tar.xz 檔案。")
        return

    print(f"找到 {len(tar_files)} 個壓縮檔。")

    for tar_file in tar_files:
        # 設定解壓縮目標目錄（與檔案同名但不含副檔名）
        # 注意：tar.xz 有兩個副檔名，所以要取兩次 stem 或者直接切掉
        target_dir = dir_path / tar_file.name.replace('.tar.xz', '')
        
        print(f"正在解壓縮: {tar_file.name} -> {target_dir.name}")
        
        try:
            # 確保目標目錄存在
            if not target_dir.exists():
                target_dir.mkdir(parents=True, exist_ok=True)
            
            with tarfile.open(tar_file, "r:xz") as tar:
                tar.extractall(path=target_dir)
            print(f"  [成功] 已完成 {tar_file.name}")
        except Exception as e:
            print(f"  [錯誤] 解壓縮 {tar_file.name} 時發生問題: {e}")

if __name__ == "__main__":
    source_dir = r"c:\Users\jerry1016\.gemini\antigravity\VIX\資料來源"
    extract_all_tar_xz(source_dir)
