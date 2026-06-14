# metablog

透過 MetaWeblog XML-RPC API 管理部落格文章的命令列工具，支援任何實作 MetaWeblog 標準的平台（dotblogs、WordPress 等）。

## 功能

- `publish`：將 Markdown 文章發布或更新到部落格（草稿或公開）
- `list`：列出最新文章
- `get`：從部落格下載文章，轉換為 Markdown 存檔

## 環境需求

- [uv](https://docs.astral.sh/uv/) — Python 套件與環境管理

## 安裝

```bash
git clone https://github.com/yaochangyu/metablog.git
cd metablog
uv sync
```

## 設定

### 1. 建立 `.env`

```bash
cp .env.example .env
```

填入以下欄位（不要填密碼，所有欄位皆為必填）：

```env
BLOG_USER=your_email@example.com
BLOG_NAME=你的部落格名稱
BLOG_URL=your_blog_subdomain
BLOG_API_URL=https://dotblogs.com.tw/Api/MetaWeblog
```

> `BLOG_PASSWORD` **不要**放在 `.env`，請用下方的 Keychain 方式設定。

dotblogs 以外的平台只需更換 `BLOG_API_URL`。

### 2. 將密碼存入系統 Keychain（只需一次）

密碼存於 OS 加密鑰匙圈（macOS Keychain / Windows Credential Manager / Linux Secret Service），不落地於任何檔案：

```bash
uv run python3 -c "import keyring; keyring.set_password('dotblogs', 'BLOG_PASSWORD', '你的密碼')"
```

驗證是否存入成功：

```bash
uv run python3 -c "import keyring; print(keyring.get_password('dotblogs', 'BLOG_PASSWORD'))"
```

### 3. 安裝為 Claude Code Skill（選用）

在 Claude Code 設定中新增此 skill，Claude 就能直接幫你發文：

```json
{
  "skills": [
    { "path": "/path/to/metablog" }
  ]
}
```

## 使用方式

### 列出最新文章

```bash
# 最新 10 筆（預設）
uv run scripts/metablog_cli.py list

# 指定筆數
uv run scripts/metablog_cli.py list --size 20

# 全部
uv run scripts/metablog_cli.py list --all
```

### 下載文章為 Markdown

```bash
# 最新 2 篇
uv run scripts/metablog_cli.py get --latest 2

# 指定 postId（可多個）
uv run scripts/metablog_cli.py get --ids <postId> [postId ...]

# 指定輸出目錄（預設 output/）
uv run scripts/metablog_cli.py -o /path/to/dir get --latest 5
```

下載的 `.md` 檔會自動加上 frontmatter，可直接用 `publish` 更新回去。

### 發布文章

```bash
# 指定檔案
uv run scripts/metablog_cli.py publish /path/to/post.md

# 使用預設路徑（output/blog.md）
uv run scripts/metablog_cli.py publish

# 指定輸出目錄下的 blog.md
uv run scripts/metablog_cli.py -o /path/to/dir publish
```

- **無 frontmatter**：自動產生並寫回 `.md`，上傳為草稿
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
