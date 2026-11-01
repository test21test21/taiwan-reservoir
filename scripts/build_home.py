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
        eyebrow="TAIWAN AT A GLANCE", h1="一眼看懂台灣", lead="水、電、人口、航班、旅客：台灣最新的官方數字，每個主題都能點進去看細節。",
        updated="資料更新", meta_src="資料來源：政府開放資料", meta_freq="每小時自動更新", ctx="位置與基本資料", tbl="探索台灣數據", tbl_sub="五個主題的最新數字，點進去看細節。",
        cols=("主題", "最新數字", "趨勢", "資料時間"),
        f_loc=("位置", "東亞・西太平洋"), f_tz=("時區", "UTC+8"), f_pop="人口", f_div=("行政區", "22 個縣市"),
        pop_fmt=lambda p: f"{p / 1e4:,.1f}<small> 萬人</small>", pop_when=lambda m: f"{m[:4]} 年 {int(m[5:])} 月底・內政部戶政司",
        pop_chg=lambda c: f"比一年前{'少' if c < 0 else '多'} {abs(c) / 1e4:.1f} 萬人",
        map_label="台灣在東亞的位置", inset="台灣本島", names={"156": "中國", "392": "日本", "410": "韓國", "608": "菲律賓", "158": "台灣", "sea": "太平洋"},
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


def line_chart(vals, w=140, h=44):
    """連續資料（近 30 天、今天）：細線＋極淡底色，最後一點加圓點。"""
    if len(vals) < 2:
        return ""
    lo, hi = min(vals), max(vals)
    span = (hi - lo) or 1
    pts = [(3 + i * (w - 9) / (len(vals) - 1), 5 + (h - 12) * (1 - (v - lo) / span)) for i, v in enumerate(vals)]
    d = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    x, y = pts[-1]
    return (f'<svg class="chart" viewBox="0 0 {w} {h}" preserveAspectRatio="none" aria-hidden="true"><path class="base" d="M0 {h - .5}H{w}"/>'
            f'<polygon class="area" points="3,{h - 1} {d} {x:.1f},{h - 1}"/><polyline class="ln" points="{d}"/>'
            f'<circle class="pt" cx="{x:.1f}" cy="{y:.1f}" r="3.2"/></svg>')


def bar_chart(vals, w=140, h=44):
    """每月、每年的資料：細長條，最新一根用主色。"""
    if not vals:
        return ""
    hi = max(vals) or 1
    n = len(vals)
    gap = 2 if n > 16 else 3
    bw = (w - gap * (n - 1)) / n
    out = []
    for i, v in enumerate(vals):
        bh = max(1.5, (h - 4) * v / hi)
        out.append(f'<rect class="{"last" if i == n - 1 else "b"}" x="{i * (bw + gap):.1f}" y="{h - bh:.1f}" width="{bw:.1f}" height="{bh:.1f}" rx="1"/>')
    return f'<svg class="chart" viewBox="0 0 {w} {h}" preserveAspectRatio="none" aria-hidden="true">{"".join(out)}</svg>'


