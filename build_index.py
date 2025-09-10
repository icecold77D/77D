# -*- coding: utf-8 -*-
"""
生成根目錄 index.html：
- 掃描當前目錄下的所有子資料夾（不含以 . 或 _ 開頭）
- 每個資料夾中尋找名為 'title' 的圖片（支援 jpg/jpeg/png/webp/gif，大小寫不限）
- 產生一個卡片牆頁面，依資料夾名稱（預期日期開頭）由新到舊排序
- 點擊縮圖開啟該資料夾的 _index.html；若不存在，則開啟該資料夾
"""

from pathlib import Path
from urllib.parse import quote
import re
import datetime

# ========== 可調參數 ==========
IMAGE_BASENAME = "title"
IMAGE_EXTS = [".jpg", ".jpeg", ".png", ".webp", ".gif"]
EXCLUDE_DIR_PREFIXES = (".", "_")   # 例如 .git、_assets
ONLY_IMMEDIATE_CHILDREN = True      # 只掃描第一層子資料夾
SORT_DESC = True                    # True=新到舊 (Z→A)
OUTPUT_FILE = "index.html"
PAGE_TITLE = "Gallery"
SITE_HEADER = "📸 My Daily Drops"
SITE_SUBTITLE = "點縮圖進入各日的 _index.html"
CARD_MAX_WIDTH = 360                # 單張卡片最大寬度(px)
# =================================

def has_title_image(folder: Path):
    """回傳 (image_path|None)。在 folder 找檔名為 title 的圖片。"""
    for ext in IMAGE_EXTS:
        p = folder / f"{IMAGE_BASENAME}{ext}"
        if p.exists():
            return p
        # 也容忍大小寫不同
        for f in folder.iterdir():
            if f.is_file() and f.suffix.lower() == ext and f.stem.lower() == IMAGE_BASENAME:
                return f
    return None

def link_target(folder: Path):
    """優先連到 _index.html；若無則回資料夾本身。"""
    idx = folder / "_index.html"
    return idx if idx.exists() else folder

def looks_like_yyyymmdd_prefix(name: str):
    """粗略檢查是否以 YYYYMMDD 開頭，回傳 (bool, key) 供排序。"""
    m = re.match(r"^(\d{8})", name)
    if not m:
        return False, name
    ymd = m.group(1)
    try:
        dt = datetime.datetime.strptime(ymd, "%Y%m%d").date()
        # 排序鍵：日期 + 原始名，確保穩定
        return True, (dt, name)
    except ValueError:
        return False, name

def collect_entries(root: Path):
    """蒐集每個子資料夾的封面與連結。"""
    folders = []
    if ONLY_IMMEDIATE_CHILDREN:
        candidates = [p for p in root.iterdir() if p.is_dir()]
    else:
        candidates = [p for p in root.rglob("*") if p.is_dir() and p != root]

    for d in candidates:
        if d.name.startswith(EXCLUDE_DIR_PREFIXES):
            continue
        img = has_title_image(d)
        if not img:
            continue
        href = link_target(d)
        folders.append({
            "name": d.name,
            "dir": d,
            "img": img,
            "href": href
        })
    # 排序：若有 YYYYMMDD 開頭，依日期排序；否則用字典序
    def sort_key(item):
        ok, key = looks_like_yyyymmdd_prefix(item["name"])
        if ok:
            # 讓日期較新的排前面 -> 取日期做 key
            return (key[0], key[1])
        return (datetime.date(1900,1,1), item["name"])  # 非日期開頭排在最後

    folders.sort(key=sort_key, reverse=SORT_DESC)
    return folders

def build_html(entries):
    """產生單檔 index.html 內容。"""
    cards_html = []
    for e in entries:
        img_rel = e["img"].relative_to(Path.cwd())
        href_rel = e["href"].relative_to(Path.cwd())
        # URL encode（避免空白或中文路徑出包）
        img_url = quote(str(img_rel).replace("\\", "/"))
        href_url = quote(str(href_rel).replace("\\", "/"))
        alt_text = e["name"]

        cards_html.append(f"""
        <a class="card" href="{href_url}">
          <figure>
            <img src="{img_url}" alt="{alt_text}" loading="lazy" />
            <figcaption>{alt_text}</figcaption>
          </figure>
        </a>
        """.strip())

    cards = "\n".join(cards_html) if cards_html else "<p>目前沒有找到任何含 title 圖片的子資料夾。</p>"

    return f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{PAGE_TITLE}</title>
