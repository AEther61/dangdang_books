"""
当当图书畅销榜采集脚本

支持三类榜单：
    1. 近 7 日榜（recent7）—— 总榜 + 各分类分榜，代表"当前"状态
    2. 月榜（month）    —— 各月畅销排行，提供"时间维度"历史数据
    3. 近 24 小时榜（24hours）

用法：
    # 默认：总榜近7日，5 页
    python scraper/fetch_ranking.py

    # 全部 43 个分类 × 5 页（近7日榜）
    python scraper/fetch_ranking.py --all-categories --pages 5

    # 时间维度：2026 年 1-10 月，总榜各 5 页
    python scraper/fetch_ranking.py --months 2026:1-10 --pages 5

    # 一次全要：43 分类近7日 + 10 个月的历史
    python scraper/fetch_ranking.py --all-categories --months 2026:1-10 --pages 5

分类名从榜单页导航自动发现，不硬编码；月榜月份自动跳过无数据的月份。
采集到已有数据会自动跳过（断点续爬），中断后重跑即可继续。

字段说明见 data/README.md。仅采集公开榜单信息，每页间隔默认 0.8 秒。
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path

import requests
from parsel import Selector

# 榜单类型 -> URL 模板占位符
#   recent7 / 24hours: {code}-recent7-0-0-1-{page}
#   month:            {code}-month-{year}-{month}-1-{page}
URLS = {
    "recent7": "http://bang.dangdang.com/books/bestsellers/{code}-recent7-0-0-1-{page}",
    "24hours": "http://bang.dangdang.com/books/bestsellers/{code}-24hours-0-0-1-{page}",
    "month": "http://bang.dangdang.com/books/bestsellers/{code}-month-{year}-{month}-1-{page}",
}

OVERALL_CODE = "01.00.00.00.00.00"

# 分类名里的斜杠统一去掉，避免在页面/筛选里显示和 URL 参数出问题。
CATEGORY_ALIAS = {
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
    "亲子/家教": "亲子家教",
    "育儿/早教": "育儿早教",
    "孕产/胎教": "孕产胎教",
    "保健/养生": "保健养生",
    "成功/励志": "成功励志",
    "休闲/爱好": "休闲爱好",
    "手工/DIY": "手工DIY",
    "体育/运动": "体育运动",
    "政治/军事": "政治军事",
    "两性关系": "两性关系",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9",
}

DEFAULT_OUT = Path(__file__).resolve().parent.parent / "data" / "books.jsonl"


def clean_name(name):
    """分类名去斜杠、去后缀。"""
    if not name:
        return ""
    name = CATEGORY_ALIAS.get(name, name)
    return name.replace("/", "").strip()


def text_of(node):
    if node is None:
        return ""
    return re.sub(r"\s+", " ", " ".join(node.xpath(".//text()").getall())).strip()


def parse_rating(item):
    width = item.css(".star .level span::attr(style)").get()
    if not width:
        return None
    match = re.search(r"width:\s*([\d.]+)%", width)
    return round(float(match.group(1)) / 10, 1) if match else None


def parse_review_count(item):
    raw = text_of(item.css(".star a"))
    match = re.search(r"([\d,]+)", raw)
    return int(match.group(1).replace(",", "")) if match else 0


def parse_price(item):
    """返回 (现价, 原价)。同一商品有秒杀价+活动价时只取第一段。"""
    current = text_of(item.css(".price .price_n"))
    original = text_of(item.css(".price .price_r"))
    cur_m = re.search(r"[\d.]+", current.replace(",", ""))
    ori_m = re.search(r"[\d.]+", original.replace(",", ""))
    return (
        cur_m.group(0) if cur_m else None,
        ori_m.group(0) if ori_m else None,
    )


def parse_category_from_title(title, kind):
    """从页面 title 解析分类名。

    第1页: “小说畅销榜-近7日畅销书排行榜-…”
    第2页: “第2页_小说畅销榜-近7日畅销书排行榜-…”  ← 多出页码前缀，必须先剥掉
    月榜:  “图书畅销榜-1月畅销书排行榜-…”
    """
    title = (title or "").strip()
    if not title:
        return ""
    # 去掉“第N页_”这类分页前缀
    title = re.sub(r"^第\d+页[_\-]?", "", title).strip()
    head = re.split(r"[-_]", title)[0]
    head = re.sub(r"(类图书|畅销榜|排行榜)$", "", head).strip()
    if head in ("", "总", "总榜", "图书"):
        return "总榜"
    return clean_name(head) or "总榜"


def parse_item(item, rank, category, kind, period):
    title = item.css(".name a::attr(title)").get() or text_of(item.css(".name a"))
    detail_url = item.css(".name a::attr(href)").get() or ""
    cover_url = item.css(".pic img::attr(src)").get() or ""

    pid = ""
    match = re.search(r"product\.dangdang\.com/(\d+)\.html", detail_url)
    if match:
        pid = match.group(1)

    infos = item.css(".publisher_info")
    authors, publish_date, publisher = [], "", ""
    if len(infos) >= 1:
        authors = [text_of(a) for a in infos[0].css("a") if text_of(a)]
    if len(infos) >= 2:
        if infos[1].css("span"):
            publish_date = text_of(infos[1].css("span"))
        links = [text_of(a) for a in infos[1].css("a") if text_of(a)]
        publisher = links[0] if links else ""

    current_price, original_price = parse_price(item)

    return {
        "rank": rank,
        "ranking_category": category,
        "ranking_period": period,   # 时间维度：如 “2026-07” 或 “近7日”
        "ranking_kind": kind,       # recent7 / month / 24hours
        "title": title.strip(),
        "dangdang_id": pid,
        "price": current_price,
        "original_price": original_price,
        "rating": parse_rating(item),
        "review_count": parse_review_count(item),
        "authors": authors,
        "publisher": publisher,
        "publish_date": publish_date,
        "cover_url": cover_url,
        "detail_url": detail_url,
        "categories": [category],
    }


def build_url(kind, code, page, year=None, month=None):
    return URLS[kind].format(code=code, page=page, year=year, month=month)


def fetch(session, url, retries=3):
    for attempt in range(1, retries + 1):
        try:
            r = session.get(url, headers=HEADERS, timeout=20)
            r.raise_for_status()
            r.encoding = "gbk"
            return Selector(r.text)
        except Exception as exc:  # noqa: BLE001
            if attempt == retries:
                print(f"    放弃 {url}: {type(exc).__name__}", file=sys.stderr)
                return None
            time.sleep(1.0 * attempt)
    return None


def discover_categories(session):
    """从总榜页导航解析全部分类名与编码。"""
    sel = fetch(session, build_url("recent7", OVERALL_CODE, 1))
    if sel is None:
        return {}
    mapping = {}
    pattern = re.compile(r"/books/bestsellers/([\d.]+)-(recent7|24hours)-")
    for link in sel.css("a[href*=bestsellers]"):
        href = link.css("::attr(href)").get() or ""
        name = text_of(link)
        if not name:
            continue
        match = pattern.search(href)
        if not match:
            continue
        code = match.group(1)
        if code == OVERALL_CODE:
            continue
        name = clean_name(name)
        if name and name not in ("近24小时", "近7日", "近30日"):
            mapping.setdefault(name, code)
    return mapping


def crawl_one(session, kind, code, category, pages, delay, year=None, month=None):
    """抓一个榜单（某分类 × 某周期）的所有页。"""
    period = f"{year}-{month:02d}" if kind == "month" else {
        "recent7": "近7日", "24hours": "近24小时",
    }.get(kind, kind)

    records = []
    for page in range(1, pages + 1):
        sel = fetch(session, build_url(kind, code, page, year, month))
        if sel is None:
            break
        title = sel.css("title::text").get() or ""
        real_category = parse_category_from_title(title, kind)
        # 月榜的 title 不含分类，用传入的分类名
        cat = category if kind == "month" else (real_category or category)

        items = sel.css("ul.bang_list li")
        if not items:
            break
        for item in items:
            rec = parse_item(item, len(records) + 1, cat, kind, period)
            if not rec["title"] or not rec["price"]:
                continue
            records.append(rec)
        time.sleep(delay)
    return records


def load_done_keys(out_path):
    """已抓过的 (分类, 周期) 组合，用于断点续爬。"""
    done = set()
    if not out_path.exists():
        return done
    try:
        with out_path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                cat = (obj.get("categories") or [obj.get("ranking_category", "")])[0]
                done.add((cat, obj.get("ranking_period", "")))
    except OSError:
        pass
    return done


def parse_months(spec):
    """解析 --months 2026:1-10 或 2026:3,6,9 -> [(2026,1),...]"""
    if not spec:
        return []
    out = []
    for chunk in spec.split(","):
        chunk = chunk.strip()
        if ":" not in chunk:
            continue
        year_s, rng = chunk.split(":", 1)
        year = int(year_s)
        if "-" in rng:
            a, b = rng.split("-", 1)
            out.extend((year, m) for m in range(int(a), int(b) + 1))
        else:
            out.append((year, int(rng)))
    return out


def main():
    parser = argparse.ArgumentParser(description="抓取当当畅销榜（支持分类 + 时间维度）")
    parser.add_argument("--pages", type=int, default=5, help="每个榜单抓几页，默认 5（每页 20 条）")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="输出 JSONL 路径")
    parser.add_argument("--delay", type=float, default=0.8, help="每页间隔秒数")
    parser.add_argument("--all-categories", action="store_true", help="抓全部分类（当前 43 个）")
    parser.add_argument("--categories", type=int, default=0, metavar="N", help="抓前 N 个分类")
    parser.add_argument("--only", default="", help="只抓指定分类，逗号分隔")
    parser.add_argument("--months", default="", help="月榜，如 2026:1-10")
    parser.add_argument("--kind", default="recent7", choices=list(URLS), help="榜单类型")
    parser.add_argument("--resume", action="store_true", help="断点续爬：跳过已抓过的组合")
    args = parser.parse_args()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    done = load_done_keys(out_path) if args.resume else set()
    if done:
        print(f"断点续爬：已有 {len(done)} 个(分类,周期)组合，将跳过")

    all_records = []
    months = parse_months(args.months)

    # ---------- 时间维度：月榜 ----------
    if months:
        found = 0
        for year, month in months:
            period = f"{year}-{month:02d}"
            if args.resume and ("总榜", period) in done:
                print(f"[月榜 {period}] 已完成，跳过")
                continue
            recs = crawl_one(session, "month", OVERALL_CODE, "总榜",
                             args.pages, args.delay, year, month)
            if not recs:
                print(f"[月榜 {period}] 无数据，跳过（可能该月尚未结束）")
                continue
            print(f"[月榜 {period}] {len(recs)} 条")
            all_records.extend(recs)
            found += 1
        print(f"月榜完成：{found} 个月\n")

    # ---------- 当前状态：近7日 / 24小时榜 ----------
    need_categories = args.all_categories or args.categories or args.only
    if need_categories:
        print("发现分类 ...")
        cat_map = discover_categories(session)
        print(f"共 {len(cat_map)} 个分类")
        if args.only:
            wanted = [n.strip() for n in args.only.split(",") if n.strip()]
            targets = {n: cat_map[n] for n in wanted if n in cat_map}
        elif args.categories:
            targets = dict(list(cat_map.items())[: args.categories])
        else:
            targets = dict(cat_map)
    else:
        targets = {}

    # 总是抓总榜
    crawl_targets = {"总榜": OVERALL_CODE}
    crawl_targets.update(targets)

    period_now = "近7日" if args.kind == "recent7" else "近24小时"
    for name, code in crawl_targets.items():
        if args.resume and (name, period_now) in done:
            print(f"[{name}] 已完成，跳过")
            continue
        recs = crawl_one(session, args.kind, code, name, args.pages, args.delay)
        print(f"[{name}] {len(recs)} 条")
        all_records.extend(recs)

    # ---------- 合并去重：按 (dangdang_id, 分类, 周期) 唯一 ----------
    existing = []
    if out_path.exists() and args.resume:
        with out_path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        existing.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass

    merged = existing + all_records
    seen = set()
    unique = []
    for rec in merged:
        cat = (rec.get("categories") or [rec.get("ranking_category", "")])[0]
        key = (rec.get("dangdang_id") or rec.get("title"), cat, rec.get("ranking_period", ""))
        if key in seen:
            continue
        seen.add(key)
        unique.append(rec)

    with out_path.open("w", encoding="utf-8") as f:
        for rec in unique:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # 统计
    books = len({r["dangdang_id"] for r in unique})
    by_period = {}
    for r in unique:
        by_period[r.get("ranking_period", "")] = by_period.get(r.get("ranking_period", ""), 0) + 1
    by_cat = {}
    for r in unique:
        c = (r.get("categories") or [""])[0]
        by_cat[c] = by_cat.get(c, 0) + 1

    print(f"\n完成：记录 {len(unique)} 条，涉及图书 {books} 本 -> {out_path}")
    print(f"周期分布：{dict(sorted(by_period.items()))}")
    print(f"分类数：{len(by_cat)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
