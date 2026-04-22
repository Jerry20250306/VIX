import os
import shutil

def package_demo(date_str):
    target_dir = f"VIX_Demo_{date_str}"
    
    # 1. 確保目標資料夾是乾淨的
    if os.path.exists(target_dir):
        shutil.rmtree(target_dir)
    os.makedirs(target_dir, exist_ok=True)
    
    # 2. 複製執行檔
    exe_src = os.path.join("dist", "VIX_Viewer.exe")
    if os.path.exists(exe_src):
        shutil.copy(exe_src, target_dir)
        print(f"Copied {exe_src}")
    
    # 3. 複製 output 中對應日期的檔案
    out_target = os.path.join(target_dir, "output")
    os.makedirs(out_target, exist_ok=True)
    out_src = "output"
    if os.path.exists(out_src):
        for f in os.listdir(out_src):
            if date_str in f:
                src_file = os.path.join(out_src, f)
                if os.path.isfile(src_file):
                    shutil.copy(src_file, out_target)
        print(f"Copied output files for {date_str}")
        
    # 4. 複製 資料來源 中包含該日期的所有資料夾 (包括 20251231 與 J002-11300041_20251231)
    if os.path.exists("資料來源"):
        for f in os.listdir("資料來源"):
            if date_str in f:
                src_path = os.path.join("資料來源", f)
                target_path = os.path.join(target_dir, "資料來源", f)
                if os.path.isdir(src_path):
                    shutil.copytree(src_path, target_path)
                    print(f"Copied {src_path}")
        
    # 5. 複製說明文件
    readme_src = "README_OFFLINE.txt"
    if os.path.exists(readme_src):
        shutil.copy(readme_src, target_dir)
        print(f"Copied {readme_src}")

if __name__ == "__main__":
    package_demo("20251231")
    print("打包完成！")
