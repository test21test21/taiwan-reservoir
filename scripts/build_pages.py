#!/usr/bin/env python3
"""產生給搜尋引擎看的靜態頁：每座水庫一頁、sitemap.xml、robots.txt。

部署時在「準備網站檔案」之後執行：
    python3 scripts/build_pages.py _site

- _site/reservoir/<水庫代碼>/index.html：數字直接寫進 HTML（Google 不用跑 JavaScript 就看得到）
- _site/index.html、_site/reservoir/index.html：放進 <!--SITE_ICONS-->、<!--SITE_NAV-->（scripts/site_nav.py）
- _site/reservoir/index.html：把 <!--RESERVOIR_LINKS--> 換成全部水庫頁的連結
- _site/about/index.html：關於本站
- _site/births/：出生與死亡，全台＋各縣市一頁（scripts/build_births.py）
- _site/power/：台灣今日電力（scripts/build_power.py）
- _site/flights/：航班（scripts/build_flights.py）
- _site/tourism/：旅客人次（scripts/build_travel.py）
- _site/sitemap.xml、_site/robots.txt
"""
import csv
import html
import json
import os
import re
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

import build_births
import build_flights
import build_power
import build_travel
import i18n_en
import i18n_ja
import i18n_ko
import site_nav

SITE = "https://taiwandata.info"
# 關於本站頁上的自我介紹（空白就不顯示）與聯絡方式
ABOUT_ME = ""  # 空白就不顯示「關於我」那一段
CONTACT = "歡迎來信：<a href=\"mailto:contact@taiwandata.info\">contact@taiwandata.info</a>"
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


def vol_m(n):
    """英文版：萬立方公尺換成 million m³。"""
    if n is None:
        return "–"
    v = n / 100
    return fmt(v, 2 if v < 10 else 1)


MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def en_time(iso):
    if not iso:
        return ""
    t = datetime.fromisoformat(iso)
    return f"{MON[t.month - 1]} {t.day}, {t:%H:%M}"


def en_date(d):
    return f"{MON[int(d[5:7]) - 1]} {int(d[8:10])}" if d else ""


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
html[lang="ja"] th, html[lang="ko"] th { white-space:nowrap; }
"""


def hreflang(path):
    """中英日韓各版互相標示，搜尋引擎才知道是同一頁的不同語言。path：中文版網址（/reservoir/）。"""
    return "\n".join(f'<link rel="alternate" hreflang="{h}" href="{SITE}{site_nav.lang_url(k, path)}">'
                     for k, _, _, h in site_nav.LANGS) + f'\n<link rel="alternate" hreflang="x-default" href="{SITE}{path}">'


HTML_LANG = {"zh": "zh-Hant-TW", "en": "en", "ja": "ja", "ko": "ko"}
SITE_NAME = {"zh": "Taiwan Data 台灣數據", "en": "Taiwan Data", "ja": "Taiwan Data 台湾データ", "ko": "Taiwan Data 대만 데이터"}
LOCALE = {"zh": "zh_TW", "en": "en_US", "ja": "ja_JP", "ko": "ko_KR"}


def head(title, desc, url, image, lang="zh", path=None):
    """path：這一頁的中文版網址（/about/），有其他語言版的頁才給。"""
    return f"""<!doctype html>
