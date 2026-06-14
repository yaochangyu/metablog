#!/usr/bin/env python3
"""
用 MetaWebLog API 操作 dotblogs.com.tw

環境變數：
  BLOG_USER      登入 email（必填）
  BLOG_PASSWORD  登入密碼（必填）

用法：
  publish_blog.py publish [file.md]                   發布/更新文章（預設 blog.md）
  publish_blog.py list [--size N] [--all]             列出文章
  publish_blog.py get <postId> [postId ...]           下載文章轉存為 .md
  publish_blog.py get --latest N                      下載最新 N 篇

frontmatter 欄位（publish 時若不存在會自動產生並寫回 .md）：
  title / abstract / keywords / categories / weblogName
  postId / postDate / postStatus / dontInferFeaturedImage / stripH1Header
"""
import argparse
import os
import re
import sys
import xmlrpc.client
import markdown
import yaml
from datetime import datetime
import keyring
from dotenv import load_dotenv
from markdownify import markdownify as html2md

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

KEYRING_SERVICE = "dotblogs"
API_URL         = os.environ.get("BLOG_API_URL", "https://dotblogs.com.tw/Api/MetaWeblog")
BLOG_NAME       = os.environ.get("BLOG_NAME", "")
BLOG_URL        = os.environ.get("BLOG_URL", "")

FRONTMATTER_KEYS = [
    "title", "abstract", "keywords", "categories", "weblogName",
    "postId", "postDate", "postStatus", "dontInferFeaturedImage", "stripH1Header",
]


# ---------------------------------------------------------------------------
# YAML frontmatter 工具
# ---------------------------------------------------------------------------

def _yaml_scalar(val) -> str:
    if val is None:
        return ""
    if isinstance(val, bool):
        return "true" if val else "false"
    s = str(val)
    if s and (s[0] in "[]{},#*&!|>'\"`@%" or ": " in s or s.startswith("- ")):
        return "'" + s.replace("'", "''") + "'"
    return s


def format_frontmatter(meta: dict) -> str:
    lines = ["---"]
    for key in FRONTMATTER_KEYS:
        val = meta.get(key, "")
        if isinstance(val, list):
            lines.append(f"{key}: {', '.join(str(v) for v in val)}")
        else:
            lines.append(f"{key}: {_yaml_scalar(val)}")
    lines.append("---\n")
    return "\n".join(lines)


def parse_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    meta = yaml.safe_load(text[3:end].strip()) or {}
    body = text[end + 4:].lstrip("\n")
    return meta, body


def update_frontmatter_field(path: str, field: str, value: str):
    with open(path, encoding="utf-8") as f:
        content = f.read()
    if not content.startswith("---"):
        return
    end = content.find("\n---", 3)
    if end == -1:
        return
    yaml_block = content[3:end]
    yaml_block = re.sub(
        rf"^{field}:.*$",
        f"{field}: {_yaml_scalar(value)}",
        yaml_block,
        flags=re.MULTILINE,
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"---{yaml_block}\n---{content[end + 4:]}")


# ---------------------------------------------------------------------------
# Markdown 工具
# ---------------------------------------------------------------------------

def md_to_html(md_text: str) -> str:
    engine = markdown.Markdown(extensions=["tables", "fenced_code", "nl2br"])
    return engine.convert(md_text)


def extract_h1(text: str) -> str:
    m = re.match(r"^#\s+(.+)", text, re.MULTILINE)
    return m.group(1).strip() if m else "未命名文章"


def strip_h1(text: str) -> str:
    return re.sub(r"^#\s+.+\n*", "", text, count=1)


def first_paragraph_html(body_md: str) -> str:
    body = strip_h1(body_md).strip()
    first = next((p.strip() for p in re.split(r"\n\n+", body) if p.strip()), "")
    return md_to_html(first) if first else ""


# ---------------------------------------------------------------------------
# frontmatter 自動產生 + 寫回
# ---------------------------------------------------------------------------