def region_map(t):
    """東亞地圖：world-map.json 的國界、經緯線，台灣塗主色，右下角放台灣本島放大圖。"""
    import math
    w = worldmap.world()
    W0, N0, E0, S0 = 104, 42, 144, 6
    x0, y0 = worldmap.xy(N0, W0)
    x1, y1 = worldmap.xy(S0, E0)
    vw, vh = x1 - x0, y1 - y0
    keep = {"156", "392", "410", "408", "608", "158", "704", "418", "116", "764", "104", "496", "360", "458", "096", "626", "344", "446"}
    land = "".join(f'<path class="c" d="{w["countries"][k]}"/>' for k in sorted(keep) if k in w["countries"] and k != "158")
    grat = []
    for lon in (110, 120, 130, 140):
        x, _ = worldmap.xy(0, lon)
        grat.append(f'<path class="g" d="M{x} {y0}V{y1}"/><text class="gl" x="{x + .8}" y="{y1 - 1.2}">{lon}°E</text>')
    for lat in (10, 20, 30, 40):
        _, y = worldmap.xy(lat, 0)
        grat.append(f'<path class="g" d="M{x0} {y}H{x1}"/><text class="gl" x="{x0 + .8}" y="{y - .8}">{lat}°N</text>')
    n = t["names"]

    def lab(key, lat, lon, cls="cn"):
        x, y = worldmap.xy(lat, lon)
        return f'<text class="{cls}" x="{x}" y="{y}">{e(n[key])}</text>'
    tx, ty = worldmap.xy(23.7, 120.95)
    # 台灣本島放大圖（reservoir/taiwan-map.json），放在右下角海上
    m = json.loads((ROOT / "reservoir/taiwan-map.json").read_text(encoding="utf-8"))
    ih = 36
    k = ih / m["height"]
    iw = m["width"] * k
    ix, iy = x1 - iw - 9, y1 - ih - 9
    inset = (f'<rect class="ib" x="{ix - 3:.1f}" y="{iy - 3:.1f}" width="{iw + 6:.1f}" height="{ih + 9:.1f}"/>'
             f'<g transform="translate({ix:.1f} {iy:.1f}) scale({k:.5f})">'
             + "".join(f'<path class="tw-c" d="{d}"/>' for d in m["counties"].values())
             + f'</g><text class="il" x="{ix + iw / 2:.1f}" y="{iy + ih + 4.6:.1f}">{e(t["inset"])}</text>'
             f'<path class="lk" d="M{tx + 2.4:.1f} {ty + 2.6:.1f}L{ix - 3:.1f} {iy - 3:.1f}"/>'
             f'<rect class="box" x="{tx - 2.2:.1f}" y="{ty - 3:.1f}" width="4.6" height="5.8"/>')
    per_km = 0.9 * w["s"] / (111.32 * math.cos(math.radians(23.5)))
    sx, sy = worldmap.xy(8.2, 105.2)
    bar = (f'<g class="scale"><path d="M{sx} {sy}h{1000 * per_km:.1f}M{sx} {sy - 1}v2M{sx + 500 * per_km:.1f} {sy - 1}v2M{sx + 1000 * per_km:.1f} {sy - 1}v2"/>'
           f'<text x="{sx}" y="{sy - 1.8}">0</text><text x="{sx + 500 * per_km:.1f}" y="{sy - 1.8}">500</text>'
           f'<text x="{sx + 1000 * per_km:.1f}" y="{sy - 1.8}">1,000 {e(t["km"])}</text></g>')
    return (f'<svg class="rmap" viewBox="{x0} {y0} {vw:.1f} {vh:.1f}" role="img" aria-label="{e(t["map_label"])}">'
            f'<rect class="sea" x="{x0}" y="{y0}" width="{vw:.1f}" height="{vh:.1f}"/>'
            + "".join(grat) + f'<g>{land}</g><path class="tw" d="{w["countries"]["158"]}"/>'
            + lab("156", 32, 109.5) + lab("392", 34.6, 136.6, "cn") + lab("410", 37.6, 126.2, "cn s") + lab("608", 12.2, 121.2)
            + lab("sea", 26, 131.5, "sea-t") + f'<text class="twl" x="{tx + 3.2}" y="{ty - 3.4}">{e(n["158"])}</text>'
            + inset + bar + "</svg>")