<html lang="{HTML_LANG[lang]}">
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
<meta property="og:site_name" content="{SITE_NAME[lang]}">
<meta property="og:locale" content="{LOCALE[lang]}">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{SITE}/{image}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
{hreflang(path) if path else ""}
{site_nav.ICONS}
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;700&display=swap">
<style>{CSS}</style>
</head>"""


CHART_MIN_DAYS = 7  # 資料滿 7 天才畫折線圖，不然只有幾個點不好看


def L(lang, zh, en, ja, ko):
    """依語言挑文字。"""
    return en if lang == "en" else ja if lang == "ja" else ko if lang == "ko" else zh


def history_chart(rows, lang="zh"):
    """過去 30 天蓄水率折線圖（SVG，直接寫進 HTML）。有一年前的資料時，多畫一條灰色虛線「去年同期」。"""
    en = lang == "en"
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
    W, H, L_, R, T, B = 420, 220, 46, 12, 12, 26
    t0, span = days[0], max(1, (days[-1] - days[0]).days)
    X = lambda d: L_ + (W - L_ - R) * (d - t0).days / span
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
        f'<line x1="{L_}" x2="{W - R}" y1="{Y(g):.1f}" y2="{Y(g):.1f}" class="g"/>'
        f'<text x="{L_ - 5}" y="{Y(g) + 4:.1f}" text-anchor="end">{g}%</text>'
        for g in range(lo, hi + 1, step))
    ticks = sorted({0, len(days) // 2, len(days) - 1})
    xlab = "".join(
        f'<text x="{X(days[i]):.1f}" y="{H - 8}" text-anchor="{"start" if i == 0 else "end" if i == len(days) - 1 else "middle"}">'
        f'{en_date(days[i].isoformat()) if en else f"{days[i].month}/{days[i].day}"}</text>' for i in ticks)
    ly_line = f'<path d="{path(last)}" class="ly"/>' if has_last else ""
    dot = f'<circle cx="{X(days[-1]):.1f}" cy="{Y(now[-1]):.1f}" r="4" class="dot"/>'
    legend = ((f'<p class="legend"><span class="k now"></span>{L(lang, "今年", "This year", "今年", "올해")}'
               f'<span class="k ly"></span>{L(lang, "去年同期", "Same day last year", "前年同日", "작년 같은 날")}</p>') if has_last else "")
    title = L(lang, f"過去 {len(days)} 天蓄水率", f"Storage over the last {len(days)} days", f"過去{len(days)}日間の貯水率", f"최근 {len(days)}일 저수율")
    return (f'<section class="box"><h2>{title}</h2>{legend}'
            f'<svg class="chart" viewBox="0 0 {W} {H}" role="img" aria-label="{title}">'
            f'{grid}{ly_line}<path d="{path(now)}" class="line"/>{dot}{xlab}</svg></section>')


def md(d, en=False):
    """2026-10-13 → 中文、日文 10/13、英文 Oct 13"""
    return en_date(d) if en else f"{int(d[5:7])}/{int(d[8:10])}"


def history_table(rows, lang="zh"):
    en = lang == "en"
    rows = [r for r in rows if r.get("percent")][-30:]
    if len(rows) < 2:
        return ""
    v = vol_m if en else vol
    flow = (lambda x: fmt(x / 100, 2)) if en else (lambda x: fmt(x, 1))
    body = "".join(
        f'<tr><td>{md(r["date"], en)}</td>'
        f'<td class="n">{float(r["percent"]):.1f}%</td>'
        f'<td class="n">{v(float(r["storage"])) if r.get("storage") else "–"}</td>'
        f'<td class="n">{flow(float(r["inflow_daily"])) if r.get("inflow_daily") else "–"}</td></tr>'
        for r in reversed(rows)
    )
    if en:
        table = ('<table><tr><th>Date</th><th class="n">Storage %</th><th class="n">Storage</th><th class="n">Inflow</th></tr>'
                 f'{body}</table><p class="lead">Storage and inflow in million m³</p>')
        summary, h2 = "Daily figures", f"Storage over the last {len(rows)} days"
    elif lang == "ja":
        table = ('<table><tr><th>日付</th><th class="n">貯水率</th><th class="n">貯水量</th><th class="n">流入量</th></tr>'
                 f'{body}</table><p class="lead">貯水量・流入量の単位：万m³（約1万トン）</p>')
        summary, h2 = "日別の数値を見る", f"直近{len(rows)}日間の貯水率"
    elif lang == "ko":
        table = ('<table><tr><th>날짜</th><th class="n">저수율</th><th class="n">저수량</th><th class="n">유입량</th></tr>'
                 f'{body}</table><p class="lead">저수량·유입량 단위: 만 m³(약 1만 톤)</p>')
        summary, h2 = "일별 수치 보기", f"최근 {len(rows)}일 저수율"
    else:
        table = ('<table><tr><th>日期</th><th class="n">蓄水率</th><th class="n">蓄水量</th><th class="n">進水量</th></tr>'
                 f'{body}</table><p class="lead">蓄水量、進水量單位：萬立方公尺（約萬噸）</p>')
        summary, h2 = "看每日數字", f"最近 {len(rows)} 天蓄水率"
    if len(rows) >= CHART_MIN_DAYS:  # 上面已有折線圖，表格收起來
        return f'<section class="box"><details><summary>{summary}</summary>{table}</details></section>'
    return f'<section class="box"><h2>{h2}</h2>{table}</section>'


FOOT = {
    "zh": "本站為個人經營，非政府網站；所有數據皆來自政府開放資料。",
    "en": "An independent site, not affiliated with the government. All figures come from government open data.",
    "ja": i18n_ja.FOOT,
    "ko": i18n_ko.FOOT,
}


def reservoir_page(r, info, hist, alert, peers, updated, lang="zh"):
    """一座水庫一頁。lang="en" 產生 /en/reservoir/<代碼>/，lang="ja" 產生 /jp/reservoir/<代碼>/，lang="ko" 產生 /kr/reservoir/<代碼>/。"""
    en, ja, ko = lang == "en", lang == "ja", lang == "ko"
    rid = r["id"]
    tr_name = lambda x: i18n_en.name(x["id"], x["name"]) if en else i18n_ja.name(x["id"], x["name"]) if ja else i18n_ko.name(x["id"], x["name"]) if ko else x["name"]
    name = tr_name(r)
    path = f"/reservoir/{rid}/"
    url = SITE + site_nav.lang_url(lang, path)
    region = (i18n_en.REGIONS if en else i18n_ja.REGIONS if ja else i18n_ko.REGIONS if ko else {}).get(r["region"], r["region"])
    if en:
        when = en_time(r.get("observed_at")) or en_date(r.get("daily_date"))
    else:
        when = tw_time(r.get("observed_at")) or (r.get("daily_date") or "")[5:].replace("-", "/")
    good = ok(r)
    if good:
        p = r["percent"]
        if en:
            title = f"{name} Storage {p:.1f}% ({when}) | Taiwan Reservoir Levels"
            desc = (f"{name}, Taiwan, is at {p:.1f}% of capacity: {vol_m(r.get('storage'))} of {vol_m(r.get('capacity'))} "
                    f"million m³ effective storage (observed {when}). Updated hourly from Water Resources Agency open data.")
        elif ja:
            title = f"{name}の貯水率 {p:.1f}%（{when} 更新）｜台湾ダム貯水率"
            desc = (f"台湾・{name}の現在の貯水率は {p:.1f}%、有効貯水量 {vol(r.get('storage'))} 万m³、"
                    f"有効貯水容量 {vol(r.get('capacity'))} 万m³（{when} 観測）。経済部水利署のオープンデータから毎時更新。")
        elif ko:
            title = f"{name} 저수율 {p:.1f}% ({when} 업데이트) | 대만 저수지 저수율"
            desc = (f"대만 {name}의 현재 저수율은 {p:.1f}%, 유효저수량 {vol(r.get('storage'))}만 m³, "
                    f"유효저수용량 {vol(r.get('capacity'))}만 m³({when} 관측). 경제부 수리서 공공데이터로 매시간 업데이트.")
        else:
            title = f"{name}蓄水率 {p:.1f}%（{when} 更新）｜台灣水庫水情"
            desc = (f"{name}目前蓄水率 {p:.1f}%，有效蓄水量 {vol(r.get('storage'))} 萬立方公尺，"
                    f"有效容量 {vol(r.get('capacity'))} 萬立方公尺（{when} 觀測）。每小時更新，資料來自經濟部水利署。")
        today = (r.get("observed_at") or "")[:10]
        prev = [x for x in hist if x.get("percent") and x["date"] < today]
        change = ""
        if prev:
            d = round(p - float(prev[-1]["percent"]), 1)
            cls, arrow = ("up", "▲") if d > 0 else ("down", "▼") if d < 0 else ("flat", "▶")
            change = f'<span class="delta">{L(lang, "比昨天", "vs yesterday", "前日比", "전일 대비")} <b class="{cls}">{arrow} {abs(d):.1f}%</b></span>'
        lvl = max(0, min(100, p))
        wc = next(c for m, c in TANK if p >= m)
        tank = (f'<div class="tank{" deep" if p >= 58 else ""}" style="--p:{lvl:.1f}%;--wc:{wc}">'
                f'<div class="pct">{p:.1f}<small>%</small></div>{change}</div>')
        if en:
            big = f'<div class="lead">Effective storage {vol_m(r.get("storage"))} / {vol_m(r.get("capacity"))} million m³</div>'
        elif ja:
            big = f'<div class="lead">有効貯水量 {vol(r.get("storage"))} / {vol(r.get("capacity"))} 万m³</div>'
        elif ko:
            big = f'<div class="lead">유효저수량 {vol(r.get("storage"))} / {vol(r.get("capacity"))}만 m³</div>'
        else:
            big = f'<div class="lead">有效蓄水量 {vol(r.get("storage"))} / {vol(r.get("capacity"))} 萬立方公尺</div>'
    else:
        if en:
            title = f"{name} Live Conditions | Taiwan Reservoir Levels"
            desc = f"Water level, inflow and facts for {name}, Taiwan. Updated hourly from Water Resources Agency open data."
            msg = ("The official figure looks wrong, so storage % is hidden for now" if r.get("suspect")
                   else "The Water Resources Agency doesn't publish a storage % for this reservoir")
        elif ja:
            title = f"{name}のリアルタイム水情｜台湾ダム貯水率"
            desc = f"台湾・{name}の水位、流入量、基本データ。経済部水利署のオープンデータから毎時更新。"
            msg = ("公式値に誤りの可能性があるため、貯水率を一時的に表示していません" if r.get("suspect")
                   else "水利署はこのダムの貯水率を公表していません")
        elif ko:
            title = f"{name} 실시간 수문 현황 | 대만 저수지 저수율"
            desc = f"대만 {name}의 수위, 유입량, 기본 정보. 경제부 수리서 공공데이터로 매시간 업데이트."
            msg = ("공식 수치에 오류 가능성이 있어 저수율을 잠시 표시하지 않습니다" if r.get("suspect")
                   else "수리서는 이 저수지의 저수율을 공개하지 않습니다")
        else:
            title = f"{name}即時水情｜台灣水庫水情"
            desc = f"{name}的水位、進出水量與基本資料，每小時更新，資料來自經濟部水利署。"
            msg = "官方數字疑似有誤，暫不顯示蓄水率" if r.get("suspect") else "水利署目前沒有提供這座水庫的蓄水率"
        big = f'<div class="pct none">{msg}</div>'
        tank = ""

    stats = []
    # (欄位, 中文名, 英文名, 日文名, 韓文名, 中文單位, 英文單位, 日文單位, 韓文單位, 小數位, 英文版換成 million m³)
    for key, label, label_en, label_ja, label_ko, unit, unit_en, unit_ja, unit_ko, d, mm in [
        ("water_level", "水位", "Water level", "水位", "수위", "公尺", "m", "m", "m", 2, False),
        ("full_level", "滿水位", "Full level", "満水位", "만수위", "公尺", "m", "m", "m", 1, False),
        ("inflow_daily", "昨日進水量", "Inflow yesterday", "前日の流入量", "어제 유입량", "萬噸", "million m³", "万m³", "만 m³", 1, True),
        ("outflow_daily", "昨日取用量", "Drawn yesterday", "前日の取水量", "어제 취수량", "萬噸", "million m³", "万m³", "만 m³", 1, True),
        ("rainfall_daily", "昨日集水區雨量", "Catchment rain yesterday", "前日の流域雨量", "어제 유역 강우량", "毫米", "mm", "mm", "mm", 1, False),
        ("inflow_cms", "目前進水", "Inflow now", "現在の流入量", "현재 유입량", "立方公尺/秒", "m³/s", "m³/s", "m³/s", 1, False),
    ]:
        if r.get(key) is not None:
            v = fmt(r[key] / 100, 2) if en and mm else fmt(r[key], d)
            stats.append(f"<div><dt>{L(lang, label, label_en, label_ja, label_ko)}</dt><dd>{v}<small>{L(lang, unit, unit_en, unit_ja, unit_ko)}</small></dd></div>")

    county = county_of(r, info)
    light = ""
    if alert and county and alert.get("counties", {}).get(county) in LIGHTS:
        k = alert["counties"][county]
        nm, lbl, c = LIGHTS[k]
        pub = alert.get("published", "")
        if en:
            nm, lbl, _ = i18n_en.LIGHTS[k]
            light = (f'<section class="box"><h2>{e(i18n_en.COUNTIES.get(county, county))} water alert</h2><div class="light">'
                     f'<i class="lamp" style="background:{c}"></i>'
                     f'<span><b>{lbl} ({nm} light)</b>  <span class="lead">Water Resources Agency, {e(en_date(pub))}</span></span></div></section>')
        elif ja:
            nm, lbl, _ = i18n_ja.LIGHTS[k]
            light = (f'<section class="box"><h2>{e(i18n_ja.COUNTIES.get(county, county))}の水情信号</h2><div class="light">'
                     f'<i class="lamp" style="background:{c}"></i>'
                     f'<span><b>{lbl}（{nm}）</b>　<span class="lead">経済部水利署 {e(pub)} 発表</span></span></div></section>')
        elif ko:
            nm, lbl, _ = i18n_ko.LIGHTS[k]
            light = (f'<section class="box"><h2>{e(i18n_ko.COUNTIES.get(county, county))} 물 수급 신호</h2><div class="light">'
                     f'<i class="lamp" style="background:{c}"></i>'
                     f'<span><b>{lbl}({nm})</b>  <span class="lead">경제부 수리서 {e(pub)} 발표</span></span></div></section>')
        else:
            light = (f'<section class="box"><h2>{e(county)}水情燈號</h2><div class="light"><i class="lamp" style="background:{c}"></i>'
                     f'<span><b>{lbl}（{nm}）</b>　<span class="lead">經濟部水利署 {e(pub)} 公告</span></span></div></section>')

    facts = ""
    if en or ja or ko:
        T = i18n_en if en else i18n_ja if ja else i18n_ko
        rows = ""
        if county:
            rows += f"<tr><th>{L(lang, '', 'Location', '所在地', '위치')}</th><td>{e(T.COUNTIES.get(county, county))}</td></tr>"
        if info and str(info.get("型式") or "").strip() in T.DAM_TYPES:
            rows += f"<tr><th>{L(lang, '', 'Dam type', '型式', '형식')}</th><td>{e(T.DAM_TYPES[str(info['型式']).strip()])}</td></tr>"
        if info and str(info.get("壩堰高") or "").strip() not in ("", "…"):
            rows += f"<tr><th>{L(lang, '', 'Dam height', '堤高', '댐 높이')}</th><td>{e(str(info['壩堰高']).strip())} m</td></tr>"
        purpose = (info or {}).get("功能") or r.get("purpose")
        if purpose:
            rows += f"<tr><th>{L(lang, '', 'Purpose', '目的', '용도')}</th><td>{e(T.purposes(purpose))}</td></tr>"
        if rows:
            facts = f'<section class="box"><h2>{L(lang, "", f"About {e(name)}", f"{e(name)}の基本データ", f"{e(name)} 기본 정보")}</h2><table>{rows}</table></section>'
    elif info:
        rows = "".join(f"<tr><th>{lbl}</th><td>{e(str(info[k]).strip())}</td></tr>"
                       for k, lbl in INFO_FIELDS if str(info.get(k) or "").strip() not in ("", "…"))
        if r.get("purpose") and "功能" not in info:
            rows += f"<tr><th>用途</th><td>{e(r['purpose'])}</td></tr>"
        facts = f'<section class="box"><h2>{e(name)}基本資料</h2><table>{rows}</table></section>'
    elif r.get("purpose"):
        facts = f'<section class="box"><h2>{e(name)}基本資料</h2><table><tr><th>用途</th><td>{e(r["purpose"])}</td></tr></table></section>'

    others = "".join(
        f'<li><a href="../{x["id"]}/">{e(tr_name(x))}</a>'
        + (f'<span>{x["percent"]:.1f}%</span>' if ok(x) else "") + "</li>"
        for x in peers if x["id"] != rid)
    if others:
        h = L(lang, f"{e(region)}其他水庫", f"Other reservoirs in {e(region)}", f"{e(region)}のその他のダム", f"{e(region)}의 다른 저수지")
        others = f'<section class="box"><h2>{h}</h2><ul class="links">{others}</ul></section>'

    image = "reservoir/og.png"
    if en:
        bar = site_nav.nav("reservoir", '<a class="sitesection" href="../">Taiwan Reservoirs</a>', "en", path)
        top = (f'<nav class="crumb"><a href="../">Taiwan reservoirs</a> › {e(region)}</nav>\n'
               f'  <h1>{e(name)}</h1>\n'
               f'  <p class="lead">{e(region)} · observed {e(when)} · updated {e(updated)}</p>')
        cta = "See all reservoirs on the map"
        foot = ("<div>Source: Water Resources Agency (WRA), Ministry of Economic Affairs, open data (hourly reservoir conditions, "
                "daily operations, reservoir facts); updated hourly. Storage % = effective storage ÷ effective capacity. "
                "1 million m³ = 1 billion litres.</div>\n"
                f"    <div>{FOOT[lang]}</div>")
    elif ja:
        bar = site_nav.nav("reservoir", '<a class="sitesection" href="../">台湾のダム貯水率</a>', "ja", path)
        top = (f'<nav class="crumb"><a href="../../">Taiwan Data 台湾データ</a> › <a href="../">台湾のダム貯水率</a> › {e(region)}</nav>\n'
               f'  <h1>{e(name)}のリアルタイム貯水率</h1>\n'
               f'  <p class="lead">{e(region)}・{e(when)} 観測・更新 {e(updated)}</p>')
        cta = "台湾全体のダム地図を見る"
        foot = ("<div>出典：経済部水利署オープンデータ（ダム水情データ、ダム日報、ダム基本データ）、毎時更新。"
                "貯水率＝有効貯水量 ÷ 有効貯水容量。1万m³は約1万トンの水です。</div>\n"
                f"    <div>{FOOT[lang]}</div>")
    elif ko:
        bar = site_nav.nav("reservoir", '<a class="sitesection" href="../">대만 저수지 저수율</a>', "ko", path)
        top = (f'<nav class="crumb"><a href="../../">Taiwan Data 대만 데이터</a> › <a href="../">대만 저수지 저수율</a> › {e(region)}</nav>\n'
               f'  <h1>{e(name)} 실시간 저수율</h1>\n'
               f'  <p class="lead">{e(region)} · {e(when)} 관측 · 업데이트 {e(updated)}</p>')
        cta = "대만 전체 저수지 지도 보기"
        foot = ("<div>출처: 경제부 수리서 공공데이터(저수지 수문 데이터, 저수지 일일 운영 현황, 저수지 기본 데이터), 매시간 업데이트. "
                "저수율 = 유효저수량 ÷ 유효저수용량. 1만 m³는 물 약 1만 톤입니다.</div>\n"
                f"    <div>{FOOT[lang]}</div>")
    else:
        bar = site_nav.nav("reservoir", '<a class="sitesection" href="../">台灣水庫水情</a>', "zh", path)
        top = (f'<nav class="crumb"><a href="../../">Taiwan Data 台灣數據</a> › <a href="../">台灣水庫水情</a> › {e(region)}</nav>\n'
               f'  <h1>{e(name)}即時蓄水率</h1>\n'
               f'  <p class="lead">{e(region)}・{e(when)} 觀測・資料更新 {e(updated)}</p>')
        cta = "看全台水庫地圖"
        foot = ("<div>資料來源：經濟部水利署開放資料（水庫水情資料、水庫每日營運狀況、水庫基本資料），每小時更新。"
                "蓄水率＝有效蓄水量 ÷ 有效容量，1 萬立方公尺約等於 1 萬噸水。</div>\n"
                f"    <div>{FOOT[lang]}</div>")
    return f"""{head(title, desc, url, image, lang, path)}
