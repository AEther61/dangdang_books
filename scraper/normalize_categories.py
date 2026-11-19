"""规范化 data/books.jsonl 里的分类名（去斜杠、去后缀）。"""

import json
import re
from pathlib import Path

ALIAS = {
    "动漫/幽默": "动漫幽默",
    "美食/烹饪": "美食烹饪",
    "家居/休闲": "家居休闲",
    "医学/卫生": "医学卫生",
    "考试/教辅": "考试教辅",
    "文学/小说": "文学小说",
    "哲学/宗教": "哲学宗教",
    "经济/管理": "经济管理",
    "少儿/母婴": "少儿母婴",
    "旅游/地图": "旅游地图",
    "时尚/美妆": "时尚美妆",
    "家庭/家居": "家庭家居",
    "农业/林业": "农业林业",
    "工业/技术": "工业技术",
    "计算机/网络": "计算机网络",
}

path = Path(__file__).resolve().parent.parent / "data" / "books.jsonl"
rows = [json.loads(line) for line in path.open(encoding="utf-8")]

for row in rows:
    raw = row.get("ranking_category") or row["categories"][0]
    name = ALIAS.get(raw, raw)
    name = re.sub(r"(类图书|畅销榜|排行榜|榜)$", "", name).strip()
    name = name.replace("/", "").strip()
    # 空或只剩“总”的都归为总榜
    if not name or name == "总":
        name = "总榜"
    row["ranking_category"] = name
    row["categories"] = [name]

with path.open("w", encoding="utf-8") as file:
    for row in rows:
        file.write(json.dumps(row, ensure_ascii=False) + "\n")

from collections import Counter

print("total:", len(rows))
print("categories:", dict(Counter(r["categories"][0] for r in rows)))