def generate_and_write_frontmatter(path: str, raw: str) -> tuple[dict, str]:
    meta = {
        "title":                 extract_h1(raw),
        "abstract":              first_paragraph_html(raw),
        "keywords":              "",
        "categories":            "",
        "weblogName":            BLOG_NAME,
        "postId":                "",
        "postDate":              datetime.now().strftime("%Y-%m-%dT%H:%M:%S.0000000"),
        "postStatus":            "",
        "dontInferFeaturedImage": False,
        "stripH1Header":         True,
    }
    with open(path, "w", encoding="utf-8") as f:
        f.write(format_frontmatter(meta) + raw)
    print(f"[frontmatter] 自動產生並寫回 {os.path.basename(path)}")
    return meta, raw


# ---------------------------------------------------------------------------
# 載入並解析文章
# ---------------------------------------------------------------------------

def load_post(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        raw = f.read()

    meta, body = parse_frontmatter(raw)
    if not meta:
        meta, body = generate_and_write_frontmatter(path, raw)

    title = str(meta.get("title") or extract_h1(body))
    if meta.get("stripH1Header", False):
        body = strip_h1(body)

    body_html = md_to_html(body.strip())

    raw_cats = meta.get("categories") or []
    if isinstance(raw_cats, str):
        categories = [c.strip() for c in raw_cats.split(",") if c.strip()]
    else:
        categories = [str(c) for c in raw_cats if c]

    date_created = None
    raw_date = str(meta.get("postDate") or "")
    if raw_date:
        try:
            clean = re.sub(r"(\.\d{6})\d+$", r"\1", raw_date)
            date_created = xmlrpc.client.DateTime(datetime.fromisoformat(clean))
        except ValueError:
            pass

    return {
        "title":        title,
        "description":  body_html,
        "mt_excerpt":   str(meta.get("abstract") or ""),
        "mt_keywords":  str(meta.get("keywords") or ""),
        "categories":   categories,
        "date_created": date_created,
        "post_id":      str(meta.get("postId") or "").strip() or None,
        "publish":      str(meta.get("postStatus") or "").lower() == "publish",
    }


# ---------------------------------------------------------------------------
# MetaWeblog 操作
# ---------------------------------------------------------------------------

def get_blogid(proxy, username: str, password: str) -> str:
    blogs = proxy.blogger.getUsersBlogs("", username, password)
    if not blogs:
        raise RuntimeError("找不到任何 blog，請確認帳密正確")
    blog = blogs[0]
    print(f"Blog：{blog['blogName']}  (blogid={blog['blogid']})")
    return blog["blogid"]


def build_post_struct(info: dict) -> dict:
    struct = {"title": info["title"], "description": info["description"]}
    if info["mt_excerpt"]:
        struct["mt_excerpt"] = info["mt_excerpt"]
    if info["mt_keywords"]:
        struct["mt_keywords"] = info["mt_keywords"]
    if info["categories"]:
        struct["categories"] = info["categories"]
    if info["date_created"]:
        struct["dateCreated"] = info["date_created"]
    return struct


def fetch_posts(proxy, blogid: str, username: str, password: str,
                size: int, fetch_all: bool) -> list:
    """
    getRecentPosts(blogid, user, pass, n) 只支援「取最新 n 筆」，無 offset。
    - fetch_all=False：直接取最新 size 筆
    - fetch_all=True ：每次加一個 chunk 直到沒有新資料
    """
    if fetch_all:
        collected: list = []
        while True:
            posts = proxy.metaWeblog.getRecentPosts(blogid, username, password, len(collected) + size)
            new = posts[len(collected):]
            collected.extend(new)
            if len(new) < size:
                break
        return collected
    else:
        return proxy.metaWeblog.getRecentPosts(blogid, username, password, size)


def print_posts(posts: list, fetch_all: bool):
    if not posts:
        print("（無文章）")
        return

    print(f"{'#':>4}  {'日期':12}  {'postId':8}  {'標題'}")
    print("-" * 80)

    for i, p in enumerate(posts, start=1):
        ds = str(p.get("dateCreated", ""))
        date_str = f"{ds[0:4]}-{ds[4:6]}-{ds[6:8]}" if len(ds) >= 8 else "----/--/--"
        title   = p.get("title", "（無標題）")
        post_id = p.get("postid", "")
        print(f"{i:>4}  {date_str:12}  {post_id[:8]}  {title}")

    label = "全部" if fetch_all else "最新"
    print(f"\n{label} {len(posts)} 篇")


# ---------------------------------------------------------------------------
# 子命令：publish
# ---------------------------------------------------------------------------

def resolve_output_dir(output_dir: str) -> str:
    if os.path.isabs(output_dir):
        return output_dir
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), output_dir)


