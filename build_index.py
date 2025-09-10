# -*- coding: utf-8 -*-
"""
build_index.py
掃描當前目錄下的子資料夾，尋找每個資料夾中的 'title' 圖片（jpg/png/webp/gif），
輸出 data.json 與 index.html（首頁），並建立 .nojekyll 以避免 GitHub Pages 忽略底線檔案。

用法：
    python build_index.py
"""

from __future__ import annotations
from pathlib import Path
import json
import re
import datetime as _dt
import webbrowser
import sys

# ===== 可調參數 =====
IMAGE_BASENAME = "title"
IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".gif")
EXCLUDE_DIR_PREFIXES = (".", "_")     # 跳過 .git、_assets……
ONLY_IMMEDIATE_CHILDREN = True        # True=只掃描第一層子資料夾
SORT_DESC = True                      # True=新到舊
OUTPUT_JSON = "data.json"
OUTPUT_HTML = "index.html"            # 建議首頁用 index.html (非 _index.html)
CREATE_NOJEKYLL = True                # 在根目錄建立 .nojekyll
AUTO_OPEN_AFTER_BUILD = True          # 生成後自動用瀏覽器開啟 index.html
PAGE_TITLE = "我的縮圖首頁"
SITE_HEADER = "📸 我的首頁"
SITE_SUB = "點縮圖會開子資料夾的 _index.html"
# ====================


ROOT = Path.cwd()


def find_title_image(folder: Path) -> Path | None:
    """在 folder 找檔名為 'title' 的圖片（大小寫不拘、副檔名依 IMAGE_EXTS）。"""
    # 先試精準組合
    for ext in IMAGE_EXTS:
        candidate = folder / f"{IMAGE_BASENAME}{ext}"
        if candidate.exists():
            return candidate
    # 再寬鬆大小寫比對
    for f in folder.iterdir():
        if f.is_file() and f.suffix.lower() in IMAGE_EXTS and f.stem.lower() == IMAGE_BASENAME:
            return f
    return None


def link_target(folder: Path) -> Path:
    """優先連到 _index.html；若不存在，連到資料夾本身。"""
    idx = folder / "_index.html"
    return idx if idx.exists() else folder


_date_re = re.compile(r"^(\d{8})")


def sort_key_for_dir(d: Path):
    """以資料夾名稱的 YYYYMMDD 前綴為優先排序鍵；無則用很早的日期，最後再以名稱排序。"""
    m = _date_re.match(d.name)
    if m:
        ymd = m.group(1)
        try:
            dt = _dt.datetime.strptime(ymd, "%Y%m%d").date()
            return (dt, d.name)
        except ValueError:
            pass
    # 非日期開頭 → 排到較後面
    return (_dt.date(1900, 1, 1), d.name)


def collect_entries(root: Path):
    """回傳 [{name, img, href}] 列表。img/href 皆為相對於 root 的 POSIX 路徑字串。"""
    if ONLY_IMMEDIATE_CHILDREN:
        candidates = [p for p in root.iterdir() if p.is_dir()]
    else:
        candidates = [p for p in root.rglob("*") if p.is_dir() and p != root]

    # 排除特定前綴資料夾
    candidates = [d for d in candidates if not d.name.startswith(EXCLUDE_DIR_PREFIXES)]

    # 依日期前綴排序
    candidates.sort(key=sort_key_for_dir, reverse=SORT_DESC)

    items = []
    for d in candidates:
        img = find_title_image(d)
        if not img:
            continue
        href_path = link_target(d)
        # 轉成相對於 root 的 POSIX 路徑（適合放在 JSON/HTML）
        img_rel = img.relative_to(root).as_posix()
        href_rel = href_path.relative_to(root).as_posix()
        # 如果是資料夾本身，補上尾斜線，瀏覽器顯示會更穩定
        if href_path.is_dir() and not href_rel.endswith("/"):
            href_rel += "/"

        items.append({
            "name": d.name,
            "img": img_rel,
            "href": href_rel,
        })
    return items


HTML_TEMPLATE = f"""<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{PAGE_TITLE}</title>
<style>
  body{{margin:0;background:#101012;color:#eee;font-family:ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto}}
  header{{padding:16px 12px;border-bottom:1px solid #26262b;position:sticky;top:0;background:#101012cc;backdrop-filter:blur(6px)}}
  h1{{margin:0;font-size:18px}}
  .muted{{color:#a1a1aa;font-size:12px}}
  .grid{{display:grid;gap:14px;padding:16px;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));max-width:1200px;margin:0 auto}}
  .card{{display:block;background:#19191e;border:1px solid #26262b;border-radius:14px;overflow:hidden;text-decoration:none;color:inherit}}
  .card img{{display:block;width:100%;aspect-ratio:16/9;object-fit:cover;background:#0f0f12}}
  .card span{{display:block;padding:10px 12px;font-size:14px;border-top:1px solid #26262b;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
</style>
</head>
<body>
<header>
  <h1>{SITE_HEADER}</h1>
  <div class="muted">{SITE_SUB}</div>
</header>

<main class="grid" id="grid"></main>

<script>
(async () => {{
  const grid = document.getElementById('grid');
  const url = new URL('./{OUTPUT_JSON}', location.href);
  // 破快取參數
  url.searchParams.set('v', Date.now());
  let items = [];
  try {{
    const r = await fetch(url.toString(), {{ cache: 'no-store' }});
    if (!r.ok) throw new Error('HTTP ' + r.status);
    items = await r.json();
  }} catch (err) {{
    grid.innerHTML = '<p style="color:#f88">載入資料失敗：' + (err && err.message || err) + '</p>';
    return;
  }}
  if (!Array.isArray(items) || items.length === 0) {{
    grid.innerHTML = '<p class="muted">目前沒有可顯示的項目（確認資料夾內有 title.jpg / _index.html）。</p>';
    return;
  }}
  grid.innerHTML = '';
  for (const it of items) {{
    const a = document.createElement('a');
    a.className = 'card';
    a.href = it.href;
    a.innerHTML = `
      <img src="${{it.img}}" alt="${{it.name}}">
      <span>${{it.name}}</span>
    `;
    grid.appendChild(a);
  }}
}})();
</script>
</body>
</html>
"""


def write_json(items):
    ROOT.joinpath(OUTPUT_JSON).write_text(
        json.dumps(items, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def write_html():
    ROOT.joinpath(OUTPUT_HTML).write_text(HTML_TEMPLATE, encoding="utf-8")


def ensure_nojekyll():
    if CREATE_NOJEKYLL:
        p = ROOT / ".nojekyll"
        if not p.exists():
            p.write_text("", encoding="utf-8")


def main():
    items = collect_entries(ROOT)
    write_json(items)
    write_html()
    ensure_nojekyll()
    print(f"✅ 已生成 {OUTPUT_JSON}（{len(items)} 筆）與 {OUTPUT_HTML}")
    if AUTO_OPEN_AFTER_BUILD:
        try:
            webbrowser.open_new_tab((ROOT / OUTPUT_HTML).as_uri())
        except Exception:
            pass


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("❌ 發生錯誤：", e, file=sys.stderr)
        sys.exit(1)
