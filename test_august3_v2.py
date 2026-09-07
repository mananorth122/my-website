import os
import re
import time
import requests
from bs4 import BeautifulSoup

OUTPUT_DIR = os.path.join("content", "day-log")
os.makedirs(OUTPUT_DIR, exist_ok=True)

AUGUST_URL = "https://sites.google.com/view/mana-kitazawa/day-log/2026-8"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def get_august_links():
    res = requests.get(AUGUST_URL, headers=headers)
    links = []
    if res.status_code == 200:
        soup = BeautifulSoup(res.text, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "/day-log/2026-8/" in href and re.search(r"\d+-\d{4}-", href):
                full_url = "https://sites.google.com" + href if href.startswith("/") else href
                if full_url not in links:
                    links.append(full_url)
    return links

def parse_daylog_article(url):
    res = requests.get(url, headers=headers)
    if res.status_code != 200:
        return False

    soup = BeautifulSoup(res.text, "html.parser")
    
    # 1. ナビゲーションやフッターなどシステム要素を削除
    for ignore_tag in soup.find_all(["nav", "header", "footer", "script", "style"]):
        ignore_tag.decompose()

    # 2. 本文エリアの要素から段落を抽出（HTMLタグの境界でしっかり改行させる）
    raw_blocks = []
    for el in soup.find_all(["h1", "h2", "h3", "p", "blockquote", "li"]):
        text = el.get_text().strip()
        # システム系UI文字列の除外フィルター
        if text and not any(skip in text for skip in ["Skip to", "Search this site", "Embedded Files", "Report abuse", "Page details"]):
            if text not in raw_blocks:
                raw_blocks.append(text)

    full_text = "\n\n".join(raw_blocks)

    # 3. タイトルの切り出し (#256 タイトル名)
    title_match = re.search(r"(#(\d+)[^\n\r]+)", full_text)
    if not title_match:
        return False

    full_title = title_match.group(1).strip()
    entry_num = title_match.group(2)
    
    # タイトル部分に本文が連結してしまっている場合のクリーンアップ
    # 例: "#256 ポリアンナの原則" だけを抽出（最初の改行まで）
    full_title = full_title.split("\n")[0]
    
    # 4. 日付の抽出
    date_match = re.search(r"-(\d{4})-(\d{1,2})-(\d{1,2})$", url.split("?")[0])
    if date_match:
        y, m, d = date_match.groups()
        date_str = f"{y}-{int(m):02d}-{int(d):02d}"
    else:
        date_str = "2026-08-01"

    # 5. キーワードの抽出と整形
    keywords = []
    kw_match = re.search(r"keywords\s*\[(.*?)\]", full_text, re.IGNORECASE)
    if kw_match:
        raw_kw = kw_match.group(1)
        keywords = [k.strip(" '\"[]") for k in re.split(r"\]\s*\[|,", raw_kw) if k.strip()]

    # 6. 本文の整理（タイトル以降〜keywords以前の文章を取得）
    body_lines = []
    capture = False

    for block in raw_blocks:
        if full_title in block or f"#{entry_num}" in block:
            capture = True
            continue
        if "keywords" in block.lower():
            break
        if capture:
            # 引用・英語文言などの整形
            if block.startswith("To elucidate") or block.startswith("The influence"):
                body_lines.append(f"> {block}")
            else:
                body_lines.append(block)

    body_content = "\n\n".join(body_lines)
    kw_formatted = ", ".join([f'"{k}"' for k in keywords])

    # 7. Hugo用 Markdown ファイルの生成
    md_content = f"""+++
title = "{full_title}"
date = "{date_str}"
draft = false
url = "/day-log/{entry_num}/"
keywords = [{kw_formatted}]
+++

{body_content}
"""

    filepath = os.path.join(OUTPUT_DIR, f"{entry_num}.md")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(md_content)

    print(f"✅ 【修正成功】 Day Log #{entry_num}")
    print(f"   タイトル: {full_title}")
    print(f"   日付: {date_str}")
    print(f"   キーワード: {keywords}\n")
    return True

if __name__ == "__main__":
    print("--- 改良版スクリプトで8月記事の抽出を実行中 ---")
    links = get_august_links()
    
    success = 0
    for link in links:
        if success >= 3:
            break
        print(f"処理中: {link}")
        if parse_daylog_article(link):
            success += 1
        time.sleep(1)

    print(f"--- 完了: {success} 件のクリーンなMarkdownを生成しました ---")