def cmd_publish(args, username: str, password: str):
    out = resolve_output_dir(args.output_dir)
    md_path = args.file or os.path.join(out, "blog.md")
    if not os.path.isfile(md_path):
        print(f"錯誤：找不到 {md_path}", file=sys.stderr)
        sys.exit(1)

    info = load_post(md_path)
    post_struct = build_post_struct(info)

    print(f"標題   ：{info['title']}")
    print(f"分類   ：{info['categories'] or '（未設定）'}")
    print(f"關鍵字 ：{info['mt_keywords'] or '（未設定）'}")
    print(f"內文   ：{len(info['description'])} chars")
    print(f"模式   ：{'公開' if info['publish'] else '草稿'}")

    proxy = xmlrpc.client.ServerProxy(API_URL)

    if info["post_id"]:
        print(f"動作   ：更新既有文章 (postId={info['post_id']})")
        ok = proxy.metaWeblog.editPost(info["post_id"], username, password, post_struct, info["publish"])
        print(f"\n✅ 更新成功！(ok={ok})")
        print(f"後台編輯：https://dotblogs.com.tw/{BLOG_URL}/admin/edit/{info['post_id']}")
    else:
        print("動作   ：新增文章")
        blogid = get_blogid(proxy, username, password)
        post_id = proxy.metaWeblog.newPost(blogid, username, password, post_struct, info["publish"])
        update_frontmatter_field(md_path, "postId", post_id)
        print(f"\n✅ 發布成功！post_id={post_id}")
        print(f"後台編輯：https://dotblogs.com.tw/{BLOG_URL}/admin/edit/{post_id}")
        print(f"postId 已寫回 {os.path.basename(md_path)}")


# ---------------------------------------------------------------------------
# 子命令：list
# ---------------------------------------------------------------------------

def cmd_list(args, username: str, password: str):
    proxy = xmlrpc.client.ServerProxy(API_URL)
    blogid = proxy.blogger.getUsersBlogs("", username, password)[0]["blogid"]
    posts = fetch_posts(proxy, blogid, username, password, size=args.size, fetch_all=args.all)
    print_posts(posts, fetch_all=args.all)


# ---------------------------------------------------------------------------
# 子命令：get（下載文章 → .md）
# ---------------------------------------------------------------------------

def _safe_filename(title: str) -> str:
    """將標題轉成合法檔名（保留中文，替換不合法字元）。"""
    name = re.sub(r'[\\/:*?"<>|]', "-", title)
    name = re.sub(r'\s+', " ", name).strip()
    return name[:80] or "untitled"


def _parse_xmlrpc_date(raw) -> str:
    """xmlrpc.DateTime（20260509T06:56:56）→ ISO 格式字串。"""
    ds = str(raw)  # e.g. "20260509T06:56:56"
    if len(ds) >= 8:
        date_part = f"{ds[0:4]}-{ds[4:6]}-{ds[6:8]}"
        time_part = ds.split("T")[1] if "T" in ds else "00:00:00"
        return f"{date_part}T{time_part}.0000000"
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S.0000000")


