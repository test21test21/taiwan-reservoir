#!/usr/bin/env python3
"""產生給搜尋引擎看的靜態頁：每座水庫一頁、sitemap.xml、robots.txt。

部署時在「準備網站檔案」之後執行：
    python3 scripts/build_pages.py _site

- _site/reservoir/<水庫代碼>/index.html：數字直接寫進 HTML（Google 不用跑 JavaScript 就看得到）
- _site/index.html、_site/reservoir/index.html：放進 <!--SITE_ICONS-->、<!--SITE_NAV-->（scripts/site_nav.py）
- _site/reservoir/index.html：把 <!--RESERVOIR_LINKS--> 換成全部水庫頁的連結
- _site/about/index.html：關於本站
- _site/births/：出生與死亡，全台＋各縣市一頁（scripts/build_births.py）
- _site/sitemap.xml、_site/robots.txt
"""
import csv
import html
import json
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

import build_births
import site_nav

SITE = "https://taiwandata.info"
# 關於本站頁上的自我介紹（空白就不顯示）與聯絡方式
ABOUT_ME = ""  # 空白就不顯示「關於我」那一段
CONTACT = "有建議或發現數字有誤，歡迎來信：<a href=\"mailto:contact@taiwandata.info\">contact@taiwandata.info</a>"
ROOT = Path(__file__).resolve().parent.parent
LOW = 40
REGIONS = ["北部", "中部", "南部", "東部", "澎湖", "金門", "馬祖"]
ISLAND_COUNTY = {"澎湖": "澎湖縣", "金門": "金門縣", "馬祖": "連江縣"}
# 和 reservoir/index.html 同一份
BINS = [(80, "#2a86e8"), (60, "#5fc3f0"), (40, "#a9dcf2"), (-1, "#a274e8")]
TANK = [(80, "#0b4a8f"), (60, "#1f7ad6"), (40, "#5aaee8"), (-1, "#8a55dd")]  # 跟總覽頁卡片的水杯同色
LIGHTS = {
    "N": ("藍燈", "水情正常", "#2f6fd6"),
    "G": ("綠燈", "水情提醒", "#2e9d4f"),
    "Y": ("黃燈", "減壓供水", "#e2b000"),
    "O": ("橙燈", "減量供水", "#ef7d1a"),
    "R": ("紅燈", "分區供水", "#d93a2f"),
}
INFO_FIELDS = [
    ("鄉鎮市區名稱", "位置"), ("河川名稱", "河川"), ("機關名稱", "管理機關"), ("型式", "壩型"),
    ("壩堰高", "壩高（公尺）"),
    ("功能", "用途"),
]

e = html.escape


def fmt(n, d=0):
    if n is None:
        return "–"
    return f"{n:,.{d}f}"


def vol(n):
    return fmt(n, 1 if n is not None and n < 100 else 0)


def color(p):
    return next(c for m, c in BINS if p >= m)


def tw_time(iso):
    if not iso:
        return ""
    t = datetime.fromisoformat(iso)
    return f"{t.month}/{t.day} {t:%H:%M}"


def ok(r):
    return r.get("percent") is not None and not r.get("suspect")


def county_of(r, info):
    if r["region"] in ISLAND_COUNTY:
        return ISLAND_COUNTY[r["region"]]
    loc = (info or {}).get("鄉鎮市區名稱") or ""
    c = loc[:3].replace("巿", "市").replace("台", "臺")
    return c if c.endswith(("市", "縣")) else None


def load():
    latest = json.loads((ROOT / "data/latest.json").read_text(encoding="utf-8"))
    info = {}
    p = ROOT / "data/reservoir_info.json"
    if p.exists():
        for x in json.loads(p.read_text(encoding="utf-8")):
            info[str(x.get("水庫代碼"))] = x
    hist = defaultdict(list)
    p = ROOT / "data/history.csv"
    if p.exists():
        with p.open(encoding="utf-8") as f:
            for row in csv.DictReader(f):
                hist[row["id"]].append(row)
    alert = None
    p = ROOT / "data/alert.json"
    if p.exists():
        alert = json.loads(p.read_text(encoding="utf-8"))
    return latest, info, hist, alert


