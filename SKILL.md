---
name: metablog-cli
description: 透過 MetaWeblog XML-RPC API 管理部落格文章。當使用者提到發文、更新文章、列出文章、下載部落格內容、dotblogs、MetaWeblog、或想把 Markdown 文章推上部落格時，一定要使用這個 skill。即使使用者只說「幫我發這篇」或「看一下我的 blog」，也應套用此 skill。
---

# metablog-cli

用 MetaWeblog XML-RPC API 對部落格執行 publish / list / get 三種操作，支援任何實作 MetaWeblog 標準的平台（dotblogs、WordPress 等）。

## 安裝

```bash
git clone https://github.com/yaochangyu/metablog-cli.git
cd metablog
uv sync
```

在 Claude Code 設定中新增此 skill：

```json
{
  "skills": [
    { "path": "/path/to/metablog" }
  ]
}
```

## 初始設定

**1. 建立 `.env`**

```bash
cp .env.example .env
```

填入以下欄位（不要填密碼）：

```env
BLOG_USER=your_email@example.com
BLOG_NAME=你的部落格名稱
BLOG_URL=your_subdomain
BLOG_API_URL=https://dotblogs.com.tw/Api/MetaWeblog
```

**2. 將密碼存入系統 Keychain（只需執行一次）**

```bash
uv run python3 -c "import keyring; keyring.set_password('dotblogs', 'BLOG_PASSWORD', '你的密碼')"
```

密碼存於 OS 加密鑰匙圈，不落地於任何檔案。

## 操作指令

所有指令從 `/path/to/metablog/` 執行：

### 列出文章

```bash
# 最新 10 筆（預設）
uv run ${CLAUDE_SKILL_DIR}/scripts/metablog_cli.py list

# 指定筆數
uv run ${CLAUDE_SKILL_DIR}/scripts/metablog_cli.py list --size 20

# 全部
uv run ${CLAUDE_SKILL_DIR}/scripts/metablog_cli.py list --all
```

### 下載文章為 Markdown

```bash
# 最新 N 篇
uv run ${CLAUDE_SKILL_DIR}/scripts/metablog_cli.py get --latest 2

# 指定 postId
uv run ${CLAUDE_SKILL_DIR}/scripts/metablog_cli.py get --ids <postId> [postId ...]
```

下載的 `.md` 會存到 `output/`，並自動補上 frontmatter。

### 發布 / 更新文章

```bash
# 發布指定 .md 檔
uv run ${CLAUDE_SKILL_DIR}/scripts/metablog_cli.py publish /path/to/post.md

# 使用預設路徑（output/blog.md）
uv run ${CLAUDE_SKILL_DIR}/scripts/metablog_cli.py publish
```

- 無 frontmatter → 自動產生並寫回 `.md`，上傳為草稿
- frontmatter 有 postId → 更新既有文章（editPost）
- frontmatter 無 postId → 新增文章，postId 自動回填

### 指定輸出目錄

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/metablog_cli.py -o /path/to/dir publish
uv run ${CLAUDE_SKILL_DIR}/scripts/metablog_cli.py -o /path/to/dir get --latest 5
```

## Frontmatter 欄位

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

## 使用情境

**情境 A：使用者要發一篇新文章**
1. 確認 `.md` 檔路徑
2. 執行 `publish`，若無 frontmatter 會自動產生
3. 告知草稿連結（後台編輯 URL）

**情境 B：使用者要更新舊文章**
1. 若手邊無 `.md`，先用 `get --ids <postId>` 下載
2. 修改內容後執行 `publish`（frontmatter 已有 postId，自動走 editPost）

**情境 C：使用者要查看目前文章列表**
1. 執行 `list`，依需求加 `--size` 或 `--all`
2. 列出 postId 供後續操作參考