def page(lang="zh", theme="calm"):
    t = T[lang]
    d = data()
    r, p, b, f, v = d["reservoir"], d["power"], d["births"], d["flights"], d["travel"]
    dt = lambda iso: t["when_dt"](datetime.fromisoformat(iso))

    def chip(val, label, unit="%", digits=1):
        if val is None:
            return ""
        cls, arrow = ("up", "▲") if val > 0.05 else ("down", "▼") if val < -0.05 else ("flat", "▶")
        return f'<span class="chg"><b class="chip {cls}">{arrow} {abs(val):.{digits}f}{unit}</b>{e(label)}</span>'
    pt = " " + t["unit_pt"] if lang == "zh" else " pt"
    lights = dict(green="綠燈", yellow="黃燈", orange="橘燈")
    items = [
        ("reservoir", f"{r['pct']:.1f}<small>%</small>",
         chip(r["pct"] - r["last_year"] if r["last_year"] is not None else None, t["vs_ly"], pt), line_chart(r["spark"]), dt(r["when"])),
        ("power", f"{p['now']:,.0f}<small>{t['unit_power']}</small>",
         f'<span class="chg"><b class="chip ok"><i class="lamp {p["light"]}"></i>{lights[p["light"]]}</b>備轉容量率 {p["rate"]:.1f}%</span>',
         line_chart(p["spark"]), dt(p["when"])),
        ("births", f"{b['births']:,}<small>{t['unit_people']}</small>", chip(b["yoy"], t["vs_ly_m"]), bar_chart(b["spark"]), t["when_m"](b["month"])),
        ("flights", f"{f['lf']:.1f}<small>%</small>", chip(f["lf"] - f["prev"] if f["prev"] is not None else None, t["vs_lm"], pt),
         bar_chart(f["spark"]), t["when_m"](f["month"])),
        ("travel", f"{v['inbound'] / 1e4:,.0f}<small>{t['unit_wan']}</small>", chip(v["yoy"], t["vs_py"]), bar_chart(v["spark"]), t["when_y"](v["year"])),
    ]
    trs = []
    for k, num, change, chart, when in items:
        name, sub, label, cap = t["rows"][k]
        trs.append(
            f'<a class="row" href="{URL[k]}"><span class="ic"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="{ICONS[k]}"/></svg></span>'
            f'<span class="nm"><b>{e(name)}</b><span>{e(sub)}</span></span>'
            f'<span class="fig"><span class="num">{num}</span><span class="lbl">{e(label)}</span>{change}</span>'
            f'<span class="viz">{chart}<span class="cap">{e(cap)}</span></span>'
            f'<span class="when">{e(when)}</span><span class="go" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M5 12h13M13 6l6 6-6 6"/></svg></span></a>')
    pop = d["population"]
    facts = (
        f'<dl class="facts"><div><dt>{e(t["f_pop"])}</dt><dd><span class="big">{t["pop_fmt"](pop["pop"])}</span>'
        f'<span class="note">{e(t["pop_when"](pop["month"]))}</span>'
        + (f'<span class="note">{e(t["pop_chg"](pop["year_change"]))}</span>' if pop["year_change"] is not None else "")
        + f'</dd></div><div><dt>{e(t["f_loc"][0])}</dt><dd>{e(t["f_loc"][1])}</dd></div>'
        f'<div><dt>{e(t["f_tz"][0])}</dt><dd>{e(t["f_tz"][1])}</dd></div>'
        f'<div><dt>{e(t["f_div"][0])}</dt><dd>{e(t["f_div"][1])}</dd></div></dl>')
    upd = dt(d["generated_at"]) if d.get("generated_at") else ""
    return f"""<body class="th-{theme}">
<!--SITE_NAV-->
<header class="hero"><div class="w">
  <p class="eyebrow">{e(t["eyebrow"])}</p>
  <h1>{e(t["h1"])}</h1>
  <p class="lead">{e(t["lead"])}</p>
  <p class="meta"><span><i class="dot"></i>{e(t["meta_freq"])}</span><span>{e(t["updated"])} {e(upd)}</span><span>{e(t["meta_src"])}</span></p>
</div></header>
<main class="w grid">
  <details class="ctx" open>
    <summary><h2>{e(t["ctx"])}</h2><span class="plus" aria-hidden="true"></span></summary>
    <div class="ctx-in"><div class="mapbox">{region_map(t)}</div>{facts}</div>
  </details>
  <section class="topics">
    <div class="th"><h2>{e(t["tbl"])}</h2><p class="sub">{e(t["tbl_sub"])}</p></div>
    <div class="thead"><span>{e(t["cols"][0])}</span><span>{e(t["cols"][1])}</span><span>{e(t["cols"][2])}</span><span>{e(t["cols"][3])}</span><span></span></div>
    <div class="rows">{"".join(trs)}</div>
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
:root { --f-body:"Noto Sans TC","PingFang TC","Microsoft JhengHei",system-ui,sans-serif; --f-head:var(--f-body); --f-num:var(--f-body); --r-card:14px; }
* { box-sizing:border-box; }
.hero h1, h2, .nm b, .foot b { font-family:var(--f-head); }
.num, .facts .big { font-family:var(--f-num); }
body { margin:0; background:var(--bg); color:var(--text); font-family:var(--f-body);
  font-size:15px; line-height:1.6; font-variant-numeric:tabular-nums; -webkit-font-smoothing:antialiased; }
a { color:inherit; }
.w { max-width:1320px; margin:0 auto; padding-inline:max(18px, env(safe-area-inset-left)) max(18px, env(safe-area-inset-right)); }
@media (min-width:761px) { .w { padding-inline:40px; } }
.hero { padding:56px 0 6px; }
.eyebrow { margin:0 0 14px; font-size:12px; font-weight:700; letter-spacing:.22em; color:var(--accent); }
.hero h1 { margin:0; font-size:clamp(34px, 5.2vw, 54px); line-height:1.12; font-weight:700; letter-spacing:.03em; color:var(--ink); }
.hero .lead { margin:16px 0 0; font-size:clamp(15px, 1.6vw, 18px); line-height:1.7; color:var(--muted); max-width:40em; }
.meta { display:flex; flex-wrap:wrap; gap:6px 22px; margin:18px 0 0; font-size:13px; color:var(--muted); }
.meta .dot { display:inline-block; width:7px; height:7px; border-radius:50%; background:var(--accent); margin-right:7px; vertical-align:1px; }
.grid { display:grid; gap:32px; padding-top:44px; padding-bottom:64px; }
@media (min-width:1100px) { .grid { grid-template-columns:320px minmax(0, 1fr); gap:0; } .ctx { padding-right:44px; } .topics { padding-left:44px; } }
h2 { font-size:20px; margin:0; line-height:1.35; color:var(--ink); font-weight:700; letter-spacing:.02em; }
.ctx summary { list-style:none; display:flex; align-items:center; justify-content:space-between; gap:12px; }
.ctx summary::-webkit-details-marker { display:none; }
.plus { width:20px; height:20px; position:relative; flex:none; color:var(--muted); }
.plus::before, .plus::after { content:""; position:absolute; left:3px; right:3px; top:9px; height:1.5px; background:currentColor; }
.plus::after { transform:rotate(90deg); transition:transform .2s; }
.ctx[open] .plus::after { transform:rotate(0); }
@media (max-width:760px) {
  .ctx { border:1px solid var(--line-strong); border-radius:var(--r-sm); padding:13px 16px; background:var(--surface); }
  .ctx summary { cursor:pointer; } .ctx h2 { font-size:16px; } }
@media (min-width:761px) { .plus { display:none; } .ctx summary { pointer-events:none; } }
@media (min-width:761px) and (max-width:1099px) { .ctx-in { display:grid; grid-template-columns:1fr 1fr; gap:0 32px; align-items:start; } }
.mapbox { margin-top:16px; border:1px solid var(--line); border-radius:var(--r-sm); overflow:hidden; background:var(--sea); }
.rmap { display:block; width:100%; height:auto; }
.rmap .sea { fill:var(--sea); }
.rmap .g { stroke:var(--grat); stroke-width:.25; stroke-dasharray:.8 .8; }
.rmap .gl { font-size:2.9px; fill:var(--maplab); opacity:.8; letter-spacing:.1px; }
.rmap .c { fill:var(--land); stroke:var(--land-line); stroke-width:.3; stroke-linejoin:round; }
.rmap .tw { fill:var(--tw); }
.rmap .cn { font-size:4.3px; fill:var(--maplab); letter-spacing:.6px; }
.rmap .cn.s { font-size:3.7px; }
.rmap .sea-t { font-size:3.8px; fill:var(--maplab); letter-spacing:1.2px; font-style:italic; opacity:.85; }
.rmap .twl { font-size:4.9px; font-weight:700; fill:var(--tw); letter-spacing:.6px; }
.rmap .ib { fill:var(--surface); stroke:var(--line-strong); stroke-width:.25; }
.rmap .tw-c { fill:var(--tw); stroke:var(--surface); stroke-width:.8; vector-effect:non-scaling-stroke; }
.rmap .il { font-size:3.1px; fill:var(--maplab); text-anchor:middle; letter-spacing:.3px; }
.rmap .lk { stroke:var(--line-strong); stroke-width:.25; fill:none; }
.rmap .box { fill:none; stroke:var(--tw); stroke-width:.3; }
.rmap .scale path { stroke:var(--maplab); stroke-width:.3; fill:none; }
.rmap .scale text { font-size:2.9px; fill:var(--maplab); }
.facts { margin:8px 0 0; }
.facts div { display:grid; grid-template-columns:76px minmax(0, 1fr); gap:14px; padding:14px 0; border-bottom:1px solid var(--line); }
.facts div:last-child { border-bottom:0; }
.facts dt { font-size:14px; color:var(--muted); }
.facts dd { margin:0; color:var(--ink); }
.facts .big { display:block; font-size:26px; font-weight:700; line-height:1.2; color:var(--ink); }
.facts .big small { font-size:14px; font-weight:500; color:var(--muted); margin-left:3px; }
.facts .note { display:block; font-size:12.5px; color:var(--muted); line-height:1.6; margin-top:2px; }
.th .sub { margin:4px 0 0; font-size:14px; color:var(--muted); }
.thead, .row { display:grid; grid-template-columns:44px minmax(0, 1fr) minmax(0, 1.1fr) 128px 96px 32px; gap:20px; align-items:center; }
.thead { margin-top:22px; padding:0 20px 10px; font-size:12px; letter-spacing:.08em; color:var(--muted); border-bottom:1px solid var(--line-strong); }
.thead span:first-child { grid-column:span 2; }
.row { padding:22px 20px; border-bottom:1px solid var(--line); text-decoration:none; transition:background .15s, border-color .15s; }
.row:hover { background:var(--hover); }
.row:focus-visible { outline:2px solid var(--accent); outline-offset:-2px; }
.ic { width:44px; height:44px; border-radius:50%; display:grid; place-items:center; background:var(--ic-bg); }
.ic svg { width:22px; height:22px; fill:var(--ic-fg); }
.nm b { display:block; font-size:17px; line-height:1.35; color:var(--ink); letter-spacing:.02em; }
.nm span { display:block; font-size:13.5px; color:var(--muted); line-height:1.5; margin-top:3px; }
.num { display:block; font-size:34px; font-weight:700; line-height:1.05; color:var(--ink); white-space:nowrap; letter-spacing:-.005em; }
.num small { font-size:14px; font-weight:500; margin-left:4px; color:var(--muted); letter-spacing:0; }
.lbl { display:block; font-size:13.5px; color:var(--text); margin-top:6px; }
.chg { display:flex; flex-wrap:wrap; align-items:center; gap:4px 8px; margin-top:8px; font-size:12.5px; color:var(--muted); }
.chip { display:inline-flex; align-items:center; padding:2px 8px; border-radius:999px; font-size:12px; font-weight:700; line-height:1.6; white-space:nowrap; }
.chip.up { background:var(--up-bg); color:var(--up); } .chip.down { background:var(--down-bg); color:var(--down); }
.chip.flat, .chip.ok { background:var(--chip); color:var(--ink); }
.lamp { display:inline-block; width:7px; height:7px; border-radius:50%; margin-right:6px; }
.lamp.green { background:#2f8a4f; } .lamp.yellow { background:#d9a300; } .lamp.orange { background:#e07b1f; }
.viz .chart { display:block; width:100%; height:44px; overflow:visible; }
.viz .cap { display:block; font-size:11.5px; color:var(--muted); margin-top:6px; letter-spacing:.04em; }
.chart .base { stroke:var(--line-strong); stroke-width:1; vector-effect:non-scaling-stroke; }
.chart .area { fill:var(--area); }
.chart .ln { fill:none; stroke:var(--accent); stroke-width:1.75; stroke-linejoin:round; stroke-linecap:round; vector-effect:non-scaling-stroke; }
.chart .pt { fill:var(--accent); stroke:var(--surface); stroke-width:2; }
.chart .b { fill:var(--bar); } .chart .last { fill:var(--accent); }
.when { font-size:13.5px; color:var(--text); }
.go { width:32px; height:32px; border-radius:50%; border:1px solid var(--line-strong); display:grid; place-items:center; transition:background .15s, border-color .15s; }
.go svg { width:16px; height:16px; fill:none; stroke:var(--accent); stroke-width:2; stroke-linecap:round; stroke-linejoin:round; }
.row:hover .go { background:var(--accent); border-color:var(--accent); }
.row:hover .go svg { stroke:var(--on-accent); }
@media (max-width:1099px) {
  .thead { display:none; } .rows { margin-top:16px; border-top:1px solid var(--line-strong); }
  .row { grid-template-columns:44px minmax(0, 1fr) minmax(0, 1fr) 124px 32px; grid-template-areas:"ic nm fig viz go" "ic nm when viz go"; gap:4px 20px; }
  .ic { grid-area:ic; } .nm { grid-area:nm; } .fig { grid-area:fig; } .viz { grid-area:viz; } .when { grid-area:when; font-size:12.5px; color:var(--muted); } .go { grid-area:go; } }
@media (max-width:760px) {
  .row { grid-template-columns:40px minmax(0, 1fr) 112px; grid-template-areas:"ic nm go" ". fig viz" ". when when"; gap:0 14px; padding:20px 4px; align-items:start; }
  .ic { width:40px; height:40px; } .ic svg { width:20px; height:20px; }
  .nm b { font-size:16px; } .nm span { font-size:13px; }
  .fig { margin-top:12px; } .num { font-size:32px; }
  .viz { align-self:end; padding-bottom:2px; } .viz .chart { height:35px; } .viz .cap { text-align:right; font-size:11px; margin-top:4px; }
  .when { margin-top:8px; font-size:12.5px; color:var(--muted); }
  .go { justify-self:end; width:30px; height:30px; } }
.foot { background:var(--foot-bg); border-top:1px solid var(--line); padding:30px 0 44px; }
.foot .cols { display:grid; gap:20px; }
@media (min-width:761px) { .foot .cols { grid-template-columns:repeat(3, minmax(0, 1fr)); gap:40px; } }
.foot b { font-size:13px; color:var(--ink); letter-spacing:.04em; }
.foot p { margin:6px 0 0; font-size:13px; color:var(--muted); line-height:1.75; }
.foot a { color:var(--accent); text-decoration:none; }
"""

