# Git 與 GitHub 使用指南 (Git & GitHub Usage Guide)

本文件說明在本專案中常用的 Git 指令與 GitHub 工作流程。

## 📥 基礎操作：與遠端同步

### 1. 下載專案 (Clone)

第一次將專案下載到本機電腦：

```bash
git clone https://github.com/使用者名稱/VIX.git
```

### 2. 更新最新程式碼 (Pull)

在開發前，先將遠端的變更拉回本機，避免衝突：

```bash
git pull origin main
```

---

## 💾 開發流程：儲存變更

### 1. 查看目前狀態 (Status)

確認哪些檔案已被修改、哪些檔案還沒被加進 Git 追蹤：

```bash
git status
```

### 2. 加入暫存區 (Add)

將修改過的檔案加入準備提交的名單：

- 加入所有變更：`git add .`
- 加入指定檔案：`git add path/to/file.py`

### 3. 提交紀錄 (Commit)

將暫存區的內容儲存為一個歷史紀錄（請務必附上清楚的變更訊息）：

```bash
git commit -m "修正: 優化 EMA 計算邏輯並更新相關規格文件"
```

### 4. 推送至 GitHub (Push)

將本機的提交推送至遠端倉庫：

```bash
git push origin main
```

---

## 🌿 分支管理 (Branching)

### 1. 建立並切換至新分支

開發新功能或修復 Bug 時，建議開分支處理：

```bash
# 建立並切換
git checkout -b feature/new-algorithm
```

### 2. 查看所有分支

```bash
git branch -a
```

### 3. 合併分支 (Merge)

將 `feature` 分支的變更合併回 `main`：

```bash
# 先切回 main
git checkout main
# 執行合併
git merge feature/new-algorithm
```

---

## 🔍 其他常用指令

### 1. 查看提交歷史 (Log)

```bash
# 簡潔模式
git log --oneline
```

### 2. 復原變更 (Undo)

- 捨棄本機尚未 add 的變更：`git checkout -- [file]`
- 移除已 add 到暫存區的檔案：`git reset HEAD [file]`

---

## 💡 專案開發建議

- **頻密提交**：每完成一個小功能或修復一個 Bug 就 commit 一次，方便回溯。
- **Pull Before Push**：推送前先執行 `git pull` 以確保沒與其他人衝突。
- **README 同步**：本專案要求在修改程式碼前，先更新相關說明文件 (如 `README.md` 或 `docs/`) 以維持開發軌跡。