CSS = """
:root { --bg:#f6f6f4; --surface:#fff; --fg:#1d2125; --muted:#676d73; --line:#e4e4e0; --water:#0a6cc2; --water-soft:#e3eef8; --low:#7a4fc4; --chip:#efefec;
  --shadow:0 1px 2px rgba(12,30,46,.06),0 4px 16px rgba(12,30,46,.05);
  --f-body:"Noto Sans TC","PingFang TC","Microsoft JhengHei",system-ui,sans-serif; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --bg:#121416; --surface:#1b1e21; --fg:#ececea; --muted:#9a9fa4; --line:#2c3035; --water:#4fb0f0; --water-soft:#16304a; --low:#bba2f0; --chip:#24282c; --shadow:none; color-scheme:dark; } }
:root[data-theme="dark"] { --bg:#121416; --surface:#1b1e21; --fg:#ececea; --muted:#9a9fa4; --line:#2c3035; --water:#4fb0f0; --water-soft:#16304a; --low:#bba2f0; --chip:#24282c; --shadow:none; color-scheme:dark; }
* { box-sizing:border-box; }
body { margin:0; background:var(--bg); color:var(--fg); font-family:var(--f-body); font-size:15px; line-height:1.6; font-variant-numeric:tabular-nums; }
.wrap { max-width:880px; margin:0 auto; padding:16px 16px 48px; }
a { color:var(--fg); text-underline-offset:3px; }
.crumb { font-size:13px; color:var(--muted); padding-block:6px; }
.crumb a { color:var(--muted); }
h1 { font-weight:700; font-size:clamp(24px,6vw,34px); margin:0; letter-spacing:.02em; }
h2 { font-size:17px; margin:0 0 8px; }
.box { background:var(--surface); border:1px solid var(--line); box-shadow:var(--shadow); border-radius:16px; padding:16px; margin-top:12px; }
.lead { color:var(--muted); margin:4px 0 0; font-size:14px; }
.big { display:flex; flex-wrap:wrap; align-items:baseline; gap:4px 16px; }
.pct { font-size:clamp(44px,12vw,64px); font-weight:700; line-height:1; }
.pct small { font-size:20px; color:var(--muted); margin-left:2px; }
.pct.low { color:var(--low); }
.delta { font-size:15px; font-weight:500; color:var(--muted); }
.delta .up { color:#1f8a4c; }
.delta .down { color:#d13c3c; }
.pct.none { font-size:22px; color:var(--muted); font-weight:500; }
.hero.has-tank { display:grid; grid-template-columns:1fr 150px; padding:0; overflow:hidden; }
.hero.has-tank .info { padding:16px; min-width:0; }
.hero .big .lead { margin:0; }
.tank { display:grid; place-content:center; justify-items:center; gap:6px; border-left:1px solid var(--line); min-height:220px;
  background:linear-gradient(to top, var(--wc) var(--p), transparent var(--p)); text-align:center; padding:0 6px; }
.tank .pct { font-size:clamp(36px,9vw,56px); }
.tank .pct small { color:inherit; }
.tank.deep .pct { color:#fff; text-shadow:0 1px 2px rgba(0,0,0,.25); }
.tank.deep .delta { color:rgba(255,255,255,.85); }
.tank.deep .delta .up { color:#8ff0b4; }
.tank.deep .delta .down { color:#ffb0b0; }
.tank.deep .delta .flat { color:#fff; }
@media (min-width:640px) { .hero.has-tank { grid-template-columns:1fr 240px; } }
.stats { display:grid; grid-template-columns:repeat(auto-fill,minmax(130px,1fr)); gap:12px; margin:16px 0 0; }
.stats div { min-width:0; }
.stats dt { font-size:12px; color:var(--muted); }
.stats dd { margin:0; font-size:18px; font-weight:700; }
.stats dd small { font-size:12px; color:var(--muted); font-weight:400; margin-left:2px; }
.chart { display:block; width:100%; height:auto; max-height:340px; margin-top:4px; }
.chart text { font-size:13px; fill:var(--muted); font-family:var(--f-body); }
@media (min-width:640px) { .chart text { font-size:9px; } }
.chart .g { stroke:var(--line); stroke-width:1; }
.chart .line { fill:none; stroke:var(--water); stroke-width:2.5; stroke-linejoin:round; stroke-linecap:round; }
.chart .ly { fill:none; stroke:var(--muted); stroke-width:2; stroke-dasharray:5 4; }
.chart .dot { fill:var(--water); stroke:var(--surface); stroke-width:2; }
.legend { margin:0; font-size:13px; color:var(--muted); display:flex; align-items:center; gap:6px; }
.legend .k { display:inline-block; width:18px; height:0; border-top:2.5px solid var(--water); margin-left:8px; }
.legend .k:first-child { margin-left:0; }
.legend .k.ly { border-top:2px dashed var(--muted); }
details summary { cursor:pointer; font-weight:700; font-size:17px; }
details table { margin-top:8px; }
.light { display:flex; align-items:center; gap:10px; }
.lamp { width:16px; height:16px; border-radius:50%; flex:none; }
table { width:100%; border-collapse:collapse; font-size:14px; }
th, td { text-align:left; padding:6px 8px; border-top:1px solid var(--line); }
td.n, th.n { text-align:right; }
th { font-weight:500; color:var(--muted); }
.prose p { margin:0; }
.links { list-style:none; padding:0; margin:0; display:flex; flex-wrap:wrap; gap:6px 14px; }
.links li { white-space:nowrap; }
.links span { color:var(--muted); font-size:13px; margin-left:4px; }
.cta { display:inline-block; margin-top:16px; padding:8px 16px; border-radius:999px; background:var(--fg); color:var(--bg); text-decoration:none; font-weight:500; }
footer { margin-top:32px; font-size:13px; color:var(--muted); display:grid; gap:6px; }
"""


