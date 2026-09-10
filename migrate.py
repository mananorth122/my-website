import os
import re
import time
import requests
from bs4 import BeautifulSoup

# ==========================================
# 移行したい年月を指定 (例: "2025-8", "2025-9", "2026-1" など)
# ==========================================
TARGET_YEAR_MONTH = "2025-8"  # ここを毎月打ち替えて実行

# 出力先ディレクトリの設定
OUTPUT_DIR = os.path.join("content", "day-log", TARGET_YEAR_MONTH)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 月別 _index.md の自動作成
year, month = TARGET_YEAR_MONTH.split("-")
index_path = os.path.join(OUTPUT_DIR, "_index.md")
if not os.path.exists(index_path):
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(f'+++\ntitle = "{year}年{month}月"\ndraft = false\n+++\n')

BASE_TARGET_URL = f"https://sites.google.com/view/mana-kitazawa/day-log/{TARGET_YEAR_MONTH}"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def get_article_links():
    print(f"[{TARGET_YEAR_MONTH}] 記事一覧を取得中: {BASE_TARGET_URL}")
    res = requests.get(BASE_TARGET_URL, headers=headers)
    links = []
    if res.status_code == 200:
        soup = BeautifulSoup(res.text, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "/day-log/" in href and (f"/{TARGET_YEAR_MONTH}/" in href or f"/{year}-{month}/" in href):
                full_url = "https://sites.google.com" + href if href.startswith("/") else href
                if not full_url.endswith(f"/day-log/{TARGET_YEAR_MONTH}") and full_url not in links:
                    links.append(full_url)
    return links

def process_element_html(el):
    """ 要素内のハイライト背景色・markタグを標準的な <mark> に置換して抽出 """
    # Google Sites の蛍光ペン（style属性の background）または mark タグを認識
    for span in el.find_all(["span", "mark"]):
        style = span.get("style", "")
        if "background" in style or span.name == "mark":
            span.string = f"__MARK_START__{span.get_text()}__MARK_END__"

    text = el.get_text().strip()
    # 独自のプレースホルダーを実際の <mark> タグに変換
    text = text.replace("__MARK_START__", "<mark>").replace("__MARK_END__", "</mark>")
    return text

def parse_daylog_article(url):
    res = requests.get(url, headers=headers)
    if res.status_code != 200:
        print(f"❌ 取得失敗 Status {res.status_code}: {url}")
        return False

    soup = BeautifulSoup(res.text, "html.parser")
    
    for ignore_tag in soup.find_all(["nav", "header", "footer", "script", "style"]):
        ignore_tag.decompose()

    raw_blocks = []
    for el in soup.find_all(["h1", "h2", "h3", "p", "blockquote", "li"]):
        text = process_element_html(el)
        if text and not any(skip in text for skip in ["Skip to", "Search this site", "Embedded Files", "Report abuse", "Page details"]):
            if text not in raw_blocks:
                raw_blocks.append(text)

    full_text = "\n\n".join(raw_blocks)

    # タイトルと記事番号の抽出
    title_match = re.search(r"(#(\d+)[^\n\r]+)", full_text)
    if not title_match:
        return False

    full_title = title_match.group(1).strip().split("\n")[0]
    entry_num = title_match.group(2)

    # 日付の抽出
    date_match = re.search(r"-(\d{4})-(\d{1,2})-(\d{1,2})$", url.split("?")[0])
    if date_match:
        y, m, d = date_match.groups()
        date_str = f"{y}-{int(m):02d}-{int(d):02d}"
    else:
        date_str = f"{year}-{int(month):02d}-01"

    # Keywordsの抽出
    keywords = []
    kw_match = re.search(r"keywords\s*\[(.*?)\]", full_text, re.IGNORECASE)
    if kw_match:
        raw_kw = kw_match.group(1)
        keywords = [k.strip(" '\"[]") for k in re.split(r"\]\s*\[|,", raw_kw) if k.strip()]

    # 本文・参考・キーワードの抽出判定
    main_body = []
    reference_lines = []
    capture = False
    in_reference = False

    for block in raw_blocks:
        if full_title in block or f"#{entry_num}" in block:
            capture = True
            continue
            
        if capture:
            # Keywordsのブロックに達したら本文・参考の取得を終了
            if re.match(r"^keywords", block, re.IGNORECASE):
                break

            # 「参考」または「References」が含まれる場合の判定（一体化対策）
            ref_header_match = re.match(r"^(参考|References)\s*(.*)", block, re.DOTALL)
            if ref_header_match:
                in_reference = True
                content_after_ref = ref_header_match.group(2).strip()
                if content_after_ref:
                    reference_lines.append(content_after_ref)
                continue

            if in_reference:
                reference_lines.append(block)
            else:
                main_body.append(block)

    body_content = "\n\n".join(main_body)

    # フッター組み立て
    formatted_footer = f"\n\n{{{{< like id=\"day-log-{entry_num}\" >}}}}\n\n---"

    if reference_lines:
        # 参考文献を確実に1行ずつ改行させるため <br> を挟む
        ref_text_block = "<br>\n".join(reference_lines)
        formatted_footer += f"\n\n**参考**  \n{ref_text_block}"

    if keywords:
        kw_display = ", ".join(keywords)
        formatted_footer += f"\n\n**Keywords**  \n{kw_display}"

    kw_formatted = ", ".join([f'"{k}"' for k in keywords])
    
    md_content = f"""+++
title = "{full_title}"
date = {date_str}
draft = false
keywords = [{kw_formatted}]
+++

{body_content}{formatted_footer}
"""

    filepath = os.path.join(OUTPUT_DIR, f"{entry_num}.md")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(md_content)

    print(f"✅ 生成完了: Day Log #{entry_num} (参考: {'あり' if reference_lines else 'なし'})")
    return True

if __name__ == "__main__":
    links = get_article_links()
    print(f"発見された記事数: {len(links)} 件\n")
    
    success = 0
    for link in links:
        if parse_daylog_article(link):
            success += 1
        time.sleep(1)

    print(f"\n🎉 {TARGET_YEAR_MONTH} 分の変換完了! 合計 {success} 件処理しました。")