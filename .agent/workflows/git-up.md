---
description: 一鍵執行 Git Add, Commit 與 Push，並自動遵守文件更新規範。
---

// turbo-all
1. 確保當前目錄為 Git 倉庫並掃描變更內容
2. 根據變更生成符合規範的提交訊息（例如：\eat: ... | docs: ...\）
3. 檢查 \spec.md\ 與 \README.md\ 是否有相應的變更（若程式碼有變更但文件未更新，主動告知使用者）
4. 執行 \git add .\
5. 執行 \git commit -m "[自動生成訊息]"
6. 執行 \git push origin [當前分支名]
"@

     = @"
---
description: 一鍵執行 Git Pull 並將本地狀態同步為與遠端完全一致（衝突時強制以遠端為主）。
---

// turbo-all
1. 檢查當前目錄是否為 Git 倉庫。
2. 執行 \git fetch --all\ 以獲取最新的遠端分支狀態。
3. 檢查本地是否有未 Commit 的變更（若有，主動提醒使用者將被覆蓋）。
4. 執行同步操作（預設策略為強制以遠端為主）：
   - \git reset --hard origin/[當前分支名]\
5. 執行 \git pull\ 確保狀態與遠端完全同步。