def download_post(proxy, post_id: str, username: str, password: str,
                  out_dir: str) -> str:
    """下載單篇文章，轉換後存為 <out_dir>/<title>.md，回傳存檔路徑。"""
    post = proxy.metaWeblog.getPost(post_id, username, password)

    title      = post.get("title", "untitled")
    html_body  = post.get("description", "")
    html_abst  = post.get("mt_excerpt", "")
    keywords   = post.get("mt_keywords", "")
    categories = post.get("categories", [])
    date_str   = _parse_xmlrpc_date(post.get("dateCreated", ""))

    # HTML → Markdown
    body_md = html2md(html_body, heading_style="ATX", bullets="-").strip()

    meta = {
        "title":                 title,
        "abstract":              html_abst,
        "keywords":              keywords,
        "categories":            ", ".join(categories) if categories else "",
        "weblogName":            BLOG_NAME,
        "postId":                post_id,
        "postDate":              date_str,
        "postStatus":            "",
        "dontInferFeaturedImage": False,
        "stripH1Header":         True,
    }

    os.makedirs(out_dir, exist_ok=True)
    filename = _safe_filename(title) + ".md"
    filepath = os.path.join(out_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(format_frontmatter(meta))
        f.write(f"# {title}\n\n")
        f.write(body_md + "\n")

    return filepath


def cmd_get(args, username: str, password: str):
    proxy  = xmlrpc.client.ServerProxy(API_URL)
    out    = resolve_output_dir(args.output_dir)

    if not args.latest and not args.ids:
        print("錯誤：請指定 --ids 或 --latest", file=sys.stderr)
        sys.exit(1)

    if args.latest:
        blogid = proxy.blogger.getUsersBlogs("", username, password)[0]["blogid"]
        posts  = proxy.metaWeblog.getRecentPosts(blogid, username, password, args.latest)
        ids    = [p["postid"] for p in posts]
    else:
        ids = args.ids

    for pid in ids:
        path = download_post(proxy, pid, username, password, out)
        print(f"✅ {pid[:8]}  →  {path}")


# ---------------------------------------------------------------------------
# 主程式
# ---------------------------------------------------------------------------

def main():
    username = os.environ.get("BLOG_USER")
    # 優先從系統 keychain 取密碼，fallback 到環境變數
    password = keyring.get_password(KEYRING_SERVICE, "BLOG_PASSWORD") \
               or os.environ.get("BLOG_PASSWORD")

    if not username:
        print("錯誤：請設定 BLOG_USER 環境變數（或 .env）", file=sys.stderr)
        sys.exit(1)
    if not password:
        print(
            "錯誤：找不到密碼。請執行：\n"
            f"  python3 -c \"import keyring; keyring.set_password('{KEYRING_SERVICE}', 'BLOG_PASSWORD', '你的密碼')\"",
            file=sys.stderr,
        )
        sys.exit(1)

    parser = argparse.ArgumentParser(description="dotblogs MetaWebLog 工具")
    parser.add_argument(
        "--output-dir", "-o",
        default="output",
        help="blog .md 檔存放目錄（預設 output，可為絕對或相對路徑）",
    )
    sub = parser.add_subparsers(dest="cmd")

    # publish
    p_pub = sub.add_parser("publish", help="發布/更新文章")
    p_pub.add_argument("file", nargs="?", help="Markdown 檔案路徑（省略時用 <output-dir>/blog.md）")

    # list
    p_lst = sub.add_parser("list", help="列出最新文章")
    p_lst.add_argument("--size", type=int, default=10, help="取最新幾筆（預設 10）")
    p_lst.add_argument("--all", action="store_true", help="取回全部文章")

    # get
    p_get = sub.add_parser("get", help="下載文章轉存為 .md")
    p_get.add_argument("--ids", nargs="+", metavar="postId", help="指定 postId（可多個）")
    p_get.add_argument("--latest", type=int, metavar="N", help="下載最新 N 篇")

    args = parser.parse_args()

    # 未指定子命令時預設為 publish
    if args.cmd is None:
        args.cmd = "publish"
        args.file = None
        args.output_dir = args.output_dir  # 已由全域解析，保留即可

    if args.cmd == "publish":
        cmd_publish(args, username, password)
    elif args.cmd == "list":
        cmd_list(args, username, password)
    elif args.cmd == "get":
        cmd_get(args, username, password)


if __name__ == "__main__":
    main()
