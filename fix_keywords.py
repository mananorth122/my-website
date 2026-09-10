import os
import re

# 置き換えルールの辞書 (置き換え前: 置き換え後)
MAPPING = {
    # 記号・中黒の除去
    "コード・スイッチング": "コードスイッチング",
    "オーディエンス・デザイン": "オーディエンスデザイン",
    "メタ・コミュニケーション": "メタコミュニケーション",
    "マス・メディア": "マスメディア",
    "マス・コミュニケーション": "マスメディア",
    "マルティモーダル": "マルチモーダル",
    # カッコの除去
    "批判的談話分析（研究）": "批判的談話分析",
    "指標性（indexicality）": "指標性",
    "発語内効力（illocutionary Force）": "発語内効力",
    "垣根表現（Hedge）": "垣根表現",
    "OED（Oxford English Dictionary）": "OED",
    "FTA（face-Threatening Act）": "FTA",
    # 表記・送り仮名の統一
    "名づけ": "名付け",
    "ほめ": "褒め",
    # 概念の統合
    "異文化間コミュニケーション": "異文化コミュニケーション",
    "高コンテキスト社会": "高コンテクスト",
    "高コンテクスト文化": "高コンテクスト",
    "ハイコンテクスト": "高コンテクスト",
    "低コンテキスト社会": "低コンテクスト",
    "低コンテクスト文化": "低コンテクスト",
}

CONTENT_DIR = "content"

# keywords = [...] の行だけを対象にする正規表現
KEYWORDS_PATTERN = re.compile(r"^(keywords\s*=\s*\[)(.*?)(\])", re.MULTILINE)


def replace_in_keywords_line(match):
    prefix = match.group(1)  # keywords = [
    items_str = match.group(2)  # "発話行為", "謝罪"...
    suffix = match.group(3)  # ]

    # 配列の中身だけを置換
    for old_key, new_key in MAPPING.items():
        items_str = items_str.replace(f'"{old_key}"', f'"{new_key}"')
        items_str = items_str.replace(f"'{old_key}'", f"'{new_key}'")

    return f"{prefix}{items_str}{suffix}"


def update_keywords():
    updated_count = 0
    for root, _, files in os.walk(CONTENT_DIR):
        for file in files:
            if file.endswith(".md"):
                path = os.path.join(root, file)
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()

                # keywords の行だけを置換処理
                new_content = KEYWORDS_PATTERN.sub(
                    replace_in_keywords_line, content
                )

                if new_content != content:
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(new_content)
                    print(f"更新完了: {path}")
                    updated_count += 1

    print(f"\n合計 {updated_count} 個のファイルの keywords 行を安全に更新しました。")


if __name__ == "__main__":
    update_keywords()