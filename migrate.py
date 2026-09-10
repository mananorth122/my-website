import os
import re
import time
import json
import requests
from bs4 import BeautifulSoup

# ==========================================
# 処理対象の年月を指定
# ==========================================
TARGET_YEAR_MONTH = "2026-6"

SKIP_ENTRIES = []

OUTPUT_DIR = os.path.join("content", "day-log", TARGET_YEAR_MONTH)
os.makedirs(OUTPUT_DIR, exist_ok=True)

year, month = TARGET_YEAR_MONTH.split("-")
index_path = os.path.join(OUTPUT_DIR, "_index.md")
if not os.path.exists(index_path):
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(f'+++\ntitle = "{year}年{int(month)}月"\ndate = {year}-{int(month):02d}-01\ndraft = false\n+++\n')

TARGET_URL = f"https://sites.google.com/view/mana-kitazawa/day-log/{TARGET_YEAR_MONTH}?authuser=0"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def get_article_links():
    print(f"{TARGET_YEAR_MONTH} の月別ページから全記事リンクを収集中: {TARGET_URL}")
    res = requests.get(TARGET_URL, headers=headers)
    links = []
    if res.status_code == 200:
        soup = BeautifulSoup(res.text, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "day-log" in href:
                full_url = "https://sites.google.com" + href if href.startswith("/") else href
                clean_url = full_url.split("?")[0].rstrip("/")
                base_clean = TARGET_URL.split("?")[0].rstrip("/")
                if clean_url != base_clean and clean_url not in [l.split("?")[0].rstrip("/") for l in links]:
                    links.append(full_url)
    return links

def process_element_formatting(el):
    """ハイライト(<mark>/背景色)および太字(<b>/<strong>)の保持処理"""
    for tag in el.find_all(["mark", "span"]):
        style = tag.get("style", "").lower()
        if tag.name == "mark" or "background-color" in style or "background" in style:
            tag.replace_with(f"<mark>{tag.text}</mark>")
            
    for tag in el.find_all(["b", "strong"]):
        tag.replace_with(f"**{tag.text}**")
        
    return el.get_text().strip()

def format_references(ref_lines):
    """
    1行に結合された参考文献を検出し、自然な区切りで改行を入れる強化処理
    """
    # 複数ブロックを一度結合
    raw_ref_text = "\n".join(ref_lines)
    
    # 1. 著者名 + 年号 (例: 野村益寛 (2014) / Tanaka, J. (2020) / 全 (2010)) の直前で改行
    text = re.sub(r'([^\n])\s*([A-Z\u3040-\u30ff\u4e00-\u9faf]+(?:\s+[A-Z\u3040-\u30ff\u4e00-\u9faf]+)*\s*[\(\（]\d{4}[\)\）])', r'\1\n\2', raw_ref_text)
    
    # 2. 箇条書き番号 (例: [1], 1., ①) の直前で改行
    text = re.sub(r'([^\n])\s*(\[\d+\]|\d+\.\s+|[①-⑳])', r'\1\n\2', text)
    
    # 3. URL (http:// や https://) の直前で改行
    text = re.sub(r'([^\n])\s*(https?://[^\s]+)', r'\1\n\2', text)

    # 各行の整形とMarkdown改行（末尾スペース2つ）の適用
    cleaned_lines = []
    for line in text.split("\n"):
        line_str = line.strip()
        if line_str:
            cleaned_lines.append(line_str)
            
    return "  \n".join(cleaned_lines)

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
        text = process_element_formatting(el)
        if text and not any(skip in text for skip in ["Skip to", "Search this site", "Embedded Files", "Report abuse", "Page details"]):
            if text not in raw_blocks:
                raw_blocks.append(text)

    full_text = "\n\n".join(raw_blocks)

    title_match = re.search(r"(#(\d+)[^\n\r]+)", full_text)
    if not title_match:
        return False

    full_title = title_match.group(1).strip().split("\n")[0]
    full_title = re.sub(r"</?mark>", "", full_title)
    full_title = re.sub(r"\*\*", "", full_title)
    
    entry_num = title_match.group(2)

    if entry_num in SKIP_ENTRIES:
        print(f"⏭️ スキップ対象 (#{entry_num}): {full_title}")
        return False

    date_match = re.search(r"-(\d{4})-(\d{1,2})-(\d{1,2})$", url.split("?")[0])
    if date_match:
        y, m, d = date_match.groups()
        date_str = f"{y}-{int(m):02d}-{int(d):02d}"
    else:
        date_str = f"{year}-{int(month):02d}-01"

    # 全文から keywords [...] を全件抽出
    keywords = []
    kw_matches = re.findall(r"keywords\s*((?:\[.*?\]\s*)+)", full_text, re.IGNORECASE)
    for kw_str in kw_matches:
        found = re.findall(r"\[(.*?)\]", kw_str)
        for k in found:
            k_clean = k.strip(" '\"[]")
            k_clean = re.sub(r"</?mark>", "", k_clean)
            if k_clean and k_clean not in keywords:
                keywords.append(k_clean)

    main_body = []
    reference_lines = []
    capture = False
    in_reference = False

    for block in raw_blocks:
        if full_title in block or f"#{entry_num}" in block:
            capture = True
            continue
            
        if capture:
            block_clean = re.sub(r"keywords\s*(?:\[.*?\]\s*)+", "", block, flags=re.IGNORECASE).strip()
            if not block_clean:
                continue

            ref_match = re.search(r"(参考|References)", block_clean)
            if ref_match:
                split_idx = ref_match.start()
                body_part = block_clean[:split_idx].strip()
                ref_part = block_clean[split_idx:].strip()

                if body_part and not in_reference:
                    main_body.append(body_part)

                in_reference = True
                cleaned_ref = re.sub(r"^(参考|References)\s*", "", ref_part).strip()
                if cleaned_ref:
                    reference_lines.append(cleaned_ref)
                continue

            if in_reference:
                reference_lines.append(block_clean)
            else:
                main_body.append(block_clean)

    body_content = "\n\n".join(main_body)

    # フッター組み立て
    formatted_footer = f"\n\n{{{{< like id=\"day-log-{entry_num}\" >}}}}\n\n---"

    if reference_lines:
        ref_text_block = format_references(reference_lines)
        formatted_footer += f"\n\n**参考**  \n{ref_text_block}"

    if keywords:
        kw_display = "、".join(keywords)
        formatted_footer += f"\n\n**Keywords**  \n{kw_display}"

    # TOML構成エラー防止のエスケープ処理
    safe_title = json.dumps(full_title, ensure_ascii=False)
    kw_formatted = json.dumps(keywords, ensure_ascii=False)

    md_content = f"""+++
title = {safe_title}
date = {date_str}
draft = false
url = "/day-log/{entry_num}/"
keywords = {kw_formatted}
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
    print(f"発見された {TARGET_YEAR_MONTH} の記事数: {len(links)} 件\n")
    
    success = 0
    for link in links:
        if parse_daylog_article(link):
            success += 1
        time.sleep(1)

    print(f"\n🎉 {TARGET_YEAR_MONTH} 分の変換完了! 合計 {success} 件の処理が終わりました。")