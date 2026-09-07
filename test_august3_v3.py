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
    
    for ignore_tag in soup.find_all(["nav", "header", "footer", "script", "style"]):
        ignore_tag.decompose()

    raw_blocks = []
    for el in soup.find_all(["h1", "h2", "h3", "p", "blockquote", "li"]):
        text = el.get_text().strip()
        if text and not any(skip in text for skip in ["Skip to", "Search this site", "Embedded Files", "Report abuse", "Page details"]):
            if text not in raw_blocks:
                raw_blocks.append(text)

    full_text = "\n\n".join(raw_blocks)

    # 1. タイトルと記事番号の抽出
    title_match = re.search(r"(#(\d+)[^\n\r]+)", full_text)
    if not title_match:
        return False

    full_title = title_match.group(1).strip().split("\n")[0]
    entry_num = title_match.group(2)

    # 2. 日付の抽出 (2026-08-01 形式)
    date_match = re.search(r"-(\d{4})-(\d{1,2})-(\d{1,2})$", url.split("?")[0])
    if date_match:
        y, m, d = date_match.groups()
        date_str = f"{y}-{int(m):02d}-{int(d):02d}"
    else:
        date_str = "2026-08-01"

    # 3. キーワードの抽出
    keywords = []
    kw_match = re.search(r"keywords\s*\[(.*?)\]", full_text, re.IGNORECASE)
    if kw_match:
        raw_kw = kw_match.group(1)
        keywords = [k.strip(" '\"[]") for k in re.split(r"\]\s*\[|,", raw_kw) if k.strip()]

    # 4. 本文・参考（文献）・フッター文脈の切り分け
    main_body = []
    reference_lines = []
    capture = False
    in_reference = False

    for block in raw_blocks:
        if full_title in block or f"#{entry_num}" in block:
            capture = True
            continue
        if "keywords" in block.lower():
            break
        if capture:
            # 「参考」または「References」の検出
            if block.startswith("参考") or block.startswith("References"):
                in_reference = True
                # 「参考」ヘッダーのすぐ後に記述が続いている場合の処理
                ref_text = re.sub(r"^(参考|References)\s*", "", block).strip()
                if ref_text:
                    reference_lines.append(ref_text)
                continue

            if in_reference:
                reference_lines.append(block)
            else:
                main_body.append(block)

    # 本文の結合
    body_content = "\n\n".join(main_body)

    # 5. 「きれいなバージョン」の末尾構造を組み立て
    formatted_footer = f"\n\n{{{{< like id=\"day-log-{entry_num}\" >}}}}\n\n---"

    if reference_lines:
        ref_text_block = "\n".join(reference_lines)
        formatted_footer += f"\n\n**参考**  \n{ref_text_block}"

    if keywords:
        kw_display = "".join([f"[{k}]" for k in keywords])
        formatted_footer += f"\n\n**Keywords**  \n{kw_display}"

    # Front Matter の整形
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

    print(f"✅ 【パーフェクト出力】 Day Log #{entry_num} -> {filepath}")
    return True

if __name__ == "__main__":
    print("--- 8月記事の抽出・整形（完全版）を実行中 ---")
    links = get_august_links()
    
    success = 0
    for link in links:
        if success >= 3:
            break
        print(f"処理中: {link}")
        if parse_daylog_article(link):
            success += 1
        time.sleep(1)

    print(f"\n--- 完了: {success} 件のMarkdownを完璧なフォーマットで生成しました ---")