<body>
{bar}
<div class="wrap">
  {top}
  <section class="box hero{" has-tank" if tank else ""}">
    <div class="info">
      <div class="big">{big}</div>
      <dl class="stats">{"".join(stats)}</dl>
      <a class="cta" href="../">{cta}</a>
    </div>
    {tank}
  </section>
  {light}
  {history_chart(hist, lang)}
  {history_table(hist, lang)}
  {facts}
  {others}
  <footer>
    {foot}
  </footer>
</div>
</body>
</html>
"""


def about_page(lang="zh"):
    path = "/about/"
    url = SITE + site_nav.lang_url(lang, path)
    if lang in ("en", "ja", "ko"):
        if lang == "en":
            title = "About | Taiwan Data"
            desc = "Taiwan Data is an independent site that compiles statistics from Taiwan government open data."
            bar = site_nav.nav("about", '<h1 class="sitesection">About</h1>', "en", path)
            h_about, h_contact = "About this site", "Contact"
            about = ("Taiwan Data turns Taiwan's government open data into simple tools: live reservoir levels and water alerts,\n"
                     "    monthly births and deaths, flight load factors, and passenger and tourism statistics. Every figure comes from official sources and is updated automatically.")
            contact = "Email us: "
        elif lang == "ko":
            title = "사이트 소개｜Taiwan Data 대만 데이터"
            desc = "Taiwan Data 대만 데이터는 대만 정부 공공데이터를 정리·집계한 개인 운영 사이트입니다."
            bar = site_nav.nav("about", '<h1 class="sitesection">사이트 소개</h1>', "ko", path)
            h_about, h_contact = "사이트 소개", "문의"
            about = ("Taiwan Data는 대만 정부의 공공데이터를 간단한 도구로 정리한 사이트입니다. 저수지 실시간 저수율과 물 수급 신호,\n"
                     "    월별 출생·사망 수, 항공편 탑승률, 여객 수 등을 보여 줍니다. 모든 수치는 공식 출처에서 가져오며 자동으로 업데이트됩니다.")
            contact = "이메일 문의: "
        else:
            title = "このサイトについて｜Taiwan Data 台湾データ"
            desc = "Taiwan Data 台湾データは、台湾政府のオープンデータを整理・集計した個人運営のサイトです。"
            bar = site_nav.nav("about", '<h1 class="sitesection">このサイトについて</h1>', "ja", path)
            h_about, h_contact = "このサイトについて", "お問い合わせ"
            about = ("Taiwan Data は、台湾政府のオープンデータをシンプルなツールにまとめたサイトです。ダムのリアルタイム貯水率と水情信号、\n"
                     "    毎月の出生数・死亡数、航空便の搭乗率、旅客数などを掲載しています。数値はすべて公式の出典によるもので、自動で更新されます。")
            contact = "メールでどうぞ："
        return f"""{head(title, desc, url, "og.png", lang, path)}
