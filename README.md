# GitHub 趋势榜 · 我的收藏夹

一个每天自动更新的 GitHub 热榜页面：**日/周/月 × 多语言**切换、关键词搜索、按「周期新增 star」排序、星标收藏（存在浏览器本机）。

零依赖、零 API key、零服务器成本 —— 抓取在 GitHub Actions 里跑，页面发布在 GitHub Pages。

## 页面能力

- 三个时间窗：今日 / 本周 / 本月
- 语言筛选：全部、Python、TypeScript、JavaScript、Go、Rust、Java、C++（可自行增删）
- 搜索：仓库名或描述
- 排序：按周期新增 star / 按总 star
- ⭐ 收藏：点星标即收藏，`只看收藏` 过滤；数据存 `localStorage`，不上传、不同步

## 工作方式

```
scripts/fetch_trending.py  抓 https://github.com/trending 的 HTML，解析成 data.json
scripts/build_site.py      把 data.json 内嵌进单文件 site/index.html
.github/workflows/trending.yml  每天 4 次（北京时间 08:17/14:17/20:17/02:17）自动重建并发布
```

GitHub 官方不提供 trending API，所以这里是解析页面 HTML。页面结构变动时，改 `fetch_trending.py` 里的几个正则即可。

## 本地跑

```bash
python3 scripts/fetch_trending.py --proxy http://127.0.0.1:7897   # 国内需代理；海外/CI 去掉 --proxy
python3 scripts/build_site.py
open site/index.html
```

自定义维度：

```bash
python3 scripts/fetch_trending.py --periods daily,weekly --langs all,python,go --spoken zh
```

可用参数：`--langs`、`--periods`、`--spoken`、`--proxy`、`--sleep`（默认 1.2 秒/请求）、`--out`。

## 首次部署（本仓库已配好，仅需一步）

仓库 **Settings → Pages → Source** 选择 **GitHub Actions**。
之后每次 push 或定时触发都会自动发布到 `https://<用户名>.github.io/<仓库名>/`。

## 已知限制

- Trending 单页最多约 25 条，且没有分页
- 不提供历史数据；想画趋势曲线需自己每天存一份 `data.json`
- 抓取频率过高会被限流，`--sleep` 调大即可
