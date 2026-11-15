#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_site.py — 把 data.json 渲染成单文件静态页面 site/index.html
（数据内嵌，双击本地打开即可用，也可直接部署到 GitHub Pages / Cloudflare Pages）

用法：python3 build_site.py
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "site", "data.json")
OUT = os.path.join(HERE, "..", "site", "index.html")

PERIOD_LABEL = {"daily": "今日", "weekly": "本周", "monthly": "本月"}
LANG_LABEL = {
    "all": "全部语言", "python": "Python", "typescript": "TypeScript",
    "javascript": "JavaScript", "go": "Go", "rust": "Rust", "java": "Java",
    "c++": "C++", "c": "C", "swift": "Swift", "jupyter-notebook": "Jupyter",
}

TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>GitHub 趋势榜 · 我的收藏夹</title>
<style>
:root{
  --bg:#f6f7f9; --card:#fff; --text:#111827; --sub:#6b7280; --line:#e5e7eb;
  --accent:#1f6feb; --accent-soft:#e8f0fe; --star:#d97706; --chip:#f3f4f6;
}
@media (prefers-color-scheme: dark){
  :root{--bg:#0f1115;--card:#171a21;--text:#e8eaed;--sub:#9aa4b2;--line:#262b35;
        --accent:#60a5fa;--accent-soft:#1b2740;--star:#fbbf24;--chip:#1e232c;}
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);
  font:15px/1.55 -apple-system,BlinkMacSystemFont,"PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif;}
.wrap{max-width:1040px;margin:0 auto;padding:28px 18px 64px}
header h1{font-size:24px;margin:0 0 6px;letter-spacing:-.3px}
header p{margin:0;color:var(--sub);font-size:13px}
.toolbar{position:sticky;top:0;z-index:9;background:var(--bg);padding:14px 0 10px;
  border-bottom:1px solid var(--line);margin-bottom:16px}
.row{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.row+.row{margin-top:9px}
button{font:inherit;cursor:pointer;border:1px solid var(--line);background:var(--card);
  color:var(--text);border-radius:8px;padding:6px 12px;transition:.15s}
button:hover{border-color:var(--accent)}
button.on{background:var(--accent);border-color:var(--accent);color:#fff}
input[type=search]{flex:1;min-width:180px;font:inherit;padding:8px 12px;border-radius:8px;
  border:1px solid var(--line);background:var(--card);color:var(--text)}
.hint{color:var(--sub);font-size:12px;margin-left:auto}
.item{display:flex;gap:14px;background:var(--card);border:1px solid var(--line);
  border-radius:12px;padding:14px 16px;margin-bottom:10px}
.rank{color:var(--sub);font-size:13px;min-width:24px;padding-top:2px;font-variant-numeric:tabular-nums}
.main{flex:1;min-width:0}
.repo{font-weight:600;color:var(--accent);text-decoration:none;word-break:break-all}
.repo:hover{text-decoration:underline}
.desc{color:var(--text);font-size:13.5px;margin:5px 0 4px;display:-webkit-box;
  -webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}
.desc-en{color:var(--sub);font-size:12px;margin:0 0 8px;display:-webkit-box;
  -webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
body.no-en .desc-en{display:none}
.meta{display:flex;gap:14px;flex-wrap:wrap;font-size:12.5px;color:var(--sub)}
.meta b{color:var(--text);font-weight:600}
.dot{width:9px;height:9px;border-radius:50%;background:var(--accent);display:inline-block;margin-right:5px;vertical-align:-1px}
.gain{color:var(--star);font-weight:600}
.fav{border:none;background:none;font-size:19px;line-height:1;color:var(--line);padding:0 4px}
.fav.on{color:var(--star)}
.empty{color:var(--sub);text-align:center;padding:48px 0}
footer{margin-top:28px;color:var(--sub);font-size:12px;text-align:center}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>GitHub 趋势榜 · 我的收藏夹</h1>
    <p>数据来源 github.com/trending ｜ 抓取时间 __GENERATED__ ｜ 中文简介自动翻译 ｜ 收藏保存在本机浏览器</p>
  </header>

  <div class="toolbar">
    <div class="row" id="periods"></div>
    <div class="row" id="langs"></div>
    <div class="row">
      <input type="search" id="q" placeholder="搜索仓库名 / 中文简介 / 英文简介，例如 智能体、quant、rust">
      <button id="sortBtn">按周期新增排序</button>
      <button id="favBtn">只看收藏</button>
      <button id="enBtn">显示原文</button>
      <span class="hint" id="count"></span>
    </div>
  </div>

  <div id="list"></div>
  <footer>榜单每格最多约 25 条，数据为抓取时刻快照；星数口径以 GitHub 页面为准。<br>
  中文简介由机器翻译（Google），术语可能不准，可点「显示原文」核对；译文按仓库说明缓存，不会重复翻译。</footer>
</div>

<script>
const DATA = __DATA__;
const PERIOD_LABEL = __PLABEL__;
const LANG_LABEL = __LLABEL__;

let state = { period: "daily", lang: "all", q: "", sortBy: "gain", favOnly: false, showEn: true };
let favs = new Set(JSON.parse(localStorage.getItem("gh_favs") || "[]"));

const el = id => document.getElementById(id);
const esc = s => (s || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

function boardKeys() {
  return Object.keys(DATA.boards);
}
function availableLangs(period) {
  const tags = new Set(["all"]);
  Object.keys(DATA.boards).forEach(k => {
    const [p, l] = k.split("|");
    if (p === period && DATA.boards[k].length) tags.add(l);
  });
  return [...tags].sort((a, b) => (a === "all" ? -1 : b === "all" ? 1 : a.localeCompare(b)));
}

function renderTabs() {
  const pd = el("periods");
  pd.innerHTML = "";
  DATA.periods.forEach(p => {
    const b = document.createElement("button");
    b.textContent = PERIOD_LABEL[p] || p;
    if (p === state.period) b.classList.add("on");
    b.onclick = () => {
      state.period = p;
      if (!availableLangs(p).includes(state.lang)) state.lang = "all";
      render();
    };
    pd.appendChild(b);
  });

  const lg = el("langs");
  lg.innerHTML = "";
  availableLangs(state.period).forEach(l => {
    const b = document.createElement("button");
    b.textContent = LANG_LABEL[l] || l;
    if (l === state.lang) b.classList.add("on");
    b.onclick = () => { state.lang = l; render(); };
    lg.appendChild(b);
  });
}

function renderList() {
  let items = (DATA.boards[`${state.period}|${state.lang}`] || []).slice();
  if (state.q) {
    const q = state.q.toLowerCase();
    items = items.filter(i => (i.repo + " " + (i.desc || "") + " " + (i.desc_zh || "")).toLowerCase().includes(q));
  }
  if (state.favOnly) items = items.filter(i => favs.has(i.repo));
  if (state.sortBy === "gain") items.sort((a, b) => (b.period_stars || 0) - (a.period_stars || 0));
  else items.sort((a, b) => (b.stars || 0) - (a.stars || 0));

  el("count").textContent = items.length + " 个仓库";
  const list = el("list");
  if (!items.length) {
    list.innerHTML = '<div class="empty">这个筛选条件下没有结果</div>';
    return;
  }
  list.innerHTML = items.map((i, n) => {
    const f = favs.has(i.repo) ? " on" : "";
    return `<div class="item">
      <div class="rank">${n + 1}</div>
      <div class="main">
        <button class="fav${f}" data-repo="${i.repo}" title="收藏">★</button>
        <a class="repo" href="${i.url}" target="_blank" rel="noopener">${i.repo}</a>
        <div class="desc">${esc(i.desc_zh || i.desc) || "（无描述）"}</div>
        ${i.desc_zh ? `<div class="desc-en">${esc(i.desc)}</div>` : ""}
        <div class="meta">
          <span class="gain">+${(i.period_stars ?? 0).toLocaleString()} / ${PERIOD_LABEL[state.period]}</span>
          <span><b>${(i.stars ?? 0).toLocaleString()}</b> stars</span>
          <span><b>${(i.forks ?? 0).toLocaleString()}</b> forks</span>
          ${i.language ? `<span><span class="dot"></span>${i.language}</span>` : ""}
        </div>
      </div>
    </div>`;
  }).join("");

  list.querySelectorAll(".fav").forEach(b => {
    b.onclick = () => {
      const r = b.dataset.repo;
      favs.has(r) ? favs.delete(r) : favs.add(r);
      localStorage.setItem("gh_favs", JSON.stringify([...favs]));
      b.classList.toggle("on");
      if (state.favOnly) renderList();
    };
  });
}

function render() {
  renderTabs();
  renderList();
  el("sortBtn").textContent = state.sortBy === "gain" ? "按周期新增排序" : "按总 star 排序";
  el("sortBtn").classList.toggle("on", state.sortBy === "total");
  el("favBtn").classList.toggle("on", state.favOnly);
  el("enBtn").textContent = state.showEn ? "隐藏原文" : "显示原文";
  el("enBtn").classList.toggle("on", !state.showEn);
  if (document.body) document.body.classList.toggle("no-en", !state.showEn);
}

el("q").addEventListener("input", e => { state.q = e.target.value.trim(); renderList(); });
el("sortBtn").onclick = () => { state.sortBy = state.sortBy === "gain" ? "total" : "gain"; render(); };
el("favBtn").onclick = () => { state.favOnly = !state.favOnly; render(); };
el("enBtn").onclick = () => { state.showEn = !state.showEn; render(); };

render();
</script>
</body>
</html>
"""


def main():
    with open(DATA, encoding="utf-8") as f:
        data = json.load(f)
    safe_json = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    html = (TEMPLATE
            .replace("__GENERATED__", data.get("generated_at", "-"))
            .replace("__DATA__", safe_json)
            .replace("__PLABEL__", json.dumps(PERIOD_LABEL, ensure_ascii=False))
            .replace("__LLABEL__", json.dumps(LANG_LABEL, ensure_ascii=False)))
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)
    print("生成", os.path.abspath(OUT), f"{len(html)/1024:.0f} KB")


if __name__ == "__main__":
    main()
