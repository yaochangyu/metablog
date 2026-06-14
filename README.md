# publish-blog

用 MetaWebLog XML-RPC API 操作 dotblogs.com.tw 的命令列工具。

## 功能

- `publish`：將 Markdown 文章發布或更新到 dotblogs（草稿或公開）
- `list`：列出最新文章
- `get`：從 dotblogs 下載文章，轉換為 Markdown 存檔

## 環境需求

- [uv](https://docs.astral.sh/uv/) — Python 套件與環境管理

## 安裝

```bash
git clone <repo>
cd publish-blog
uv sync
```

## 設定

### 1. 建立 `.env`

複製範本後填入部落格資訊：

```bash
cp .env.example .env
```

`.env` 內容：

```env
BLOG_USER=your_email@example.com
BLOG_NAME=你的部落格名稱
BLOG_URL=your_blog_subdomain
```

> `BLOG_PASSWORD` **不要**放在 `.env`，請用下方的 keychain 方式設定。

### 2. 將密碼存入系統 Keychain

密碼透過作業系統的加密鑰匙圈（macOS Keychain / Windows Credential Manager / Linux Secret Service）儲存，不落地於任何檔案：

```bash
uv run python3 -c "import keyring; keyring.set_password('dotblogs', 'BLOG_PASSWORD', '你的密碼')"
```

執行一次即可，之後腳本會自動從 keychain 讀取。

若需要驗證是否存入成功：

```bash
uv run python3 -c "import keyring; print(keyring.get_password('dotblogs', 'BLOG_PASSWORD'))"
```

若需要更換密碼，重新執行 `set_password` 覆蓋即可。

## 使用方式

### 列出最新文章

```bash
# 最新 10 筆（預設）
uv run publish_blog.py list

# 指定筆數
uv run publish_blog.py list --size 20

# 全部
uv run publish_blog.py list --all
```

### 下載文章為 Markdown

```bash
# 最新 2 篇
uv run publish_blog.py get --latest 2

# 指定 postId（可多個）
uv run publish_blog.py get --ids <postId> [postId ...]

# 指定輸出目錄（預設 output/）
uv run publish_blog.py -o /path/to/dir get --latest 5
```

下載的 `.md` 檔會自動加上 frontmatter，可直接用 `publish` 子命令更新回去。

### 發布文章

```bash
# 使用預設路徑（output/blog.md）
uv run publish_blog.py publish

# 指定檔案
uv run publish_blog.py publish /path/to/post.md

# 指定輸出目錄下的 blog.md
uv run publish_blog.py -o /path/to/dir publish
```

- **無 frontmatter**：自動產生並寫回 `.md` 檔，上傳為草稿
- **有 frontmatter、postId 為空**：新增文章，`postId` 自動回填
- **有 frontmatter、postId 有值**：更新既有文章

### Frontmatter 欄位說明

| 欄位 | 說明 |
|------|------|
| `title` | 文章標題 |
| `abstract` | 摘要（HTML），對應 `mt_excerpt` |
| `keywords` | 逗號分隔關鍵字 |
| `categories` | 分類，字串或 list |
| `weblogName` | 部落格名稱 |
| `postId` | 文章 ID，有值則更新，空則新增 |
| `postDate` | 發布日期，ISO 8601 格式 |
| `postStatus` | `publish` → 公開；其餘 → 草稿 |
| `stripH1Header` | `true` → 發布時移除內文第一個 H1 |
| `dontInferFeaturedImage` | 保留欄位 |
