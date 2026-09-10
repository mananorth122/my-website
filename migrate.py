import os
import re
import time
import requests
from bs4 import BeautifulSoup

OUTPUT_DIR = os.path.join("content", "day-log", "2025-8")
os.makedirs(OUTPUT_DIR, exist_ok=True)

index_path = os.path.join(OUTPUT_DIR, "_index.md")
if not os.path.exists(index_path):
    with open(index_path, "w", encoding="utf-8") as f:
        f.write('+++\ntitle = "2025年8月"\ndate = 2025-08-01\ndraft = false\n+++\n')

AUGUST_URL = "https://sites.google.com/view/mana-kitazawa/day-log/2025-8?authuser=0"
SKIP_ENTRIES = []

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def get_august_links():
    print(f"8月の月別ページから全記事リンクを収集中: {AUGUST_URL}")
    res = requests.get(AUGUST_URL, headers=headers)
    links = []
    if res.status_code == 200:
        soup = BeautifulSoup(res.text, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "day-log" in href:
                full_url = "https://sites.google.com" + href if href.startswith("/") else href
                clean_url = full_url.split("?")[0].rstrip("/")
                base_clean = AUGUST_URL.split("?")[0].rstrip("/")
                if clean_url != base_clean and clean_url not in [l.split("?")[0].rstrip("/") for l in links]:
                    links.append(full_url)
    return links

def process_element_formatting(el):
    for tag in el.find_all(["mark", "span"]):
        style = tag.get("style", "").lower()
        if tag.name == "mark" or "background-color" in style or "background" in style:
            tag.replace_with(f"<mark>{tag.text}</mark>")
            
    for tag in el.find_all(["b", "strong"]):
        tag.replace_with(f"**{tag.text}**")
        
    return el.get_text().strip()

def format_references(ref_lines):
    """
    1行に固まってしまった参考文献を著者名や年号、番号などを基準に改行を入れる処理
    """
    raw_ref_text = "\n".join(ref_lines)
    
    # 著者名 + 年号 (例: 野村益寛 (2014) や Tanaka, J. (2020) や [1] など) の直前で強制改行
    # パターン1: 「文字. (年)」や「名前 (年)」のパターンで分割
    formatted = re.sub(r'([^\n])\s*([A-Z\u3040-\u30ff\u4e00-\u9faf]+(?:\s+[A-Z\u3040-\u30ff\u4e00-\u9faf]+)*\s*[\(\（]\d{4}[\)\）])', r'\1\n\2', raw_ref_text)
    
    # パターン2: 「1. 」「[1] 」などの箇条書き番号の直前で改行
    formatted = re.sub(r'([^\n])\s*(\[\d+\]|\d+\.\s+)', r'\1\n\2', formatted)
    
    # Markdownの改行（末尾スペース2つ + 改行）に変換
    lines = [line.strip() for line in formatted.split("\n") if line.strip()]
    return "  \n".join(lines)

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
        date_str = "2025-08-01"

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

    formatted_footer = f"\n\n{{{{< like id=\"day-log-{entry_num}\" >}}}}\n\n---"

    if reference_lines:
        # ★文献ごとに自動改行してMarkdown表示を整える
        ref_text_block = format_references(reference_lines)
        formatted_footer += f"\n\n**参考**  \n{ref_text_block}"

    if keywords:
        kw_display = "、".join(keywords)
        formatted_footer += f"\n\n**Keywords**  \n{kw_display}"

    kw_formatted = ", ".join([f'"{k}"' for k in keywords])
    md_content = f"""+++
title = "{full_title}"
date = {date_str}
draft = false
url = "/day-log/{entry_num}/"
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
    links = get_august_links()
    print(f"発見された8月の記事数: {len(links)} 件\n")
    
    success = 0
    for link in links:
        if parse_daylog_article(link):
            success += 1
        time.sleep(1)

    print(f"\n🎉 8月分の変換完了! 合計 {success} 件の処理が終わりました。")