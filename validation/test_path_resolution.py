import sys
import os
import glob

# 加入父目錄以引用 vix_utils
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from vix_utils import get_vix_config, DataPathManager

def test_resolve_20251231():
    print("Testing date: 20251231")
    
    # 1. Test get_vix_config (Default)
    print("\n--- Test 1: get_vix_config(target_date='20251231') ---")
    config = get_vix_config("20251231")
    
    raw_path = config['raw_dir']
    prod_path = config['prod_dir']
    
    if raw_path and "J002" in raw_path and "temp" in raw_path:
        print(f"[OK] Raw Path resolved to: {raw_path}")
    else:
        print(f"[FAIL] Raw Path unexpected: {raw_path}")

    if prod_path and os.path.basename(prod_path) == "20251231":
         print(f"[OK] Prod Path resolved to: {prod_path}")
    else:
        print(f"[FAIL] Prod Path unexpected: {prod_path}")
        
    # 2. Test Env Vars
    print("\n--- Test 2: Environment Variables ---")
    # Mocking env vars
    os.environ["VIX_DATA_SOURCE"] = "MY_TEST_RAW"
    os.environ["VIX_PROD_SOURCE"] = "MY_TEST_PROD"
    
    # Re-init manager to pick up env vars
    manager_env = DataPathManager()
    print(f"Env Raw Base: {manager_env.raw_base_dir}")
    print(f"Env Prod Base: {manager_env.prod_base_dir}")
    
    if "MY_TEST_RAW" in manager_env.raw_base_dir:
         print("[OK] VIX_DATA_SOURCE env var respected")
    else:
         print("[FAIL] VIX_DATA_SOURCE env var ignored")
         
    # Clean up
    del os.environ["VIX_DATA_SOURCE"]
    del os.environ["VIX_PROD_SOURCE"]

if __name__ == "__main__":
    test_resolve_20251231()
