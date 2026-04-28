import os
import tarfile
import pathlib
import zstandard as zstd
import io

def extract_all_compressed(directory):
    dir_path = pathlib.Path(directory).resolve()
    print(f"正在處理目錄: {dir_path}")

    # 找出所有壓縮檔
    xz_files = list(dir_path.glob("*.tar.xz"))
    zst_files = list(dir_path.glob("*.tar.zst"))
    
    all_files = xz_files + zst_files
    
    if not all_files:
        print("找不到任何 .tar.xz 或 .tar.zst 檔案。")
        return

    print(f"找到 {len(all_files)} 個壓縮檔 ({len(xz_files)} 個 xz, {len(zst_files)} 個 zstd)。")

    for file_path in all_files:
        # 設定解壓縮目標目錄（與檔案同名但不含副檔名）
        ext = "".join(file_path.suffixes)
        target_dir = dir_path / file_path.name.replace(ext, '')
        
        print(f"正在解壓縮: {file_path.name} -> {target_dir.name}")
        
        try:
            # 確保目標目錄存在
            if not target_dir.exists():
                target_dir.mkdir(parents=True, exist_ok=True)
            
            if file_path.suffix == '.xz':
                with tarfile.open(file_path, "r:xz") as tar:
                    tar.extractall(path=target_dir)
            elif file_path.suffix == '.zst':
                dctx = zstd.ZstdDecompressor()
                with open(file_path, 'rb') as ifh:
                    with dctx.stream_reader(ifh) as reader:
                        # 由於 tarfile.open(fileobj=reader, mode='r|') 有時在某些環境下會有問題
                        # 如果檔案不大，可以直接讀入記憶體或使用 tempfile
                        # 這裡的檔案最大 70MB，讀入記憶體是安全的
                        data = reader.read()
                        with tarfile.open(fileobj=io.BytesIO(data), mode='r') as tar:
                            tar.extractall(path=target_dir)
            
            print(f"  [成功] 已完成 {file_path.name}")
        except Exception as e:
            print(f"  [錯誤] 解壓縮 {file_path.name} 時發生問題: {e}")

if __name__ == "__main__":
    source_dir = r"c:\Users\jerry1016\.gemini\antigravity\VIX\資料來源"
    extract_all_compressed(source_dir)