<body>
{bar}
<div class="wrap prose">
  <section class="box">
    <h2>{h_about}</h2>
    <p>{about}</p>
  </section>
  <section class="box">
    <h2>{h_contact}</h2>
    <p>{contact}<a href="mailto:contact@taiwandata.info">contact@taiwandata.info</a></p>
  </section>
  <footer><div>{FOOT[lang]}</div></footer>
</div>
</body>
</html>
"""
    title = "關於本站｜Taiwan Data 台灣數據"
    desc = "Taiwan Data 台灣數據是個人經營的網站，整理與統計台灣政府開放資料。"
    return f"""{head(title, desc, url, "og.png", "zh", path)}
<body>
{site_nav.nav("about", '<h1 class="sitesection">關於本站</h1>', "zh", path)}
<div class="wrap prose">
  {f'<section class="box"><h2>關於我</h2><p>{ABOUT_ME}</p></section>' if ABOUT_ME else ""}
  <section class="box">
    <h2>聯絡我</h2>
    <p>{CONTACT}</p>
  </section>
  <footer><div>{FOOT["zh"]}</div></footer>
</div>
</body>
</html>
"""


def translate(t, pairs, what):
    """把中文版 HTML 照 (中文, 外文) 清單逐一替換；找不到的印出來（中文版改字後要一起改清單）。"""
    for zh, other in pairs:
        if zh not in t:
            print(f"注意：{what}找不到要翻譯的文字：{zh[:40]}…")
        t = t.replace(zh, other)
    return t


def use_ja_font(out):
    """日文頁改用 Noto Sans JP（日文字形），其餘不變。"""
    for f in (out / "jp").rglob("*.html"):
        t = f.read_text(encoding="utf-8")
        t2 = t.replace("family=Noto+Sans+TC:", "family=Noto+Sans+JP:").replace('"Noto Sans TC",', '"Noto Sans JP","Noto Sans TC",')
        if t2 != t:
            f.write_text(t2, encoding="utf-8")


def use_ko_font(out):
    """韓文頁改用 Noto Sans KR（韓文字形），其餘不變。"""
    for f in (out / "kr").rglob("*.html"):
        t = f.read_text(encoding="utf-8")
        t2 = t.replace("family=Noto+Sans+TC:", "family=Noto+Sans+KR:").replace('"Noto Sans TC",', '"Noto Sans KR","Noto Sans TC",')
        if t2 != t:
            f.write_text(t2, encoding="utf-8")


def old_ja_redirects(out):
    """日文版原本放在 /ja/（2026-10-17 上線半小時），改成 /jp/ 後舊網址自動轉過去。"""
    for f in (out / "jp").rglob("index.html"):
        rel = f.parent.relative_to(out / "jp").as_posix()
        new = f"/jp/{rel}/" if rel != "." else "/jp/"
        d = out / "ja" / rel
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(
            f'<!doctype html>\n<html lang="ja"><head><meta charset="utf-8">'
            f'<link rel="canonical" href="{SITE}{new}"><meta name="robots" content="noindex">'
            f'<meta http-equiv="refresh" content="0; url={new}">'
            f'<script>location.replace("{new}" + location.search + location.hash)</script></head>'
            f'<body><a href="{new}">{SITE}{new}</a></body></html>\n', encoding="utf-8")



def verify_tags():
    """Naver 搜尋引擎的網站驗證標籤。驗證碼放在 GitHub Secrets 的 NAVER_SITE_VERIFICATION（貼整段標籤或只貼 content 都可以）。"""
    v = os.environ.get("NAVER_SITE_VERIFICATION", "").strip()
    m = re.search(r'content="([^"]+)"', v)
    v = m.group(1) if m else v
    v = re.sub(r"[^A-Za-z0-9_-]", "", v)
    return f'\n<meta name="naver-site-verification" content="{v}">' if v else ""


def daum_line():
    """Daum 網站管理工具要求放在 robots.txt 的驗證行。內容放在 GitHub Secrets 的 DAUM_WEBMASTER_LINE。"""
    v = os.environ.get("DAUM_WEBMASTER_LINE", "").strip().splitlines()
    v = v[0].strip() if v else ""
    if not v:
        return ""
    if not v.startswith("#"):
        v = "#DaumWebMasterTool:" + v
    return "\n" + re.sub(r"[^\x21-\x7e]", "", v) + "\n"


def main(out):
    out = Path(out)
    latest, info, hist, alert = load()
    updated = tw_time(latest.get("generated_at"))
    lastmod = (latest.get("generated_at") or "")[:10]
    named = [r for r in latest["reservoirs"] if r.get("name")]
    by_region = defaultdict(list)
    for r in sorted(named, key=lambda x: -(x.get("capacity") or 0)):
        by_region[r["region"]].append(r)

    def all_langs(path):
        return [SITE + site_nav.lang_url(k, path) for k, _, _, _ in site_nav.LANGS]

    urls = all_langs("/") + [f"{SITE}/reservoir/"] + all_langs("/about/")
    for lang, d in (("zh", out / "about"), ("en", out / "en/about"), ("ja", out / "jp/about"), ("ko", out / "kr/about")):
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(about_page(lang), encoding="utf-8")

    # 英文版、日文版首頁：用中文版 index.html 換掉文字
    home = out / "index.html"
    if home.exists():
        t = home.read_text(encoding="utf-8")
        for lang, pairs, what in (("en", i18n_en.HOME_HTML, "英文版首頁"), ("ja", i18n_ja.HOME_HTML, "日文版首頁"),
                                 ("ko", i18n_ko.HOME_HTML, "韓文版首頁")):
            (out / site_nav.DIR[lang]).mkdir(parents=True, exist_ok=True)
            (out / site_nav.DIR[lang] / "index.html").write_text(translate(t, pairs, what), encoding="utf-8")
    updated_en = en_time(latest.get("generated_at"))
    for r in named:
        for lang, base in (("zh", out / "reservoir"), ("en", out / "en/reservoir"), ("ja", out / "jp/reservoir"), ("ko", out / "kr/reservoir")):
            d = base / r["id"]
            d.mkdir(parents=True, exist_ok=True)
            page = reservoir_page(r, info.get(r["id"]), hist.get(r["id"], []), alert, by_region[r["region"]],
                                  updated_en if lang == "en" else updated, lang)
            (d / "index.html").write_text(page, encoding="utf-8")
        urls += all_langs(f"/reservoir/{r['id']}/")

    # 英文版、日文版水庫總覽：用中文版 reservoir/index.html 換掉文字，JavaScript 靠 window.I18N 顯示外文
    idx = out / "reservoir/index.html"
    if idx.exists():
        src = idx.read_text(encoding="utf-8")
        for lang, T, section, what in (("en", i18n_en, "Taiwan Reservoirs", "英文版總覽頁"), ("ja", i18n_ja, "台湾のダム貯水率", "日文版總覽頁"),
                                      ("ko", i18n_ko, "대만 저수지 저수율", "韓文版總覽頁")):
            t = translate(src, T.OVERVIEW_HTML, what)
            i18n = {"txt": T.TXT, "regions": T.REGIONS, "counties": T.COUNTIES,
                    "lights": T.LIGHTS, "res": T.RESERVOIRS, "legend": getattr(T, "LEGEND", None)}
            t = (f'<!doctype html>\n<html lang="{HTML_LANG[lang]}">\n' + t
                 .replace("<!--I18N-->", f"<script>window.I18N = {json.dumps(i18n, ensure_ascii=False)};</script>")
                 .replace("<!--SITE_NAV-->", site_nav.nav("reservoir", f'<h1 class="sitesection">{section}</h1>', lang, "/reservoir/"))
                 .replace("<!--RESERVOIR_LINKS-->", "".join(
                     f'<div><b>{T.REGIONS.get(g, g)}</b><ul class="links">' + "".join(
                         f'<li><a href="{x["id"]}/">{e(T.name(x["id"], x["name"]))}</a></li>' for x in by_region[g])
                     + "</ul></div>" for g in REGIONS if by_region.get(g))))
            (out / site_nav.DIR[lang] / "reservoir").mkdir(parents=True, exist_ok=True)
            (out / site_nav.DIR[lang] / "reservoir/index.html").write_text(t, encoding="utf-8")
        urls += all_langs("/reservoir/")[1:]

    sections = {
        "power": {"zh": "台灣今日電力", "en": "Taiwan Power", "ja": "台湾の電力", "ko": "대만 전력"},
        "births": {"zh": "台灣出生與死亡", "en": "Taiwan Births &amp; Deaths", "ja": "台湾の出生と死亡", "ko": "대만 출생·사망"},
        "flights": {"zh": "台灣航班", "en": "Taiwan Flights", "ja": "台湾の航空便", "ko": "대만 항공편"},
        "travel": {"zh": "台灣旅客人次", "en": "Taiwan Tourism", "ja": "台湾の旅客数", "ko": "대만 여객 수"},
    }

    def section_nav(key):
        return lambda lang, path: site_nav.nav(key, f'<h1 class="sitesection">{sections[key][lang]}</h1>', lang, path)
    urls += build_births.build(out, head, section_nav("births"))
    urls += build_power.build(out, head, section_nav("power"))
    urls += build_flights.build(out, head, section_nav("flights"))
    urls += build_travel.build(out, head, section_nav("travel"))

    # 首頁與水庫總覽頁：分頁小圖示、最上方的選單列
    pages = [
        ("index.html", site_nav.nav("home", "", "zh", "/")),
        ("en/index.html", site_nav.nav("home", "", "en", "/")),
        ("jp/index.html", site_nav.nav("home", "", "ja", "/")),
        ("kr/index.html", site_nav.nav("home", "", "ko", "/")),
        ("reservoir/index.html", site_nav.nav("reservoir", '<h1 class="sitesection">台灣水庫水情</h1>', "zh", "/reservoir/")),
        ("en/reservoir/index.html", ""),
        ("jp/reservoir/index.html", ""),
        ("kr/reservoir/index.html", ""),
    ]
    for f, bar in pages:
        if (out / f).exists():
            t = (out / f).read_text(encoding="utf-8")
            t = (t.replace("<!--SITE_ICONS-->", site_nav.ICONS + verify_tags()).replace("<!--SITE_NAV-->", bar).replace("<!--I18N-->", "")
                 .replace("<!--HREFLANG-->", hreflang("/reservoir/" if "reservoir" in f else "/")))
            (out / f).write_text(t, encoding="utf-8")

    # 水庫總覽頁底部：全部水庫頁的連結（不靠 JavaScript，搜尋引擎找得到）
    idx = out / "reservoir/index.html"
    if idx.exists():
        groups = "".join(
            f'<div><b>{g}</b><ul class="links">' + "".join(
                f'<li><a href="{x["id"]}/">{e(x["name"])}</a></li>' for x in by_region[g]) + "</ul></div>"
            for g in REGIONS if by_region.get(g))
        idx.write_text(idx.read_text(encoding="utf-8").replace("<!--RESERVOIR_LINKS-->", groups), encoding="utf-8")

    use_ja_font(out)
    use_ko_font(out)
    old_ja_redirects(out)
    def sitemap(name, us):
        (out / name).write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            + "".join(f"  <url><loc>{u}</loc><lastmod>{lastmod}</lastmod></url>\n" for u in us)
            + "</urlset>\n", encoding="utf-8")
    sitemap("sitemap.xml", urls)
    # 韓文頁另外一份，給 Naver、Daum 提交用
    sitemap("sitemap-kr.xml", [u for u in urls if u.startswith(f"{SITE}/kr/")])
    (out / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\n{daum_line()}\nSitemap: {SITE}/sitemap.xml\nSitemap: {SITE}/sitemap-kr.xml\n", encoding="utf-8")
    print(f"{len(named)} 座水庫頁、sitemap {len(urls)} 個網址")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "_site")