# 三種取向（同一個版面）：沉穩、現代、科技深色。都不發光、不用螢光色。Shane 挑一種後其他刪掉
THEMES = {
    "calm": """
:root { --bg:#ffffff; --surface:#ffffff; --fg:#0f2a4a; --ink:#0f2a4a; --text:#2b3b4e; --muted:#627187; --line:#e4e9ef; --line-strong:#cbd4df;
  --chip:#eef2f7; --accent:#1d4f91; --on-accent:#ffffff; --hover:#f6f8fb; --ic-bg:#eef3f9; --ic-fg:#1d4f91; --bar:#cdd8e6;
  --area:rgba(29,79,145,.07); --up:#22703f; --up-bg:#e7f3ec; --down:#a5342c; --down-bg:#fbeceb;
  --sea:#f4f7fa; --land:#e1e7ee; --land-line:#ffffff; --grat:#d3dbe5; --maplab:#6b7a8c; --tw:#0f2a4a; --foot-bg:#f6f8fb; --r-sm:6px; }
@media (min-width:1100px) { .ctx { border-right:1px solid var(--line); } }
""",
    "modern": """
:root { --bg:#f3f5f9; --surface:#ffffff; --fg:#0f172a; --ink:#0f172a; --text:#334155; --muted:#64748b; --line:#e6eaf0; --line-strong:#d6dce5;
  --chip:#f1f5f9; --accent:#2563eb; --on-accent:#ffffff; --hover:#ffffff; --ic-bg:#eef4ff; --ic-fg:#2563eb; --bar:#d7e2f7;
  --area:rgba(37,99,235,.07); --up:#15803d; --up-bg:#e8f5ed; --down:#b42318; --down-bg:#fdeceb;
  --sea:#eef3fa; --land:#ffffff; --land-line:#d5deea; --grat:#d9e2ee; --maplab:#64748b; --tw:#2563eb; --foot-bg:#ffffff; --r-sm:10px; }
.grid { gap:24px; }
.ctx, .topics { background:var(--surface); border:1px solid var(--line); border-radius:18px; padding:24px !important; box-shadow:0 1px 2px rgba(15,23,42,.04); align-self:start; }
.thead { display:none; }
.rows { margin-top:16px; display:grid; gap:10px; border:0 !important; }
.row { border:1px solid var(--line); border-radius:14px; background:#fbfcfe; }
.row:hover { background:#fff; border-color:#bcd0f7; box-shadow:0 4px 14px rgba(37,99,235,.08); }
@media (max-width:760px) { .topics { background:none; border:0; box-shadow:none; padding:0 !important; } .ctx { padding:14px 16px !important; border-radius:14px; } .row { padding:18px 14px; background:#fff; } }
""",
    "tech": """
:root { --bg:#0c0f14; --surface:#12161d; --fg:#eef2f7; --ink:#eef2f7; --text:#c3ccd7; --muted:#8391a3; --line:#1e2530; --line-strong:#2b3441;
  --chip:#1a212b; --accent:#7fb0ff; --on-accent:#0c0f14; --hover:#121821; --ic-bg:#16202d; --ic-fg:#a9c8ff; --bar:#283342;
  --area:rgba(127,176,255,.08); --up:#7ad49c; --up-bg:rgba(122,212,156,.10); --down:#f0a3a0; --down-bg:rgba(240,163,160,.10);
  --sea:#0f131a; --land:#1b222c; --land-line:#0f131a; --grat:#1d2530; --maplab:#7b889a; --tw:#eef2f7; --foot-bg:#0a0d11; --r-sm:6px; color-scheme:dark; }
@media (min-width:1100px) { .ctx { border-right:1px solid var(--line); } }
""",
}


