#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_trending.py — 抓取 GitHub Trending 榜单（纯标准库，无需 API key）

维度：
  since    : daily / weekly / monthly
  language : all / python / typescript / ... （对应 /trending/{lang}）
  spoken   : 可选，自然语言代码，如 zh / en（?spoken_language_code=zh）

用法：
  python3 fetch_trending.py                 # 默认 3 个时间窗 × 8 种语言
  python3 fetch_trending.py --langs all,python --periods daily
  python3 fetch_trending.py --proxy http://127.0.0.1:7897   # 国内网络

输出：../site/data.json
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
ART_RE = re.compile(r'<article class="Box-row">(.*?)</article>', re.S)

DEFAULT_LANGS = ["all", "python", "typescript", "javascript", "go", "rust", "java", "c++"]
DEFAULT_PERIODS = ["daily", "weekly", "monthly"]


def strip_tags(s: str) -> str:
    s = re.sub(r"<[^>]+>", "", s or "")
    return re.sub(r"\s+", " ", s).strip()


def to_int(s):
    if not s:
        return None
    d = re.sub(r"[^\d]", "", s)
    return int(d) if d else None


def fetch(url: str, timeout: int = 30, retry: int = 3) -> str:
    last = None
    for i in range(retry):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": UA,
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            })
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8", "ignore")
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(2 + i * 3)
    raise RuntimeError(f"fetch failed: {url} -> {last}")


def parse_page(html: str, lang: str, period: str):
    out = []
    for art in ART_RE.findall(html):
        h2 = re.search(r"<h2[^>]*>(.*?)</h2>", art, re.S)
        if not h2:
            continue
        href = re.search(r'href="/([^"/\s]+/[^"/\s]+)"', h2.group(1))
        if not href:
            continue
        repo = href.group(1)

        desc_m = re.search(r'<p class="col-9[^"]*">(.*?)</p>', art, re.S)
        desc = strip_tags(desc_m.group(1)) if desc_m else ""

        lang_m = re.search(r'itemprop="programmingLanguage">(.*?)</span>', art, re.S)
        language = strip_tags(lang_m.group(1)) if lang_m else ""

        total_m = re.search(r'/stargazers"[^>]*>(.*?)</a>', art, re.S)
        total = to_int(strip_tags(total_m.group(1))) if total_m else None

        fork_m = re.search(r'/forks"[^>]*>(.*?)</a>', art, re.S)
        forks = to_int(strip_tags(fork_m.group(1))) if fork_m else None

        per_m = re.search(r"([\d,]+)\s+stars\s+(today|this week|this month)", art)
        period_stars = to_int(per_m.group(1)) if per_m else None

        built_by = len(re.findall(r'/stargazers/[^"]*"', art))  # 占位，页面结构变化时不影响主流程

        out.append({
            "repo": repo,
            "desc": desc,
            "language": language,
            "stars": total,
            "forks": forks,
            "period_stars": period_stars,
            "period": period,
            "lang_filter": lang,
            "url": "https://github.com/" + repo,
        })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--langs", default=",".join(DEFAULT_LANGS))
    ap.add_argument("--periods", default=",".join(DEFAULT_PERIODS))
    ap.add_argument("--spoken", default="", help="zh / en …，留空表示不限")
    ap.add_argument("--proxy", default=os.environ.get("HTTPS_PROXY", ""))
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "..", "site", "data.json"))
    ap.add_argument("--sleep", type=float, default=1.2)
    args = ap.parse_args()

    if args.proxy:
        opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({"http": args.proxy, "https": args.proxy})
        )
        urllib.request.install_opener(opener)

    langs = [x.strip() for x in args.langs.split(",") if x.strip()]
    periods = [x.strip() for x in args.periods.split(",") if x.strip()]

    payload = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S%z"),
        "source": "https://github.com/trending",
        "periods": periods,
        "langs": langs,
        "boards": {},
        "errors": [],
    }

    total_items = 0
    for period in periods:
        for lang in langs:
            path = "" if lang == "all" else "/" + urllib.parse.quote(lang, safe="")
            q = f"?since={period}"
            if args.spoken:
                q += f"&spoken_language_code={args.spoken}"
            url = f"https://github.com/trending{path}{q}"
            key = f"{period}|{lang}"
            try:
                html = fetch(url)
                items = parse_page(html, lang, period)
                payload["boards"][key] = items
                total_items += len(items)
                print(f"[ok] {key:24} {len(items):>2} repos", flush=True)
            except Exception as e:  # noqa: BLE001
                payload["boards"][key] = []
                payload["errors"].append(f"{key}: {e}")
                print(f"[!!] {key}: {e}", file=sys.stderr, flush=True)
            time.sleep(args.sleep)

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    print(f"\n写入 {os.path.abspath(args.out)}  共 {total_items} 条 / {len(payload['boards'])} 个榜单")
    if payload["errors"]:
        print(f"失败 {len(payload['errors'])} 个榜单（多为网络或限流）")


if __name__ == "__main__":
    main()