<meta name="robots" content="index,follow">
<style>
:root {{
  --bg: #0b0b0c;
  --fg: #f4f4f5;
  --muted: #a1a1aa;
  --card: #151518;
  --accent: #8b5cf6;
  --maxw: {CARD_MAX_WIDTH}px;
}}
* {{ box-sizing: border-box; }}
html, body {{
  margin: 0; padding: 0; background: var(--bg); color: var(--fg);
  font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, "Noto Sans", "Helvetica Neue", Arial, "Apple Color Emoji", "Segoe UI Emoji";
}}
header {{
  padding: 24px 16px;
  position: sticky; top: 0; backdrop-filter: blur(8px);
  background: linear-gradient(to bottom, rgba(11,11,12,0.8), rgba(11,11,12,0.2) 80%, transparent);
  z-index: 10;
  border-bottom: 1px solid rgba(255,255,255,0.05);
}}
h1 {{ margin: 0 0 6px 0; font-size: 20px; letter-spacing: .3px; }}
.sub {{ color: var(--muted); font-size: 13px; }}
.searchbar {{
  margin-top: 12px; display: flex; gap: 8px; align-items: center;
}}
input[type="search"] {{
  flex: 1; padding: 10px 12px; border-radius: 12px; border: 1px solid #26262b; background: #0f0f12; color: var(--fg);
  outline: none;
}}
main {{
  padding: 20px 10px 40px;
  max-width: 1300px; margin: 0 auto;
}}
.grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(var(--maxw), 1fr));
  gap: 16px;
}}
.card {{
  display: block; background: var(--card); border: 1px solid #232329; border-radius: 16px; overflow: hidden;
  text-decoration: none; color: inherit;
  transition: transform .15s ease, border-color .2s ease, box-shadow .2s ease;
}}
.card:hover {{
  transform: translateY(-2px);
  border-color: #3a3a45;
  box-shadow: 0 10px 24px rgba(0,0,0,.35);
}}
figure {{ margin: 0; }}
img {{
  display: block; width: 100%; height: auto; object-fit: cover; aspect-ratio: 16/9; background: #0f0f12;
}}
figcaption {{
  padding: 10px 12px;
  font-size: 14px; color: var(--fg); border-top: 1px solid #232329;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}}
.badge {{
  display: inline-flex; align-items: center; gap: 6px;
  font-size: 12px; color: var(--muted);
  padding: 4px 8px; border: 1px solid #26262b; border-radius: 999px;
}}
.footer {{
  text-align: center; color: var(--muted); font-size: 12px; padding: 24px 10px 40px;
}}
.hidden {{ display:none !important; }}
</style>
</head>
<body>
<header>
  <div class="head">
    <h1>{SITE_HEADER}</h1>
    <div class="sub">{SITE_SUBTITLE}</div>
    <div class="searchbar">
      <span class="badge">🔎 搜尋資料夾</span>
      <input id="q" type="search" placeholder="輸入關鍵字（例如 20250910 或 github）…" />
    </div>
  </div>
</header>

<main>
  <div id="grid" class="grid">
    {cards}
  </div>
</main>

<div class="footer">Generated by build_index.py</div>

<script>
const q = document.getElementById('q');
const grid = document.getElementById('grid');

q?.addEventListener('input', (e) => {{
  const term = (e.target.value || '').trim().toLowerCase();
  const cards = grid.querySelectorAll('.card');
  if (!term) {{
    cards.forEach(c => c.classList.remove('hidden'));
    return;
  }}
  cards.forEach(c => {{
    const cap = c.querySelector('figcaption')?.textContent?.toLowerCase() || '';
    if (cap.includes(term)) {{
      c.classList.remove('hidden');
    }} else {{
      c.classList.add('hidden');
    }}
  }});
}});
</script>
</body>
</html>
"""

def main():
    root = Path.cwd()
    entries = collect_entries(root)
    html = build_html(entries)
    (root / OUTPUT_FILE).write_text(html, encoding="utf-8")
    print(f"✅ 生成完成：{OUTPUT_FILE}，共 {len(entries)} 個卡片。")

if __name__ == "__main__":
    main()