# ---- 第二輪：八種字型搭配（Shane 2026-11-01「再給我八種，字體是只有一種選項嗎」）
FONTS = {  # Google Fonts 的 css2 參數
    "calm": "Noto+Sans+TC:wght@400;500;700", "modern": "Noto+Sans+TC:wght@400;500;700", "tech": "Noto+Sans+TC:wght@400;500;700",
    "clean": "Inter:wght@400;500;600;700&family=Noto+Sans+TC:wght@400;500;700",
    "report": "Noto+Serif+TC:wght@500;700&family=Noto+Sans+TC:wght@400;500;700",
    "carbon": "IBM+Plex+Sans:wght@400;500;600&family=Noto+Sans+TC:wght@400;500;700",
    "humane": "LXGW+WenKai+TC:wght@400;700&family=DM+Sans:wght@400;500;700&family=Noto+Sans+TC:wght@400;500;700",
    "round": "Huninn&family=Manrope:wght@500;700;800&family=Noto+Sans+TC:wght@400;500;700",
    "terminal": "JetBrains+Mono:wght@400;500;700&family=Noto+Sans+TC:wght@400;500;700",
    "magazine": "Cactus+Classical+Serif&family=DM+Sans:wght@400;500;600&family=Noto+Sans+TC:wght@400;500;700",
    "oecd": "Source+Sans+3:wght@400;600;700&family=Noto+Sans+TC:wght@400;500;700",
}
SANS = '"Noto Sans TC","PingFang TC","Microsoft JhengHei",sans-serif'
CARDS = """
.grid { gap:24px; }
@media (min-width:1100px) { .topics { padding-left:0; } .ctx { padding-right:24px; } }
.ctx { background:var(--surface); border:1px solid var(--line); border-radius:var(--r-card); padding:24px !important; align-self:start; }
.thead { display:none; }
.rows { margin-top:18px; display:grid; gap:12px; border:0 !important; }
.row { border:1px solid var(--line); border-radius:var(--r-card); background:var(--surface); }
.row:hover { background:var(--surface); border-color:var(--line-strong); }
@media (max-width:760px) { .ctx { padding:14px 16px !important; } .row { padding:18px 14px; } }
"""
TILES = CARDS + """
@media (min-width:761px) {
  .rows { grid-template-columns:1fr 1fr; gap:14px; }
  .row { grid-template-columns:44px minmax(0, 1fr) 32px; grid-template-areas:"ic nm go" "fig fig fig" "viz viz viz" "when when when"; gap:0 14px; align-items:start; padding:22px 22px 18px; }
  .row:first-child { grid-column:1 / -1; grid-template-columns:44px minmax(0, 1fr) minmax(0, 1.25fr) 32px; grid-template-areas:"ic nm viz go" ". fig viz ." ". when viz ."; }
  .ic { grid-area:ic; } .nm { grid-area:nm; } .go { grid-area:go; }
  .fig { grid-area:fig; margin-top:18px; } .viz { grid-area:viz; margin-top:16px; } .viz .chart { height:56px; } .viz .pt { display:none; }
  .when { grid-area:when; margin-top:10px; font-size:12.5px; color:var(--muted); }
  .row:first-child .viz { margin-top:0; align-self:center; } .row:first-child .viz .chart { height:96px; } }
"""
THEMES.update({
    "clean": """
:root { --f-body:"Inter",""" + SANS + """; --f-num:"Inter",sans-serif;
  --bg:#f6f8fb; --surface:#ffffff; --fg:#0b1220; --ink:#0b1220; --text:#344054; --muted:#667085; --line:#e7ebf0; --line-strong:#cfd6e0;
  --chip:#f2f4f7; --accent:#1570ef; --on-accent:#fff; --hover:#fff; --ic-bg:#eff5ff; --ic-fg:#1570ef; --bar:#d1e0ff; --area:rgba(21,112,239,.08);
  --up:#067647; --up-bg:#ecfdf3; --down:#b42318; --down-bg:#fef3f2; --sea:#eef4fb; --land:#ffffff; --land-line:#cfd9e6; --grat:#dbe4ef;
  --maplab:#667085; --tw:#1570ef; --foot-bg:#ffffff; --r-sm:10px; --r-card:16px; }
.num { font-weight:600; letter-spacing:-.02em; } .hero h1 { letter-spacing:0; }
""" + TILES,
    "report": """
:root { --f-head:"Noto Serif TC",serif; --f-num:"Noto Serif TC",serif;
  --bg:#ffffff; --surface:#ffffff; --fg:#13294b; --ink:#13294b; --text:#2f3b4c; --muted:#5f6b7a; --line:#e5e7eb; --line-strong:#13294b;
  --chip:#f1f3f6; --accent:#13294b; --on-accent:#fff; --hover:#f7f8fa; --ic-bg:transparent; --ic-fg:#13294b; --bar:#c9d1dc; --area:rgba(19,41,75,.06);
  --up:#21633b; --up-bg:#e9f2ec; --down:#9b2c24; --down-bg:#f8ebe9; --sea:#f6f7f9; --land:#e3e7ec; --land-line:#ffffff; --grat:#d6dbe2;
  --maplab:#5f6b7a; --tw:#13294b; --foot-bg:#f6f7f9; --r-sm:0px; }
.hero .w { border-bottom:3px double var(--ink); padding-bottom:26px; } .hero { padding-bottom:0; }
.eyebrow { color:var(--muted); } .thead { border-bottom-width:2px; } .row { border-bottom-color:#d5dae1; }
.num { font-weight:700; font-size:36px; } .ic { width:36px; } .ic svg { width:28px; height:28px; }
@media (min-width:1100px) { .ctx { border-right:1px solid var(--line); } }
""",
    "carbon": """
:root { --f-body:"IBM Plex Sans",""" + SANS + """; --f-num:"IBM Plex Sans",sans-serif;
  --bg:#f4f4f4; --surface:#ffffff; --fg:#161616; --ink:#161616; --text:#393939; --muted:#6f6f6f; --line:#e0e0e0; --line-strong:#c6c6c6;
  --chip:#e8e8e8; --accent:#0f62fe; --on-accent:#fff; --hover:#e8e8e8; --ic-bg:#edf5ff; --ic-fg:#0f62fe; --bar:#c6c6c6; --area:rgba(15,98,254,.07);
  --up:#198038; --up-bg:#defbe6; --down:#da1e28; --down-bg:#fff1f1; --sea:#f4f4f4; --land:#e0e0e0; --land-line:#ffffff; --grat:#d1d1d1;
  --maplab:#6f6f6f; --tw:#0f62fe; --foot-bg:#ffffff; --r-sm:0px; --r-card:0px; }
.ctx, .topics { background:#fff; padding:24px !important; }
@media (min-width:1100px) { .grid { gap:16px; } .topics { padding-left:24px; } }
.thead { background:#e0e0e0; border:0; margin-top:20px; padding:12px 20px; color:#161616; font-weight:600; letter-spacing:0; }
.ic { border-radius:0; } .go { border-radius:0; } .chip { border-radius:2px; } .num { font-weight:500; font-size:36px; }
.row:hover .go { background:#0f62fe; }
@media (max-width:760px) { .topics { padding:16px !important; } .ctx { border:0; } }
""",
    "humane": """
:root { --f-head:"LXGW WenKai TC",serif; --f-num:"DM Sans",sans-serif;
  --bg:#faf8f3; --surface:#fffdf9; --fg:#2b2724; --ink:#2b2724; --text:#3f3a35; --muted:#7a7168; --line:#ebe5da; --line-strong:#d9d0c2;
  --chip:#f2ede4; --accent:#2f6f6a; --on-accent:#fff; --hover:#fff; --ic-bg:#e9f1ef; --ic-fg:#2f6f6a; --bar:#d3e1dd; --area:rgba(47,111,106,.08);
  --up:#2f6f45; --up-bg:#e9f2ea; --down:#a3412f; --down-bg:#f8ebe6; --sea:#f3efe6; --land:#fffdf9; --land-line:#dcd3c3; --grat:#e4ddcf;
  --maplab:#7a7168; --tw:#2f6f6a; --foot-bg:#f3efe6; --r-sm:10px; --r-card:16px; }
.hero h1 { font-weight:700; letter-spacing:.06em; } .nm b { font-size:19px; font-weight:700; } .num { font-weight:700; letter-spacing:-.01em; }
""" + CARDS,
    "round": """
:root { --f-head:"Huninn",sans-serif; --f-num:"Manrope",sans-serif;
  --bg:#f1f5fa; --surface:#ffffff; --fg:#1e2a3b; --ink:#1e2a3b; --text:#3c4a5c; --muted:#6b7a8d; --line:#e2e8f0; --line-strong:#cdd6e2;
  --chip:#eef2f7; --accent:#3a6ea5; --on-accent:#fff; --hover:#fff; --ic-bg:#e8f0fa; --ic-fg:#3a6ea5; --bar:#d3e0ef; --area:rgba(58,110,165,.09);
  --up:#2d7a52; --up-bg:#e7f4ec; --down:#b5453c; --down-bg:#fbecea; --sea:#e9f0f8; --land:#ffffff; --land-line:#cfdae8; --grat:#d8e2ee;
  --maplab:#6b7a8d; --tw:#3a6ea5; --foot-bg:#ffffff; --r-sm:16px; --r-card:22px; }
.hero h1 { font-weight:400; letter-spacing:.04em; } h2, .nm b { font-weight:400; } .nm b { font-size:19px; }
.num { font-weight:800; letter-spacing:-.02em; } .ic { border-radius:14px; }
""" + TILES,
    "terminal": """
:root { --f-num:"JetBrains Mono",monospace;
  --bg:#0d1117; --surface:#161b22; --fg:#e6edf3; --ink:#e6edf3; --text:#c9d1d9; --muted:#8b949e; --line:#21262d; --line-strong:#30363d;
  --chip:#21262d; --accent:#58a6ff; --on-accent:#0d1117; --hover:#161b22; --ic-bg:#161b22; --ic-fg:#79c0ff; --bar:#30363d; --area:rgba(88,166,255,.08);
  --up:#56d364; --up-bg:rgba(86,211,100,.12); --down:#ff7b72; --down-bg:rgba(255,123,114,.12); --sea:#0d1117; --land:#1c2128; --land-line:#0d1117; --grat:#21262d;
  --maplab:#8b949e; --tw:#e6edf3; --foot-bg:#010409; --r-sm:6px; color-scheme:dark; }
.eyebrow, .meta, .thead, .when, .viz .cap, .chip, .facts .note { font-family:"JetBrains Mono",""" + SANS + """; }
.eyebrow::before { content:"$ "; color:var(--muted); }
.num { font-weight:500; font-size:32px; letter-spacing:-.02em; } .ic { border:1px solid var(--line-strong); border-radius:8px; }
@media (min-width:1100px) { .ctx { border-right:1px solid var(--line); } }
""",
    "magazine": """
:root { --f-head:"Cactus Classical Serif",serif; --f-num:"DM Sans",sans-serif;
  --bg:#ffffff; --surface:#ffffff; --fg:#111111; --ink:#111111; --text:#333333; --muted:#6b6b6b; --line:#e8e8e8; --line-strong:#111111;
  --chip:#f2f2f2; --accent:#1f4e79; --on-accent:#fff; --hover:#fafafa; --ic-bg:transparent; --ic-fg:#111; --bar:#d9d9d9; --area:rgba(17,17,17,.05);
  --up:#2a6b3f; --up-bg:#edf4ef; --down:#a33a2c; --down-bg:#f8ecea; --sea:#f7f7f7; --land:#e6e6e6; --land-line:#ffffff; --grat:#dddddd;
  --maplab:#6b6b6b; --tw:#111111; --foot-bg:#f7f7f7; --r-sm:0px; }
.hero { padding-top:72px; } .hero h1 { font-size:clamp(40px, 7vw, 76px); font-weight:400; letter-spacing:.04em; }
.eyebrow { color:var(--ink); } h2 { font-weight:400; font-size:24px; } .nm b { font-weight:400; font-size:20px; }
.ic { display:none; } .thead, .row { grid-template-columns:minmax(0, 1fr) minmax(0, 1.15fr) 132px 96px 32px; } .thead span:first-child { grid-column:auto; }
.num { font-weight:500; font-size:40px; letter-spacing:-.02em; } .chart .ln, .chart .last, .chart .pt { stroke:#111; } .chart .last, .chart .pt { fill:#111; }
.go { border-color:#111; } .go svg { stroke:#111; } .row:hover .go { background:#111; border-color:#111; }
@media (max-width:1099px) { .row { grid-template-columns:minmax(0, 1fr) minmax(0, 1fr) 124px 32px; grid-template-areas:"nm fig viz go" "nm when viz go"; } }
@media (max-width:760px) { .row { grid-template-columns:minmax(0, 1fr) 112px; grid-template-areas:"nm go" "fig viz" "when when"; } }
@media (min-width:1100px) { .ctx { border-right:1px solid var(--line); } }
""",
    "oecd": """
:root { --f-body:"Source Sans 3",""" + SANS + """; --f-num:"Source Sans 3",sans-serif;
  --bg:#ffffff; --surface:#ffffff; --fg:#0b2f5b; --ink:#0b2f5b; --text:#283a52; --muted:#5c6f86; --line:#dfe6ee; --line-strong:#b9c6d6;
  --chip:#eef3f8; --accent:#0b5cad; --on-accent:#fff; --hover:#f4f7fb; --ic-bg:#0b2f5b; --ic-fg:#ffffff; --bar:#c3d3e6; --area:rgba(11,92,173,.08);
  --up:#1f6b3d; --up-bg:#e7f2eb; --down:#a6322b; --down-bg:#f9eceb; --sea:#e8eff6; --land:#ffffff; --land-line:#c3d1e0; --grat:#d3dde8;
  --maplab:#5c6f86; --tw:#0b2f5b; --foot-bg:#0b2f5b; --r-sm:2px; }
.hero { border-top:4px solid var(--ink); }
.ctx { background:#f1f5f9; padding:22px !important; align-self:start; }
@media (min-width:1100px) { .grid { gap:40px; } .topics { padding-left:0; } }
.num { font-weight:700; font-size:36px; } .ic { border-radius:4px; }
.foot b { color:#fff; } .foot p { color:#c7d4e3; } .foot a { color:#fff; }
@media (max-width:760px) { .ctx { border:0; } }
""",
})
