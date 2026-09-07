import os
import re
import time
import requests
from bs4 import BeautifulSoup

OUTPUT_DIR = os.path.join("content", "day-log")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 8月の月別ページURL
AUGUST_URL = "https://sites.google.com/view/mana-kitazawa/day-log/2026-8"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def get_august_links():
    """8月ページから個別記事のリンクを取得"""
    print(f"8月のページにアクセス中: {AUGUST_URL}")
    res = requests.get(AUGUST_URL, headers=headers)
    links = []
    if res.status_code == 200:
        soup = BeautifulSoup(res.text, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "/day-log/2026-8/" in href:
                full_url = "https://sites.google.com" + href if href.startswith("/") else href
                if full_url not in links:
                    links.append(full_url)
    return links

def parse_daylog_article(url):
    """記事ページを読み込んでMarkdown生成"""
    res = requests.get(url, headers=headers)
    if res.status_code != 200:
        print(f"❌ 取得失敗 (Status: {res.status_code})")
        return False

    soup = BeautifulSoup(res.text, "html.parser")
    lines = [tag.get_text().strip() for tag in soup.find_all(["h1", "h2", "h3", "p", "div", "li"]) if tag.get_text().strip()]
    full_text = "\n".join(lines)

    # #数字 タイトルの抽出
    match = re.search(r"(#(\d+)\s+([^\n]+))", full_text)
    if not match:
        print("⚠️ タイトルパターンが見つかりませんでした")
        return False

    full_title = match.group(1).strip()
    entry_num = match.group(2)
    title_text = match.group(3).strip()

    # URL末尾から日付を正確に抽出 (/356-2026-8-1 -> 2026-08-01)
    date_match = re.search(r"-(\d{4})-(\d{1,2})-(\d{1,2})$", url.split("?")[0])
    if date_match:
        y, m, d = date_match.groups()
        date_str = f"{y}-{int(m):02d}-{int(d):02d}"
    else:
        date_str = "2026-08-01"

    # 本文の切り出し
    body_lines = []
    start = False
    for line in lines:
        if full_title in line or title_text in line:
            start = True
            continue
        if "keywords" in line.lower() or "北澤茉奈" in line and start:
            break
        if start and line not in body_lines:
            body_lines.append(line)

    body_content = "\n\n".join(body_lines)

    md_content = f"""+++
title = "{full_title}"
date = "{date_str}"
draft = false
url = "/day-log/{entry_num}/"
+++

{body_content}
"""

    filepath = os.path.join(OUTPUT_DIR, f"{entry_num}.md")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(md_content)

    print(f"✅ 【生成成功】: {filepath}")
    print(f"   タイトル: {full_title}")
    print(f"   日付: {date_str}")
    print(f"   本文文字数: {len(body_content)} 文字\n")
    return True

if __name__ == "__main__":
    print("--- 8月分の記事から先頭3件をテスト抽出 ---")
    links = get_august_links()
    print(f"8月ページ内で見つかった記事リンク: {len(links)} 件\n")

    success = 0
    for link in links:
        if success >= 3:
            break
        print(f"処理中: {link}")
        if parse_daylog_article(link):
            success += 1
        time.sleep(1)

    print(f"--- 8月分のテスト完了: {success} 件生成 ---")