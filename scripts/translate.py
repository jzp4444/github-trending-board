#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
translate.py — 把 data.json 里每个仓库的英文简介翻成中文（构建时自动执行，无需 API key）

做法：
  1. 收集所有不重复的英文 desc
  2. 已翻译过的直接命中缓存 site/zh_cache.json（缓存随仓库提交，下次只翻新增的）
  3. 未翻译的批量请求 Google 免费翻译端点（每批 8 条，用换行分隔，失败自动降级为逐条）
  4. 结果写回 data.json 的 desc_zh 字段，并更新缓存

用法：
  python3 translate.py                 # 默认
  python3 translate.py --proxy http://127.0.0.1:7897
  python3 translate.py --limit 20      # 只翻 20 条，用于调试
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "site", "data.json")
CACHE = os.path.join(HERE, "..", "site", "zh_cache.json")

ENDPOINT = "https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=zh-CN&dt=t"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

# 机翻常见偏差的定向纠正（只改明确错的搭配，避免误伤）
FIXUPS = [
    ("编码代理", "编码智能体"),
    ("代理技能", "智能体技能"),
    ("AI 代理", "AI 智能体"),
    ("人工智能代理", "AI 智能体"),
    ("座席", "智能体"),
    ("法学硕士", "大模型"),
    ("不和谐", "Discord"),
    ("人工智能智能体", "AI 智能体"),
    ("的的", "的"),
]

# 依英文原文判断才替换的词（避免把 proxy/React 之外的正常用词改错）
CONTEXT_FIXUPS = [
    ("react", [("反应", "React")]),
    ("angular", [("角度", "Angular")]),
    ("compose", [("组合", "Compose")]),
]


def polish(zh: str, en: str = "") -> str:
    low = (en or "").lower()
    for a, b in FIXUPS:
        zh = zh.replace(a, b)
    # agent 在 AI 语境下应为「智能体」；英文是 proxy 时保留「代理」
    if "proxy" not in low:
        zh = zh.replace("代理", "智能体")
    for key, rules in CONTEXT_FIXUPS:
        if key in low:
            for a, b in rules:
                zh = zh.replace(a, b)
    # 去掉中文之间被机翻插进去的空格
    zh = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])", "", zh)
    return zh.strip()


def request(text: str, retry: int = 3) -> str:
    body = urllib.parse.urlencode({"q": text}).encode()
    last = None
    for i in range(retry):
        try:
            req = urllib.request.Request(ENDPOINT, data=body, headers={
                "User-Agent": UA,
                "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
            })
            with urllib.request.urlopen(req, timeout=25) as r:
                raw = json.loads(r.read().decode("utf-8", "ignore"))
            segs = raw[0] or []
            return "".join(s[0] for s in segs if s and s[0])
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(1.5 * (i + 1))
    raise RuntimeError(str(last))


def translate_batch(texts, proxy_note=""):
    """一批多条：用换行拼接，返回列表；条数对不上就逐条重来"""
    joined = "\n".join(texts)
    out = request(joined)
    parts = [p for p in out.split("\n")]
    # 去掉尾部空行造成的多余片段
    parts = [p for p in parts if p.strip() != ""] if len(parts) > len(texts) else parts
    if len(parts) == len(texts):
        return parts
    # 降级：逐条
    res = []
    for t in texts:
        try:
            res.append(request(t))
        except Exception:  # noqa: BLE001
            res.append("")
        time.sleep(0.35)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--proxy", default=os.environ.get("HTTPS_PROXY", ""))
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--sleep", type=float, default=0.5)
    args = ap.parse_args()

    if args.proxy:
        urllib.request.install_opener(urllib.request.build_opener(
            urllib.request.ProxyHandler({"http": args.proxy, "https": args.proxy})))

    data = json.load(open(DATA, encoding="utf-8"))
    cache = {}
    if os.path.exists(CACHE):
        cache = json.load(open(CACHE, encoding="utf-8"))

    uniq = []
    seen = set()
    for items in data["boards"].values():
        for it in items:
            d = (it.get("desc") or "").strip()
            if d and d not in seen:
                seen.add(d)
                uniq.append(d)

    todo = [d for d in uniq if not cache.get(d)]
    if args.limit:
        todo = todo[: args.limit]

    print(f"简介总数 {len(uniq)}，已缓存 {len(uniq) - len([d for d in uniq if not cache.get(d)])}，本次待翻 {len(todo)}")

    done = 0
    for i in range(0, len(todo), args.batch):
        chunk = todo[i:i + args.batch]
        try:
            outs = translate_batch(chunk)
        except Exception as e:  # noqa: BLE001
            print(f"  批次失败，跳过 {len(chunk)} 条：{e}", file=sys.stderr)
            continue
        for src, zh in zip(chunk, outs):
            zh = polish(zh)
            if zh:
                cache[src] = zh
        done += len(chunk)
        print(f"  {done}/{len(todo)}", flush=True)
        time.sleep(args.sleep)

    # 注入 data.json
    hit = miss = 0
    for items in data["boards"].values():
        for it in items:
            d = (it.get("desc") or "").strip()
            zh = cache.get(d)
            if zh:
                it["desc_zh"] = zh
                hit += 1
            else:
                miss += 1

    json.dump(cache, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    json.dump(data, open(DATA, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"完成：{hit} 条已带中文，{miss} 条无译文（保留英文），缓存 {len(cache)} 条")


if __name__ == "__main__":
    main()
