---
name: metablog-cli
description: 透過 MetaWeblog XML-RPC API 管理部落格文章。當使用者提到發文、更新文章、列出文章、下載部落格內容、dotblogs、MetaWeblog、或想把 Markdown 文章推上部落格時，一定要使用這個 skill。即使使用者只說「幫我發這篇」或「看一下我的 blog」或 發佈點部落文章，也應套用此 skill。
---

# metablog-cli

用 MetaWeblog XML-RPC API 對部落格執行 publish / list / get 三種操作。預設平台為**點部落（dotblogs.com.tw）**，亦支援任何實作 MetaWeblog 標準的平台（WordPress 等）。

> 安裝與初始設定請參考 README.md。

## 操作指令

所有指令從 `${CLAUDE_SKILL_DIR}` 執行：

### 列出文章

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/metablog_cli.py list            # 最新 10 筆
uv run ${CLAUDE_SKILL_DIR}/scripts/metablog_cli.py list --size 20  # 指定筆數
uv run ${CLAUDE_SKILL_DIR}/scripts/metablog_cli.py list --all      # 全部
```

### 下載文章為 Markdown

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/metablog_cli.py get --latest 2               # 最新 N 篇
uv run ${CLAUDE_SKILL_DIR}/scripts/metablog_cli.py get --ids <postId> [postId]  # 指定 postId
```

下載的 `.md` 存到 `output/`，自動補上 frontmatter。

### 發布 / 更新文章

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/metablog_cli.py publish /path/to/post.md  # 指定檔案
uv run ${CLAUDE_SKILL_DIR}/scripts/metablog_cli.py publish                   # 預設 output/blog.md
uv run ${CLAUDE_SKILL_DIR}/scripts/metablog_cli.py -o /dir publish           # 指定輸出目錄
```

- 無 frontmatter → 自動產生並寫回 `.md`，上傳為草稿
- frontmatter 有 postId → 更新既有文章（editPost）
- frontmatter 無 postId → 新增文章，postId 自動回填

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

**情境 A：發一篇新文章**
1. 確認 `.md` 檔路徑
2. 執行 `publish`，若無 frontmatter 會自動產生
3. 告知草稿後台連結（輸出中的「後台編輯」URL）

**情境 B：更新舊文章**
1. 若手邊無 `.md`，先用 `get --ids <postId>` 下載
2. 修改後執行 `publish`（frontmatter 有 postId，自動走 editPost）

**情境 C：查看文章列表**
1. 執行 `list`，依需求加 `--size` 或 `--all`
2. 列出 postId 供後續操作參考