def head(title, desc, url, image):
    return f"""<!doctype html>
<html lang="zh-Hant-TW">
<head>
<meta charset="utf-8">
<!-- Google Analytics -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-0FDV48XD37"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag("js",new Date());gtag("config","G-0FDV48XD37");</script>
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Taiwan Data 台灣數據">
<meta property="og:locale" content="zh_TW">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{SITE}/{image}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
{site_nav.ICONS}
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;700&display=swap">
<style>{CSS}</style>
</head>"""


CHART_MIN_DAYS = 7  # 資料滿 7 天才畫折線圖，不然只有幾個點不好看


def history_chart(rows):
    """過去 30 天蓄水率折線圖（SVG，直接寫進 HTML）。有一年前的資料時，多畫一條灰色虛線「去年同期」。"""
    all_rows = [r for r in rows if r.get("percent")]
    rows = all_rows[-30:]
    if len(rows) < CHART_MIN_DAYS:
        return ""
    by_date = {r["date"]: float(r["percent"]) for r in all_rows}
    days = [date.fromisoformat(r["date"]) for r in rows]
    now = [float(r["percent"]) for r in rows]
    last = []
    for d in days:
        try:
            ly = d.replace(year=d.year - 1)
        except ValueError:  # 2/29
            ly = d - timedelta(days=365)
        last.append(by_date.get(ly.isoformat()))
    has_last = sum(v is not None for v in last) >= CHART_MIN_DAYS

    vals = now + ([v for v in last if v is not None] if has_last else [])
    lo, hi = min(vals), max(vals)
    lo, hi = max(0, (int(lo) // 10) * 10), min(110, -(-int(hi + 0.999) // 10) * 10)
    if hi - lo < 20:  # 至少 20 個百分點高，小波動才不會被放大成大起伏
        lo = max(0, hi - 20)
        hi = lo + 20
    W, H, L, R, T, B = 420, 220, 46, 12, 12, 26
    t0, span = days[0], max(1, (days[-1] - days[0]).days)
    X = lambda d: L + (W - L - R) * (d - t0).days / span
    Y = lambda v: T + (H - T - B) * (hi - v) / (hi - lo)

    def path(series):
        out, pen = [], "M"
        for d, v in zip(days, series):
            if v is None:
                pen = "M"
                continue
            out.append(f"{pen}{X(d):.1f},{Y(v):.1f}")
            pen = "L"
        return " ".join(out)

    step = 10 if hi - lo <= 40 else 20
    grid = "".join(
        f'<line x1="{L}" x2="{W - R}" y1="{Y(g):.1f}" y2="{Y(g):.1f}" class="g"/>'
        f'<text x="{L - 5}" y="{Y(g) + 4:.1f}" text-anchor="end">{g}%</text>'
        for g in range(lo, hi + 1, step))
    ticks = sorted({0, len(days) // 2, len(days) - 1})
    xlab = "".join(
        f'<text x="{X(days[i]):.1f}" y="{H - 8}" text-anchor="{"start" if i == 0 else "end" if i == len(days) - 1 else "middle"}">'
        f'{days[i].month}/{days[i].day}</text>' for i in ticks)
    ly_line = f'<path d="{path(last)}" class="ly"/>' if has_last else ""
    dot = f'<circle cx="{X(days[-1]):.1f}" cy="{Y(now[-1]):.1f}" r="4" class="dot"/>'
    legend = ('<p class="legend"><span class="k now"></span>今年<span class="k ly"></span>去年同期</p>'
              if has_last else "")
    return (f'<section class="box"><h2>過去 {len(days)} 天蓄水率</h2>{legend}'
            f'<svg class="chart" viewBox="0 0 {W} {H}" role="img" aria-label="過去 {len(days)} 天蓄水率折線圖">'
            f'{grid}{ly_line}<path d="{path(now)}" class="line"/>{dot}{xlab}</svg></section>')


def history_table(rows):
    rows = [r for r in rows if r.get("percent")][-30:]
    if len(rows) < 2:
        return ""
    body = "".join(
        f'<tr><td>{int(r["date"][5:7])}/{int(r["date"][8:10])}</td>'
        f'<td class="n">{float(r["percent"]):.1f}%</td>'
        f'<td class="n">{vol(float(r["storage"])) if r.get("storage") else "–"}</td>'
        f'<td class="n">{fmt(float(r["inflow_daily"]), 1) if r.get("inflow_daily") else "–"}</td></tr>'
        for r in reversed(rows)
    )
    table = ('<table><tr><th>日期</th><th class="n">蓄水率</th><th class="n">蓄水量</th><th class="n">進水量</th></tr>'
             f'{body}</table><p class="lead">蓄水量、進水量單位：萬立方公尺（約萬噸）</p>')
    if len(rows) >= CHART_MIN_DAYS:  # 上面已有折線圖，表格收起來
        return f'<section class="box"><details><summary>看每日數字</summary>{table}</details></section>'
    return f'<section class="box"><h2>最近 {len(rows)} 天蓄水率</h2>{table}</section>'


def reservoir_page(r, info, hist, alert, peers, updated):
    name, rid = r["name"], r["id"]
    url = f"{SITE}/reservoir/{rid}/"
    when = tw_time(r.get("observed_at")) or (r.get("daily_date") or "")[5:].replace("-", "/")
    good = ok(r)
    if good:
        p = r["percent"]
        title = f"{name}蓄水率 {p:.1f}%（{when} 更新）｜台灣水庫水情"
        desc = (f"{name}目前蓄水率 {p:.1f}%，有效蓄水量 {vol(r.get('storage'))} 萬立方公尺，"
                f"有效容量 {vol(r.get('capacity'))} 萬立方公尺（{when} 觀測）。每小時更新，資料來自經濟部水利署。")
        today = (r.get("observed_at") or "")[:10]
        prev = [x for x in hist if x.get("percent") and x["date"] < today]
        change = ""
        if prev:
            d = round(p - float(prev[-1]["percent"]), 1)
            cls, arrow = ("up", "▲") if d > 0 else ("down", "▼") if d < 0 else ("flat", "▶")
            change = f'<span class="delta">比昨天 <b class="{cls}">{arrow} {abs(d):.1f}%</b></span>'
        lvl = max(0, min(100, p))
        wc = next(c for m, c in TANK if p >= m)
        tank = (f'<div class="tank{" deep" if p >= 58 else ""}" style="--p:{lvl:.1f}%;--wc:{wc}">'
                f'<div class="pct">{p:.1f}<small>%</small></div>{change}</div>')
        big = f'<div class="lead">有效蓄水量 {vol(r.get("storage"))} / {vol(r.get("capacity"))} 萬立方公尺</div>'
    else:
        title = f"{name}即時水情｜台灣水庫水情"
        desc = f"{name}的水位、進出水量與基本資料，每小時更新，資料來自經濟部水利署。"
        msg = "官方數字疑似有誤，暫不顯示蓄水率" if r.get("suspect") else "水利署目前沒有提供這座水庫的蓄水率"
        big = f'<div class="pct none">{msg}</div>'
        tank = ""

    stats = []
    for key, label, unit, d in [
        ("water_level", "水位", "公尺", 2), ("full_level", "滿水位", "公尺", 1),
        ("inflow_daily", "昨日進水量", "萬噸", 1), ("outflow_daily", "昨日取用量", "萬噸", 1),
        ("rainfall_daily", "昨日集水區雨量", "毫米", 1), ("inflow_cms", "目前進水", "立方公尺/秒", 1),
    ]:
        if r.get(key) is not None:
            stats.append(f"<div><dt>{label}</dt><dd>{fmt(r[key], d)}<small>{unit}</small></dd></div>")

    county = county_of(r, info)
    light = ""
    if alert and county and alert.get("counties", {}).get(county) in LIGHTS:
        nm, lbl, c = LIGHTS[alert["counties"][county]]
        pub = alert.get("published", "")
        light = (f'<section class="box"><h2>{e(county)}水情燈號</h2><div class="light"><i class="lamp" style="background:{c}"></i>'
                 f'<span><b>{lbl}（{nm}）</b>　<span class="lead">經濟部水利署 {e(pub)} 公告</span></span></div></section>')

    facts = ""
    if info:
        rows = "".join(f"<tr><th>{lbl}</th><td>{e(str(info[k]).strip())}</td></tr>"
                       for k, lbl in INFO_FIELDS if str(info.get(k) or "").strip() not in ("", "…"))
        if r.get("purpose") and "功能" not in info:
            rows += f"<tr><th>用途</th><td>{e(r['purpose'])}</td></tr>"
        facts = f'<section class="box"><h2>{e(name)}基本資料</h2><table>{rows}</table></section>'
    elif r.get("purpose"):
        facts = f'<section class="box"><h2>{e(name)}基本資料</h2><table><tr><th>用途</th><td>{e(r["purpose"])}</td></tr></table></section>'

    others = "".join(
        f'<li><a href="../{x["id"]}/">{e(x["name"])}</a>' + (f'<span>{x["percent"]:.1f}%</span>' if ok(x) else "") + "</li>"
        for x in peers if x["id"] != rid)
    others = f'<section class="box"><h2>{e(r["region"])}其他水庫</h2><ul class="links">{others}</ul></section>' if others else ""

    image = "reservoir/og.png"
    return f"""{head(title, desc, url, image)}
<body>
{site_nav.nav("reservoir", '<a class="sitesection" href="../">水庫水情</a>')}
<div class="wrap">
  <nav class="crumb"><a href="../../">Taiwan Data 台灣數據</a> › <a href="../">水庫水情</a> › {e(r["region"])}</nav>
  <h1>{e(name)}即時蓄水率</h1>
  <p class="lead">{e(r["region"])}・{e(when)} 觀測・資料更新 {e(updated)}</p>
  <section class="box hero{" has-tank" if tank else ""}">
    <div class="info">
      <div class="big">{big}</div>
      <dl class="stats">{"".join(stats)}</dl>
      <a class="cta" href="../">看全台水庫地圖</a>
    </div>
    {tank}
  </section>
  {light}
  {history_chart(hist)}
  {history_table(hist)}
  {facts}
  {others}
  <footer>
    <div>資料來源：經濟部水利署開放資料（水庫水情資料、水庫每日營運狀況、水庫基本資料），每小時更新。蓄水率＝有效蓄水量 ÷ 有效容量，1 萬立方公尺約等於 1 萬噸水。</div>
    <div>本站為個人經營，非政府網站；所有數據皆來自政府開放資料。</div>
  </footer>
</div>
</body>
</html>
"""


def about_page():
    title = "關於本站｜Taiwan Data 台灣數據"
    desc = "Taiwan Data 台灣數據是個人經營的網站，把政府開放資料整理成一眼看懂的工具。"
    return f"""{head(title, desc, f"{SITE}/about/", "og.png")}
<body>
{site_nav.nav("about", '<h1 class="sitesection">關於本站</h1>')}
<div class="wrap prose">
  {f'<section class="box"><h2>關於我</h2><p>{ABOUT_ME}</p></section>' if ABOUT_ME else ""}
  <section class="box">
    <h2>聯絡我</h2>
    <p>{CONTACT}</p>
  </section>
  <footer><div>本站為個人經營，非政府網站；所有數據皆來自政府開放資料。</div></footer>
</div>
</body>
</html>
"""


def main(out):
    out = Path(out)
    latest, info, hist, alert = load()
    updated = tw_time(latest.get("generated_at"))
    lastmod = (latest.get("generated_at") or "")[:10]
    named = [r for r in latest["reservoirs"] if r.get("name")]
    by_region = defaultdict(list)
    for r in sorted(named, key=lambda x: -(x.get("capacity") or 0)):
        by_region[r["region"]].append(r)

    urls = [f"{SITE}/", f"{SITE}/reservoir/", f"{SITE}/about/"]
    (out / "about").mkdir(parents=True, exist_ok=True)
    (out / "about/index.html").write_text(about_page(), encoding="utf-8")
    for r in named:
        d = out / "reservoir" / r["id"]
        d.mkdir(parents=True, exist_ok=True)
        page = reservoir_page(r, info.get(r["id"]), hist.get(r["id"], []), alert, by_region[r["region"]], updated)
        (d / "index.html").write_text(page, encoding="utf-8")
        urls.append(f"{SITE}/reservoir/{r['id']}/")

    urls += build_births.build(out, head, lambda prefix: site_nav.nav("births", '<h1 class="sitesection">出生與死亡</h1>'))

    # 首頁與水庫總覽頁：分頁小圖示、最上方的選單列
    pages = [
        ("index.html", site_nav.nav("home")),
        ("reservoir/index.html", site_nav.nav("reservoir", '<h1 class="sitesection">水庫水情</h1>')),
    ]
    for f, bar in pages:
        if (out / f).exists():
            t = (out / f).read_text(encoding="utf-8")
            t = t.replace("<!--SITE_ICONS-->", site_nav.ICONS).replace("<!--SITE_NAV-->", bar)
            (out / f).write_text(t, encoding="utf-8")

    # 水庫總覽頁底部：全部水庫頁的連結（不靠 JavaScript，搜尋引擎找得到）
    idx = out / "reservoir/index.html"
    if idx.exists():
        groups = "".join(
            f'<div><b>{g}</b><ul class="links">' + "".join(
                f'<li><a href="{x["id"]}/">{e(x["name"])}</a></li>' for x in by_region[g]) + "</ul></div>"
            for g in REGIONS if by_region.get(g))
        idx.write_text(idx.read_text(encoding="utf-8").replace("<!--RESERVOIR_LINKS-->", groups), encoding="utf-8")

    (out / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"  <url><loc>{u}</loc><lastmod>{lastmod}</lastmod></url>\n" for u in urls)
        + "</urlset>\n", encoding="utf-8")
    (out / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {SITE}/sitemap.xml\n", encoding="utf-8")
    print(f"{len(named)} 座水庫頁、sitemap {len(urls)} 個網址")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "_site")
