"""首頁「台灣概覽」：左邊是位置與基本資料（東亞地圖、人口），右邊是各主題的最新數字表。

build_pages.py 每小時呼叫 build(out)，數字直接寫進 HTML（搜尋引擎看得到，也不必等 JavaScript）。
每一列的數字和該主題頁的標題一致：水庫用 21 座主要水庫的有效容量加權蓄水率，電力用台電即時發電合計，
出生用戶政司最新月份，航班用民航局國際及兩岸定期航班載客率，旅客用觀光署年度來台旅客。
"""
import calendar
import csv
import json
from collections import defaultdict
from datetime import datetime
from html import escape as e
from pathlib import Path

import worldmap

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "data"
# 水利署的主要水庫（總覽頁地圖標名字的那一群再加上各區主力），蓄水率依有效容量加權
MAJOR = {"10201", "10205", "10401", "10405", "10501", "10601", "20101", "20201", "20202", "20501", "20502",
         "20503", "20509", "30301", "30401", "30501", "30502", "30503", "30802", "30901", "31201"}
FUELS = ["nuclear", "coal", "lng", "cogen", "oil", "solar", "wind", "hydro", "other", "storage"]


def rows(p):
    with open(D / p, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def data():
    """首頁要的數字（只用官方資料）。"""
    out = {}
    lat = json.loads((D / "latest.json").read_text(encoding="utf-8"))
    maj = [r for r in lat["reservoirs"] if r["id"] in MAJOR and r.get("percent") is not None
           and not r.get("suspect") and r.get("capacity")]
    cap = sum(r["capacity"] for r in maj)
    ly = [r for r in maj if r.get("last_year_percent") is not None]
    daily = defaultdict(lambda: [0.0, 0.0])
    for r in rows("history.csv"):
        if r["id"] in MAJOR and r["percent"] and r["capacity"]:
            daily[r["date"]][0] += float(r["percent"]) * float(r["capacity"])
            daily[r["date"]][1] += float(r["capacity"])
    days = sorted(daily)[-30:]
    out["reservoir"] = dict(
        pct=sum(r["storage"] for r in maj) / cap * 100,
        last_year=sum(r["last_year_percent"] * r["capacity"] for r in ly) / sum(r["capacity"] for r in ly) if ly else None,
        when=max(r["observed_at"] for r in maj), count=len(maj),
        spark=[daily[d][0] / daily[d][1] for d in days])

    pw = json.loads((D / "power/latest.json").read_text(encoding="utf-8"))
    rv = rows("power/reserve.csv")[-1]
    today = pw["time"][:10]
    curve = [sum(float(r[f] or 0) for f in FUELS) / 10 for r in rows(f"power/hourly/{today[:7]}.csv") if r["time"].startswith(today)]
    rate = float(rv["rate"])
    out["power"] = dict(now=sum((u["mw"] or 0) for u in pw["units"]) / 10, when=pw["time"], rate=rate, rate_date=rv["date"],
                        light="green" if rate >= 10 else "yellow" if rate >= 6 else "orange", spark=curve)

    B, Dd, P = defaultdict(int), defaultdict(int), defaultdict(int)
    for r in rows("births/monthly.csv"):
        m = r["month"]
        B[m] += int(r["births_m"]) + int(r["births_f"])
        Dd[m] += int(r["deaths_m"]) + int(r["deaths_f"])
        P[m] += int(r["population"])
    ms = sorted(B)
    last = ms[-1]
    ago = f"{int(last[:4]) - 1}{last[4:]}"
    out["births"] = dict(month=last, births=B[last], deaths=Dd[last], yoy=(B[last] / B[ago] - 1) * 100 if B.get(ago) else None,
                         spark=[B[m] for m in ms[-24:]])
    out["population"] = dict(month=last, pop=P[last], year_change=P[last] - P[ago] if P.get(ago) else None)

    lf = [r for r in rows("flights/loadfactor.csv") if r["scope"] == "ALL" and r["region"] == "all"]
    out["flights"] = dict(month=lf[-1]["month"], lf=float(lf[-1]["lf"]), pax=int(lf[-1]["pax"]),
                          prev=float(lf[-2]["lf"]) if len(lf) > 1 else None, spark=[float(r["lf"]) for r in lf])

    tot = [r for r in rows("travel/totals.csv") if r["inbound"]]
    cur, prev = tot[-1], tot[-2]
    out["travel"] = dict(year=cur["year"], inbound=int(cur["inbound"]), outbound=int(cur["outbound"] or 0),
                         yoy=(int(cur["inbound"]) / int(prev["inbound"]) - 1) * 100,
                         spark=[int(r["inbound"]) for r in tot if int(r["year"]) >= 2010])
    out["generated_at"] = lat.get("generated_at")
    return out


# ---------- 文字（四種語言）
T = {
    "zh": dict(
        title="Taiwan Data 台灣數據：台灣概覽，水庫、電力、人口、航班的最新數字",
        desc="一頁看懂台灣最新的官方數字：主要水庫蓄水率、現在用電、每月出生人數、航班載客率、來台旅客人次，每個主題都能點進去看細節。",
        eyebrow="台灣概覽", h1="一眼看懂台灣", lead="水、電、人口、航班、旅客：台灣最新的官方數字，每個主題都能點進去看細節。",
        updated="資料更新", ctx="位置與基本資料", tbl="探索台灣數據", tbl_sub="五個主題的最新數字，點進去看細節。",
        cols=("主題", "最新數字", "趨勢", "資料時間"),
        f_loc=("位置", "東亞・西太平洋"), f_tz=("時區", "UTC+8"), f_pop="人口", f_div=("行政區", "22 個縣市"),
        pop_fmt=lambda p: f"{p / 1e4:,.1f}<small> 萬人</small>", pop_when=lambda m: f"{m[:4]} 年 {int(m[5:])} 月底・內政部戶政司",
        pop_chg=lambda c: f"比一年前{'少' if c < 0 else '多'} {abs(c) / 1e4:.1f} 萬人",
        map_label="台灣在東亞的位置", names={"156": "中國", "392": "日本", "410": "韓國", "608": "菲律賓", "158": "台灣", "sea": "太平洋"},
        km="公里",
        rows={
            "reservoir": ("台灣水庫水情", "蓄水率與水情燈號地圖", "主要水庫蓄水率", "近 30 天"),
            "power": ("台灣今日電力", "用電、備轉容量率與發電來源", "現在用電", "今天"),
            "births": ("台灣出生與死亡", "各縣市比較與歷年趨勢", "出生人數", "近 24 個月"),
            "flights": ("台灣航班", "航線、航空公司與載客率", "國際及兩岸載客率", "今年各月"),
            "travel": ("台灣旅客人次", "來台旅客、出國人次與機場", "來台旅客", "2010 年起"),
        },
        unit_wan="萬", unit_power="萬瓩", unit_people="人", unit_pt="個百分點",
        vs_ly="比去年同期", vs_lm="比上月", vs_ly_m="比去年同月", vs_py="比前一年",
        reserve=lambda r, l, d: f"備轉容量率 {r:.1f}%・{dict(green='綠燈', yellow='黃燈', orange='橘燈')[l]}（{int(d[5:7])}/{int(d[8:])}）",
        deaths=lambda n: f"死亡 {n:,} 人",
        pax=lambda n: f"旅客 {n / 1e4:,.0f} 萬人次",
        when_dt=lambda t: f"{t.month}/{t.day} {t:%H:%M}", when_m=lambda m: f"{m[:4]} 年 {int(m[5:])} 月", when_y=lambda y: f"{y} 年",
        src_t="資料來源", src="經濟部水利署、台灣電力公司、內政部戶政司、交通部民用航空局、交通部觀光署的開放資料。",
        about_t="關於本站", about="整理台灣政府開放資料，數字都標明資料時間。", about_link="關於本站",
        ng_t="非政府網站", ng="本站為個人經營，和任何政府機關沒有關係。", contact="歡迎來信：contact@taiwandata.info",
        open_ctx="展開", go="看細節"),
}

ICONS = {  # Material Icons（Apache 2.0）
    "reservoir": "M12 2c-5.33 4.55-8 8.48-8 11.8 0 4.98 3.8 8.2 8 8.2s8-3.22 8-8.2C20 10.48 17.33 6.55 12 2z",
    "power": "M11 21h-1l1-7H7.5c-.58 0-.57-.32-.38-.66.19-.34.05-.08.07-.12C8.48 10.94 10.42 7.54 13 3h1l-1 7h3.5c.49 0 .56.33.47.51l-.07.15C12.96 17.55 11 21 11 21z",
    "births": ("M16 11c1.66 0 2.99-1.34 2.99-3S17.66 5 16 5c-1.66 0-3 1.34-3 3s1.34 3 3 3zm-8 0c1.66 0 2.99-1.34 2.99-3S9.66 5 8 5C6.34 5 5 6.34 5 8s1.34 3 3 3zm0 2c-2.33 0-7 1.17-7 3.5V19h14v-2.5c0-2.33-4.67-3.5-7-3.5zm8 0c-.29 0-.62.02-.97.05 1.16.84 1.97 1.97 1.97 3.45V19h6v-2.5c0-2.33-4.67-3.5-7-3.5z"),
    "flights": "M21 16v-2l-8-5V3.5c0-.83-.67-1.5-1.5-1.5S10 2.67 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5l8 2.5z",
    "travel": "M20 7h-4V5c0-1.1-.9-2-2-2h-4c-1.1 0-2 .9-2 2v2H4c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V9c0-1.1-.9-2-2-2zm-6 0h-4V5h4v2z",
}
URL = {"reservoir": "reservoir/", "power": "power/", "births": "births/", "flights": "flights/", "travel": "tourism/"}


def spark(vals, w=132, h=40):
    """小折線圖，最後一點加圓點。"""
    if len(vals) < 2:
        return ""
    lo, hi = min(vals), max(vals)
    span = (hi - lo) or 1
    pts = [(2 + i * (w - 6) / (len(vals) - 1), 3 + (h - 6) * (1 - (v - lo) / span)) for i, v in enumerate(vals)]
    d = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    area = f"2,{h} " + d + f" {pts[-1][0]:.1f},{h}"
    x, y = pts[-1]
    return (f'<svg class="spark" viewBox="0 0 {w} {h}" aria-hidden="true"><polygon class="sa" points="{area}"/>'
            f'<polyline points="{d}"/><circle cx="{x:.1f}" cy="{y:.1f}" r="3"/></svg>')


def region_map(t):
    """東亞地圖：world-map.json 的國界，台灣塗主色並加一圈光暈。"""
    w = worldmap.world()
    x0, y0 = worldmap.xy(44, 101)
    x1, y1 = worldmap.xy(4, 146)
    keep = {"156", "392", "410", "408", "608", "158", "704", "418", "116", "764", "104", "496", "360", "458", "096", "626", "356", "050", "064", "524", "643", "344", "446"}
    paths = "".join(f'<path class="c{" tw" if k == "158" else ""}" d="{w["countries"][k]}"/>' for k in sorted(keep) if k in w["countries"])
    n = t["names"]

    def lab(key, lat, lon, cls=""):
        x, y = worldmap.xy(lat, lon)
        return f'<text class="{cls}" x="{x}" y="{y}">{e(n[key])}</text>'
    tx, ty = worldmap.xy(23.7, 120.95)
    # 比例尺：北緯 23.5 度的東西向距離
    import math
    per_km = 0.9 * w["s"] / (111.32 * math.cos(math.radians(23.5)))
    sx, sy = worldmap.xy(6.8, 102.5)
    bar = (f'<g class="scale"><path d="M{sx} {sy}h{1000 * per_km:.1f}"/>'
           f'<path d="M{sx} {sy - 1.2}v2.4M{sx + 500 * per_km:.1f} {sy - 1.2}v2.4M{sx + 1000 * per_km:.1f} {sy - 1.2}v2.4"/>'
           f'<text x="{sx}" y="{sy - 2.4}">0</text><text x="{sx + 500 * per_km:.1f}" y="{sy - 2.4}">500</text>'
           f'<text x="{sx + 1000 * per_km:.1f}" y="{sy - 2.4}">1,000 {e(t["km"])}</text></g>')
    return (f'<svg class="rmap" viewBox="{x0} {y0} {round(x1 - x0, 1)} {round(y1 - y0, 1)}" role="img" aria-label="{e(t["map_label"])}">'
            f'<rect class="sea" x="{x0 - 5}" y="{y0 - 5}" width="{x1 - x0 + 10}" height="{y1 - y0 + 10}"/>'
            f'<g class="land">{paths}</g>'
            f'<circle class="halo" cx="{tx}" cy="{ty}" r="5.5"/><circle class="ring" cx="{tx}" cy="{ty}" r="5.5"/>'
            + lab("156", 31, 111) + lab("392", 37.6, 141.5) + lab("410", 36.3, 126.6, "s") + lab("608", 12.8, 125.2)
            + lab("sea", 24, 136.5, "sea-t") + f'<text class="twl" x="{tx + 7}" y="{ty + 1.5}">{e(n["158"])}</text>'
            + bar + "</svg>")


def taiwan_silhouette():
    """首頁大標右邊的台灣本島（縣市界細線），來自 reservoir/taiwan-map.json。"""
    m = json.loads((ROOT / "reservoir/taiwan-map.json").read_text(encoding="utf-8"))
    return (f'<svg class="tw-sil" viewBox="0 0 {m["width"]} {m["height"]}" aria-hidden="true">'
            + "".join(f'<path d="{d}"/>' for d in m["counties"].values()) + "</svg>")


def page(lang="zh", theme="glance"):
    t = T[lang]
    d = data()
    r, p, b, f, v = d["reservoir"], d["power"], d["births"], d["flights"], d["travel"]
    dt = lambda iso: t["when_dt"](datetime.fromisoformat(iso))

    def chg(val, label, unit="%", digits=1):
        if val is None:
            return ""
        cls, arrow = ("up", "▲") if val > 0.05 else ("down", "▼") if val < -0.05 else ("flat", "▶")
        return f'<span class="chg">{e(label)} <b class="{cls}">{arrow} {abs(val):.{digits}f}{unit}</b></span>'
    pt = " " + t["unit_pt"] if lang == "zh" else " pt"
    items = [
        ("reservoir", f"{r['pct']:.1f}<small>%</small>",
         chg(r["pct"] - r["last_year"] if r["last_year"] is not None else None, t["vs_ly"], pt), r["spark"], dt(r["when"])),
        ("power", f"{p['now']:,.0f}<small> {t['unit_power']}</small>",
         f'<span class="chg"><i class="lamp {p["light"]}"></i>{e(t["reserve"](p["rate"], p["light"], p["rate_date"]))}</span>', p["spark"], dt(p["when"])),
        ("births", f"{b['births']:,}<small> {t['unit_people']}</small>",
         chg(b["yoy"], t["vs_ly_m"]) + f'<span class="chg2">{e(t["deaths"](b["deaths"]))}</span>', b["spark"], t["when_m"](b["month"])),
        ("flights", f"{f['lf']:.1f}<small>%</small>",
         chg(f["lf"] - f["prev"] if f["prev"] is not None else None, t["vs_lm"], pt) + f'<span class="chg2">{e(t["pax"](f["pax"]))}</span>',
         f["spark"], t["when_m"](f["month"])),
        ("travel", f"{v['inbound'] / 1e4:,.0f}<small> {t['unit_wan']}</small>", chg(v["yoy"], t["vs_py"]), v["spark"], t["when_y"](v["year"])),
    ]
    trs = []
    for i, (k, num, change, sp, when) in enumerate(items):
        name, sub, label, sp_cap = t["rows"][k]
        trs.append(
            f'<a class="row t-{k}" href="{URL[k]}"><span class="ix">{i + 1:02d}</span>'
            f'<span class="ic"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="{ICONS[k]}"/></svg></span>'
            f'<span class="nm"><b>{e(name)}</b><span>{e(sub)}</span></span>'
            f'<span class="fig"><span class="num">{num}</span><span class="lbl">{e(label)}</span>{change}</span>'
            f'<span class="sp">{spark(sp)}<span>{e(sp_cap)}</span></span>'
            f'<span class="when">{e(when)}</span><span class="go" aria-label="{e(t["go"])}">→</span></a>')
    pop = d["population"]
    facts = (
        f'<dl class="facts"><div><dt>{e(t["f_loc"][0])}</dt><dd>{e(t["f_loc"][1])}</dd></div>'
        f'<div><dt>{e(t["f_tz"][0])}</dt><dd>{e(t["f_tz"][1])}</dd></div>'
        f'<div><dt>{e(t["f_pop"])}</dt><dd><span class="big">{t["pop_fmt"](pop["pop"])}</span>'
        f'<span class="note">{e(t["pop_when"](pop["month"]))}</span>'
        + (f'<span class="note">{e(t["pop_chg"](pop["year_change"]))}</span>' if pop["year_change"] is not None else "")
        + f'</dd></div><div><dt>{e(t["f_div"][0])}</dt><dd>{e(t["f_div"][1])}</dd></div></dl>')
    upd = dt(d["generated_at"]) if d.get("generated_at") else ""
    return f"""<body class="th-{theme}">
<!--SITE_NAV-->
<header class="hero"><div class="w hero-in"><div>
  <p class="eyebrow">{e(t["eyebrow"])}</p>
  <h1>{e(t["h1"])}</h1>
  <p class="lead">{e(t["lead"])}</p>
  <p class="upd">{e(t["updated"])} {e(upd)}</p>
</div>{taiwan_silhouette()}</div></header>
<main class="w grid">
  <details class="ctx" open>
    <summary><h2>{e(t["ctx"])}</h2><span class="plus" aria-hidden="true"></span></summary>
    <div class="mapbox">{region_map(t)}</div>
    {facts}
  </details>
  <section class="topics">
    <h2>{e(t["tbl"])}</h2>
    <p class="sub">{e(t["tbl_sub"])}</p>
    <div class="thead"><span></span><span>{e(t["cols"][0])}</span><span>{e(t["cols"][1])}</span><span>{e(t["cols"][2])}</span><span>{e(t["cols"][3])}</span><span></span></div>
    {"".join(trs)}
  </section>
</main>
<footer class="foot"><div class="w cols">
  <div><b>{e(t["src_t"])}</b><p>{e(t["src"])}</p></div>
  <div><b>{e(t["about_t"])}</b><p>{e(t["about"])} <a href="about/">{e(t["about_link"])} →</a></p></div>
  <div><b>{e(t["ng_t"])}</b><p>{e(t["ng"])}<br>{e(t["contact"])}</p></div>
</div></footer>
<script>(function(){{var d=document.querySelector(".ctx");if(d&&window.matchMedia("(max-width: 760px)").matches)d.removeAttribute("open");}})();</script>
</body>"""


CSS = """
* { box-sizing:border-box; }
body { margin:0; background:var(--bg); color:var(--fg); font-family:"Noto Sans TC","PingFang TC","Microsoft JhengHei",system-ui,sans-serif;
  font-size:15px; line-height:1.6; font-variant-numeric:tabular-nums; }
a { color:inherit; }
.w { max-width:1320px; margin:0 auto; padding-inline:max(16px, env(safe-area-inset-left)) max(16px, env(safe-area-inset-right)); }
@media (min-width:761px) { .w { padding-inline:32px; } }
.hero { background:var(--hero-bg); color:var(--hero-fg); padding:40px 0 34px; }
.eyebrow { margin:0 0 8px; font-size:13px; font-weight:700; letter-spacing:.16em; color:var(--eyebrow); }
.hero h1 { margin:0; font-size:clamp(36px, 7vw, 64px); line-height:1.08; font-weight:700; letter-spacing:.02em; }
.hero .lead { margin:14px 0 0; font-size:clamp(15px, 1.9vw, 18px); color:var(--hero-muted); max-width:44em; }
.hero .upd { margin:8px 0 0; font-size:13px; color:var(--hero-muted); }
.hero-in { display:grid; grid-template-columns:minmax(0, 1fr) auto; align-items:center; gap:20px; }
.tw-sil { display:block; height:260px; width:auto; margin:-16px 8px -20px 0; filter:var(--sil-glow, none); }
.tw-sil path { fill:var(--sil); stroke:var(--sil-line); stroke-width:2.5; stroke-linejoin:round; }
@media (max-width:760px) { .hero-in { align-items:start; gap:8px; } .tw-sil { height:118px; margin:2px 0 0; } }
.grid { display:grid; gap:24px; padding-top:28px; padding-bottom:44px; }
@media (min-width:1100px) { .grid { grid-template-columns:340px minmax(0, 1fr); gap:48px; } }
h2 { font-size:22px; margin:0; line-height:1.3; }
.ctx summary { list-style:none; display:flex; align-items:center; justify-content:space-between; gap:12px; }
.ctx summary::-webkit-details-marker { display:none; }
.plus { width:24px; height:24px; position:relative; flex:none; color:var(--accent); }
.plus::before, .plus::after { content:""; position:absolute; left:4px; right:4px; top:11px; height:2px; border-radius:1px; background:currentColor; }
.plus::after { transform:rotate(90deg); transition:transform .2s; }
.ctx[open] .plus::after { transform:rotate(0); }
@media (max-width:760px) {
  .ctx { border:1px solid var(--line); border-radius:var(--r); padding:12px 14px; background:var(--surface); }
  .ctx summary { cursor:pointer; } .ctx h2 { font-size:17px; } }
@media (min-width:761px) { .plus { display:none; } .ctx summary { pointer-events:none; } }
@media (min-width:761px) and (max-width:1099px) { .ctx[open] { display:grid; grid-template-columns:1fr 1fr; gap:0 28px; } .ctx summary { grid-column:1 / -1; } }
.mapbox { margin-top:14px; border-radius:var(--r); overflow:hidden; border:1px solid var(--map-edge, var(--line)); background:var(--sea); }
.rmap { display:block; width:100%; height:auto; }
.rmap .sea { fill:var(--sea); }
.rmap .c { fill:var(--land); stroke:var(--border); stroke-width:.3; stroke-linejoin:round; }
.rmap .c.tw { fill:var(--tw); stroke:none; }
.rmap .halo { fill:var(--halo); }
.rmap .ring { fill:none; stroke:var(--tw); stroke-width:.45; opacity:.7; }
.rmap text { font-size:4.2px; fill:var(--maplab); font-weight:500; letter-spacing:.2px; }
.rmap text.s { font-size:3.4px; }
.rmap .sea-t { font-style:italic; opacity:.75; letter-spacing:1px; }
.rmap .twl { font-size:5.2px; font-weight:700; fill:var(--tw-label, var(--tw)); }
.rmap .scale path { stroke:var(--maplab); stroke-width:.4; fill:none; }
.rmap .scale text { font-size:3px; }
.facts { margin:12px 0 0; }
.facts div { display:grid; grid-template-columns:88px minmax(0, 1fr); gap:12px; padding:12px 0; border-top:1px solid var(--line); }
.facts dt { font-weight:700; }
.facts dd { margin:0; }
.facts .big { display:block; font-size:28px; font-weight:700; line-height:1.15; color:var(--num); }
.facts .big small { font-size:15px; font-weight:500; }
.facts .note { display:block; font-size:13px; color:var(--muted); }
.topics .sub { margin:4px 0 16px; color:var(--muted); }
.thead, .row { display:grid; grid-template-columns:30px 52px minmax(0, 1.1fr) minmax(0, 1.3fr) 150px 104px 22px; gap:18px; align-items:center; }
.thead { padding:8px 16px; font-size:13px; font-weight:700; color:var(--muted); border-bottom:var(--thead-rule, 2px solid var(--fg)); }
.thead span:first-child { grid-column:span 2; }
.row { --tc:var(--accent); padding:18px 16px; border-bottom:1px solid var(--line); text-decoration:none; transition:background .15s; }
.row:hover { background:var(--row-hover); }
.ix { font-size:13px; font-weight:700; color:var(--ix, var(--muted)); }
.ic { width:52px; height:52px; border-radius:var(--ic-r, 14px); display:grid; place-items:center; background:var(--ic-bg); }
.ic svg { width:28px; height:28px; fill:var(--ic-fg); }
.nm b { display:block; font-size:18px; line-height:1.3; }
.nm span { display:block; font-size:14px; color:var(--muted); line-height:1.45; margin-top:3px; }
.num { display:block; font-size:36px; font-weight:700; line-height:1.08; color:var(--num); letter-spacing:-.01em; white-space:nowrap; }
.num small { font-size:16px; font-weight:500; margin-left:1px; letter-spacing:0; }
.lbl { display:block; font-size:14px; color:var(--muted); margin-top:3px; }
.chg, .chg2 { display:block; font-size:13px; margin-top:3px; color:var(--muted); }
.chg2 { margin-top:0; }
.chg b { font-weight:700; }
.up { color:var(--up); } .down { color:var(--down); } .flat { color:var(--muted); }
.lamp { display:inline-block; width:9px; height:9px; border-radius:50%; margin-right:6px; }
.lamp.green { background:#22a45d; } .lamp.yellow { background:#e2a700; } .lamp.orange { background:#f28c28; }
.sp svg { display:block; width:100%; height:42px; }
.sp span { display:block; font-size:12px; color:var(--muted); margin-top:2px; }
.spark polyline { fill:none; stroke:var(--spark); stroke-width:2; stroke-linejoin:round; stroke-linecap:round; vector-effect:non-scaling-stroke; }
.spark .sa { fill:var(--spark-fill); }
.spark circle { fill:var(--spark); }
.when { font-size:14px; color:var(--muted); }
.go { font-size:20px; font-weight:700; color:var(--go, var(--accent)); transition:transform .15s; }
.row:hover .go { transform:translateX(4px); }
@media (max-width:1099px) {
  .thead, .ix { display:none; }
  .row { grid-template-columns:52px minmax(0, 1fr) minmax(0, 1fr) 120px 22px; grid-template-areas:"ic nm fig sp go" "ic nm when sp go"; row-gap:2px; }
  .ic { grid-area:ic; } .nm { grid-area:nm; } .fig { grid-area:fig; } .sp { grid-area:sp; } .when { grid-area:when; font-size:13px; } .go { grid-area:go; } }
@media (max-width:760px) {
  .row { grid-template-columns:44px minmax(0, 1fr) 104px; grid-template-areas:"ic nm go" ". fig sp" ". when when"; gap:6px 14px; padding:16px 4px; align-items:start; }
  .ic { grid-area:ic; width:44px; height:44px; } .ic svg { width:24px; height:24px; }
  .nm { grid-area:nm; } .nm b { font-size:17px; } .nm span { font-size:13px; }
  .fig { grid-area:fig; } .num { font-size:32px; }
  .sp { grid-area:sp; align-self:center; } .sp span { text-align:right; }
  .when { grid-area:when; font-size:13px; }
  .go { grid-area:go; justify-self:end; } }
.foot { background:var(--foot-bg); color:var(--foot-fg); padding:28px 0 40px; border-top:var(--foot-rule, 1px solid var(--line)); }
.foot .cols { display:grid; gap:18px; }
@media (min-width:761px) { .foot .cols { grid-template-columns:repeat(3, 1fr); gap:36px; } }
.foot b { font-size:14px; }
.foot p { margin:4px 0 0; font-size:13px; color:var(--foot-muted); line-height:1.7; }
"""

# 五種配色（Shane 挑一種後，其他可以刪掉）
THEMES = {
    "midnight": """
:root { --sil:#0f2a47; --sil-line:rgba(56,189,248,.75); --sil-glow:drop-shadow(0 0 14px rgba(56,189,248,.45)); --bg:#07111f; --surface:#0d1b2e; --fg:#eaf2ff; --muted:#8ea3bd; --line:#1b2c44; --chip:#14243a; --r:16px;
  --accent:#38bdf8; --num:#ffffff; --hero-bg:transparent; --hero-fg:#ffffff; --hero-muted:#9fb3cc; --eyebrow:#38bdf8;
  --row-hover:#12233a; --ic-bg:rgba(56,189,248,.12); --ic-fg:#38bdf8; --up:#4ade80; --down:#fb7185;
  --sea:#081a2f; --land:#132a45; --border:rgba(148,190,240,.35); --maplab:#9fb3cc; --tw:#38bdf8; --halo:rgba(56,189,248,.22);
  --spark:#38bdf8; --spark-fill:rgba(56,189,248,.14); --foot-bg:#050d18; --foot-fg:#eaf2ff; --foot-muted:#8ea3bd; --thead-rule:1px solid #1b2c44; color-scheme:dark; }
body { background:radial-gradient(900px 420px at 85% -60px, rgba(56,189,248,.20), transparent 70%), radial-gradient(700px 360px at 0% 0%, rgba(99,102,241,.16), transparent 70%), var(--bg); background-repeat:no-repeat; }
.row { background:var(--surface); border:1px solid var(--line); border-radius:16px; margin-top:10px; }
.row:hover { border-color:rgba(56,189,248,.5); }
.rmap .c.tw { filter:drop-shadow(0 0 1.2px #38bdf8); }
.facts .big { color:#fff; }
""",
    "five": """
:root { --sil:#ffffff; --sil-line:#0f1b2d; --bg:#f3f5f9; --surface:#ffffff; --fg:#0f1b2d; --muted:#5b6778; --line:#e2e7ee; --chip:#eef1f6; --r:14px;
  --accent:#1668e3; --num:#0f1b2d; --hero-bg:#0f1b2d; --hero-fg:#ffffff; --hero-muted:#b6c2d4; --eyebrow:#fbbf24;
  --row-hover:#f7f9fc; --ic-fg:#ffffff; --up:#15803d; --down:#dc2626;
  --sea:#dde7f3; --land:#ffffff; --border:#a9b8cc; --maplab:#4b5a6e; --tw:#e0336f; --halo:rgba(224,51,111,.16);
  --foot-bg:#0f1b2d; --foot-fg:#ffffff; --foot-muted:#b6c2d4; }
.row { --ic-bg:var(--tc); --spark:var(--tc); --spark-fill:color-mix(in srgb, var(--tc) 14%, transparent); }
.hero { background:linear-gradient(90deg, #1668e3 0 20%, #f29d0b 20% 40%, #e0336f 40% 60%, #7546e8 60% 80%, #0e9f8e 80%) bottom / 100% 6px no-repeat, #0f1b2d; }
.topics, .ctx { background:var(--surface); border-radius:18px; padding:22px; box-shadow:0 1px 2px rgba(15,27,45,.05), 0 8px 24px rgba(15,27,45,.06); }
.row { border-left:4px solid transparent; }
.row:hover { border-left-color:var(--tc); background:color-mix(in srgb, var(--tc) 6%, #fff); }
.row .num { color:var(--tc-num, var(--tc)); }
.t-reservoir { --tc:#1668e3; } .t-power { --tc:#f29d0b; --tc-num:#c47a00; } .t-births { --tc:#e0336f; }
.t-flights { --tc:#7546e8; } .t-travel { --tc:#0e9f8e; --tc-num:#0b8577; }
.row .go { color:var(--tc); }
@media (max-width:760px) { .topics { padding:16px 14px; } .ctx { padding:12px 14px; } }
""",
    "paper": """
:root { --sil:#e3412b; --sil-line:#f4eee2; --bg:#f4eee2; --surface:#f4eee2; --fg:#141414; --muted:#5d574e; --line:#cfc4b0; --chip:#e9e0cf; --r:0px;
  --accent:#e3412b; --num:#141414; --hero-bg:transparent; --hero-fg:#141414; --hero-muted:#4a453e; --eyebrow:#e3412b;
  --row-hover:#ece3d1; --ic-bg:transparent; --ic-fg:#141414; --ic-r:0; --up:#1d7a3e; --down:#e3412b; --ix:#e3412b;
  --sea:#f4eee2; --land:#e2d7c3; --border:#9b8f7a; --maplab:#4a453e; --tw:#e3412b; --halo:rgba(227,65,43,.14); --map-edge:#141414;
  --spark:#141414; --spark-fill:transparent; --foot-bg:#141414; --foot-fg:#f4eee2; --foot-muted:#c9bfae; --thead-rule:3px solid #141414; }
.hero .w { border-bottom:3px solid #141414; padding-bottom:26px; }
.hero h1 { font-size:clamp(40px, 8vw, 80px); font-weight:900; letter-spacing:0; }
.hero { padding-bottom:0; }
.row { border-bottom:1px solid #141414; }
.ix { font-size:16px; }
.num { font-size:40px; font-weight:900; }
.spark circle { fill:#e3412b; }
h2 { font-weight:900; }
.topics h2, .ctx h2 { border-top:3px solid #141414; padding-top:10px; }
@media (max-width:760px) { .ctx { background:transparent; border:0; border-top:3px solid #141414; border-radius:0; padding:10px 0 0; } .ctx h2 { border:0; padding:0; } }
""",
    "cobalt": """
:root { --sil:#ffffff; --sil-line:#0038ff; --bg:#ffffff; --surface:#ffffff; --fg:#0a0a0a; --muted:#5a5f6b; --line:#e3e5ea; --chip:#f1f3f7; --r:0px;
  --accent:#0038ff; --num:#0a0a0a; --hero-bg:#0038ff; --hero-fg:#ffffff; --hero-muted:rgba(255,255,255,.82); --eyebrow:rgba(255,255,255,.78);
  --row-hover:#f3f6ff; --ic-bg:#0038ff; --ic-fg:#ffffff; --ic-r:0; --up:#0a8a4a; --down:#e5243b; --ix:#0038ff;
  --sea:#eef2ff; --land:#ffffff; --border:#8fa3ff; --maplab:#2b3350; --tw:#0038ff; --halo:rgba(0,56,255,.14);
  --spark:#0038ff; --spark-fill:rgba(0,56,255,.08); --foot-bg:#0a0a0a; --foot-fg:#ffffff; --foot-muted:#b4b8c2; }
.hero { padding:56px 0 46px; }
.hero h1 { font-size:clamp(42px, 9vw, 96px); letter-spacing:-.01em; }
.ix { font-size:22px; font-weight:700; }
.num { font-size:40px; }
.row { border-bottom:1px solid #0a0a0a; }
.thead { border-bottom:2px solid #0a0a0a; }
@media (max-width:760px) { .ctx { border:2px solid #0a0a0a; } }
""",
    "forest": """
:root { --sil:#6ee7a8; --sil-line:#0d3b2c; --sil-glow:drop-shadow(0 0 18px rgba(110,231,168,.35)); --bg:#f1f5f1; --surface:#ffffff; --fg:#10231b; --muted:#56675f; --line:#dbe5de; --chip:#e9f1ec; --r:16px;
  --accent:#1f9d55; --num:#0d3b2c; --hero-bg:#0d3b2c; --hero-fg:#f0fff6; --hero-muted:#a9d5bd; --eyebrow:#6ee7a8;
  --row-hover:#f3faf5; --ic-bg:#e1f3e8; --ic-fg:#1f9d55; --up:#1f9d55; --down:#d64545;
  --sea:#d8eadf; --land:#ffffff; --border:#93b7a2; --maplab:#3c5548; --tw:#1f9d55; --halo:rgba(31,157,85,.2);
  --spark:#1f9d55; --spark-fill:rgba(31,157,85,.12); --foot-bg:#0d3b2c; --foot-fg:#f0fff6; --foot-muted:#a9d5bd; --thead-rule:2px solid #0d3b2c; }
.hero { background:radial-gradient(700px 300px at 92% 120%, rgba(110,231,168,.28), transparent 70%), #0d3b2c; }
.row { background:var(--surface); border:1px solid var(--line); border-radius:16px; margin-top:10px; }
.row:hover { border-color:#1f9d55; }
.mapbox { box-shadow:0 1px 2px rgba(13,59,44,.06); }
""",
}
