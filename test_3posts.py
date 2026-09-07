import os
import re
import time
import requests
from bs4 import BeautifulSoup

OUTPUT_DIR = os.path.join("content", "day-log")
os.makedirs(OUTPUT_DIR, exist_ok=True)

BASE_SITE = "https://sites.google.com/view/mana-kitazawa/day-log"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

# テスト対象の最新3件のURL
test_urls = [
    f"{BASE_SITE}/2026-9/387-2026-9-1",
    f"{BASE_SITE}/2026-9/386-2026-8-31",
    f"{BASE_SITE}/2026-9/385-2026-8-30",
]

print("--- お試し3件の移行を開始します ---")

for url in test_urls:
    print(f"\nアクセス中: {url}")
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code != 200:
            print(f"❌ 取得失敗 (Status: {res.status_code})")
            continue

        soup = BeautifulSoup(res.text, "html.parser")
        page_text = soup.get_text("\n")

        match = re.search(r"(#(\d+)\s+([^\n]+))", page_text)
        if not match:
            print("⚠️ 記事タイトル構造が見つかりませんでした")
            continue

        full_title = match.group(1).strip()
        entry_num = match.group(2)
        title_text = match.group(3).strip()

        date_match = re.search(r"(\d{4}[-/.]\d{1,2}[-/.]\d{1,2})", page_text)
        date_str = date_match.group(1).replace(".", "-").replace("/", "-") if date_match else "2026-09-01"

        lines = [line.strip() for line in page_text.split("\n") if line.strip()]
        body_lines = []
        capture = False

        for line in lines:
            if full_title in line or title_text in line:
                capture = True
                continue
            if "keywords" in line.lower() and capture:
                break
            if capture:
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

        print(f"✅ 生成成功: {filepath}")
        time.sleep(1)

    except Exception as e:
        print(f"⚠️ エラー: {e}")

print("\n--- 3件のテスト完了 ---")