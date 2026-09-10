import os
import re
import time
import requests
from bs4 import BeautifulSoup

# ==========================================
# 移行したい年月を指定 (例: "2025-8", "2025-9", "2026-1" など)
# ==========================================
TARGET_YEAR_MONTH = "2025-8"  # ここを毎月打ち替えて実行

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

def parse_daylog_article(url):
    res = requests.get(url, headers=headers)
    if res.status_code != 200:
        print(f"❌ 取得失敗 Status {res.status_code}: {url}")
        return False

    soup = BeautifulSoup(res.text, "html.parser")
    
    # 不要な枠組みの除外
    for ignore_tag in soup.find_all(["nav", "header", "footer", "script", "style"]):
        ignore_tag.decompose()

    # ハイライト（background要素）を <mark> に置換
    for span in soup.find_all(["span", "mark"]):
        style = span.get("style", "")
        if "background" in style or span.name == "mark":
            span.string = f"<mark>{span.get_text()}</mark>"

    # 1行ずつ分解して取得
    raw_text = soup.get_text(separator="\n")
    lines = [line.strip() for line in raw_text.split("\n") if line.strip()]

    cleaned_lines = []
    for line in lines:
        if not any(skip in line for skip in ["Skip to", "Search this site", "Embedded Files", "Report abuse", "Page details", "mana-kitazawa"]):
            cleaned_lines.append(line)

    full_text = "\n".join(cleaned_lines)

    # タイトルと記事番号の抽出 (#6 など)
    title_match = re.search(r"(#(\d+)[^\n\r]+)", full_text)
    if not title_match:
        return False

    full_title = title_match.group(1).strip()
    entry_num = title_match.group(2)

    # 日付の抽出
    date_match = re.search(r"-(\d{4})-(\d{1,2})-(\d{1,2})$", url.split("?")[0])
    if date_match:
        y, m, d = date_match.groups()
        date_str = f"{y}-{int(m):02d}-{int(d):02d}"
    else:
        date_str = f"{year}-{int(month):02d}-01"

    # Keywords の抽出 ([ポライトネス] [フェイス] 形式を分解)
    keywords = []
    kw_match = re.search(r"keywords\s*(.*)", full_text, re.IGNORECASE)
    if kw_match:
        raw_kw = kw_match.group(1)
        keywords = [k.strip(" '\"[]") for k in re.split(r"\]\s*\[|,", raw_kw) if k.strip()]

    # 本文と参考の分類
    main_body = []
    reference_lines = []
    capture = False
    in_reference = False

    for line in cleaned_lines:
        if full_title in line or f"#{entry_num}" in line:
            capture = True
            continue

        if capture:
            # Keywords 行を見つけたらブロック抽出終了
            if re.match(r"^keywords", line, re.IGNORECASE):
                break

            # 「参考」または「References」行の検出
            ref_match = re.match(r"^(参考|References)\s*(.*)", line)
            if ref_match:
                in_reference = True
                after_text = ref_match.group(2).strip()
                if after_text:
                    reference_lines.append(after_text)
                continue

            if in_reference:
                reference_lines.append(line)
            else:
                main_body.append(line)

    body_content = "\n\n".join(main_body)

    # フッター整形 (最新仕様 #396 と完全統一)
    formatted_footer = f"\n\n{{{{< like id=\"day-log-{entry_num}\" >}}}}\n\n---"

    if reference_lines:
        # 参考部分: 末尾に <br> または半角スペース2つを付与して1行ずつ正しく改行
        ref_text_block = "<br>\n".join(reference_lines)
        formatted_footer += f"\n\n**参考**  \n{ref_text_block}"

    if keywords:
        # カンマ区切りのテキスト表記
        kw_display = ", ".join(keywords)
        formatted_footer += f"\n\n**Keywords**  \n{kw_display}"

    # Front Matter 用の JSON配列形式
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