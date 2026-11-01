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
        desc="台灣最新的官方數字：主要水庫蓄水率、現在用電、每月出生人數、航班載客率、來台旅客人次。",
        eyebrow="TAIWAN AT A GLANCE", h1="一眼看懂台灣", lead="水庫、電力、人口、航班、旅客的最新官方數字。",
        updated="資料更新", meta_src="資料來源：政府開放資料", meta_freq="每小時自動更新", ctx="位置與基本資料", tbl="探索台灣數據",
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
        ng_t="非政府網站", ng="本站為個人經營，和任何政府機關沒有關係。", contact="歡迎來信：contact@taiwandata.info"),
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
            f'<path class="pt" d="M{x:.1f} {y:.1f}h0"/></svg>')


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


def page(lang="zh"):
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
            f'<a class="row card" href="{URL[k]}"><span class="ic"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="{ICONS[k]}"/></svg></span>'
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
    return f"""<body>
<!--SITE_NAV-->
<header class="hero"><div class="w">
  <p class="eyebrow">{e(t["eyebrow"])}</p>
  <h1>{e(t["h1"])}</h1>
  <p class="lead">{e(t["lead"])}</p>
  <p class="meta"><span><i class="dot"></i>{e(t["meta_freq"])}</span><span>{e(t["updated"])} {e(upd)}</span><span>{e(t["meta_src"])}</span></p>
</div></header>
<main class="w grid">
  <section class="ctx">
    <h2 class="sh"><button type="button" aria-expanded="true" aria-controls="ctx-in">{e(t["ctx"])}<span class="plus" aria-hidden="true"></span></button></h2>
    <div class="ctx-in card" id="ctx-in"><div class="mapbox">{region_map(t)}</div>{facts}</div>
  </section>
  <section class="topics">
    <h2 class="sh">{e(t["tbl"])}</h2>
    <div class="rows">{"".join(trs)}</div>
  </section>
</main>
<footer class="foot"><div class="w cols">
  <div><b>{e(t["src_t"])}</b><p>{e(t["src"])}</p></div>
  <div><b>{e(t["about_t"])}</b><p>{e(t["about"])} <a href="about/">{e(t["about_link"])} →</a></p></div>
  <div><b>{e(t["ng_t"])}</b><p>{e(t["ng"])}<br>{e(t["contact"])}</p></div>
</div></footer>
<script>(function(){{var c=document.querySelector(".ctx"),b=c&&c.querySelector("button");if(!b)return;
function set(o){{c.classList.toggle("shut",!o);b.setAttribute("aria-expanded",o?"true":"false");}}
if(window.matchMedia("(max-width: 760px)").matches)set(false);b.addEventListener("click",function(){{set(c.classList.contains("shut"));}});}})();</script>
</body>"""


CSS = """
:root { --f-body:"Noto Sans TC","PingFang TC","Microsoft JhengHei",system-ui,sans-serif; --f-head:"LXGW WenKai TC",var(--f-body); --f-num:"DM Sans",var(--f-body);
  --ink:#111111; --text:#333333; --muted:#6b6b6b; --line:#e3e3e3; --line-strong:#c8c8c8; --fill:#f2f2f2;
  --icon:#2b6a66; --up:#1e7a45; --down:#c0392b;
  --sea:#e9f0f5; --land:#ffffff; --land-line:#c5cfd7; --grat:#d3dde5; --maplab:#5f6b73; --tw:#2b6a66; }
/* 黑白灰：底全白、字黑灰。只有地圖、台灣小圖、主題圖示、增減百分比（和官方燈號）有顏色 */
* { box-sizing:border-box; }
.hero h1, h2, .nm b, .foot b { font-family:var(--f-head); }
.num, .facts .big { font-family:var(--f-num); }
body { margin:0; background:#ffffff; color:var(--text); font-family:var(--f-body);
  font-size:15px; line-height:1.6; font-variant-numeric:tabular-nums; -webkit-font-smoothing:antialiased; }
a { color:inherit; }
.w { max-width:1320px; margin:0 auto; padding-inline:max(18px, env(safe-area-inset-left)) max(18px, env(safe-area-inset-right)); }
@media (min-width:761px) { .w { padding-inline:40px; } }

/* 開頭 */
.hero { padding:56px 0 0; }
.eyebrow { margin:0 0 14px; font-size:12px; font-weight:700; letter-spacing:.22em; color:var(--muted); }
.hero h1 { margin:0; font-size:clamp(34px, 5.2vw, 54px); line-height:1.12; font-weight:700; letter-spacing:.06em; color:var(--ink); }
.hero .lead { margin:16px 0 0; font-size:clamp(15px, 1.6vw, 18px); line-height:1.7; color:var(--muted); }
.meta { display:flex; flex-wrap:wrap; gap:6px 22px; margin:18px 0 0; font-size:13px; color:var(--muted); }
.meta .dot { display:inline-block; width:7px; height:7px; border-radius:50%; background:var(--ink); margin-right:7px; vertical-align:1px; }

/* 兩欄：左「位置與基本資料」、右「探索台灣數據」。兩欄標題同一條線、卡片上緣同一條線、下緣同一條線 */
.grid { display:grid; gap:40px; padding-top:48px; padding-bottom:64px; }
@media (min-width:1100px) { .grid { grid-template-columns:360px minmax(0, 1fr); gap:0 24px; align-items:stretch; } }
.sh { margin:0 0 16px; font-size:20px; line-height:28px; color:var(--ink); font-weight:700; letter-spacing:.04em; }
.card { background:#ffffff; border:1px solid var(--line); border-radius:16px; }
.sh button { all:unset; display:flex; align-items:center; justify-content:space-between; gap:12px; width:100%; font:inherit; color:inherit; letter-spacing:inherit; }
.plus { width:20px; height:20px; position:relative; flex:none; color:var(--muted); }
.plus::before, .plus::after { content:""; position:absolute; left:3px; right:3px; top:9px; height:1.5px; background:currentColor; }
.plus::after { transform:rotate(0); transition:transform .2s; }
.ctx.shut .plus::after { transform:rotate(90deg); }
@media (min-width:761px) { .plus { display:none; } .sh button { pointer-events:none; } }

.ctx { display:flex; flex-direction:column; }
.ctx-in { flex:1; display:flex; flex-direction:column; padding:20px; }
.mapbox { border:1px solid var(--line); border-radius:10px; overflow:hidden; background:var(--sea); }
.facts { flex:1; display:flex; flex-direction:column; margin:8px 0 0; }
.facts div { flex:1 1 auto; display:grid; grid-template-columns:72px minmax(0, 1fr); gap:16px; align-content:center; align-items:baseline; padding:14px 0; border-bottom:1px solid var(--line); }
.facts div:last-child { border-bottom:0; padding-bottom:0; }
.facts dt { font-size:14px; color:var(--muted); }
.facts dd { margin:0; color:var(--ink); }
.facts .big { display:block; font-size:26px; font-weight:700; line-height:1.2; color:var(--ink); }
.facts .big small { font-size:14px; font-weight:500; color:var(--muted); margin-left:3px; }
.facts .note { display:block; font-size:12.5px; color:var(--muted); line-height:1.6; margin-top:2px; }
@media (min-width:761px) and (max-width:1099px) { .ctx-in { display:grid; grid-template-columns:minmax(0, 1fr) minmax(0, 1fr); gap:0 32px; align-items:stretch; } .facts { margin:0; } .facts div:first-child { padding-top:0; } }

/* 地圖 */
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
.rmap .ib { fill:#ffffff; stroke:var(--line-strong); stroke-width:.25; }
.rmap .tw-c { fill:var(--tw); stroke:#ffffff; stroke-width:.8; vector-effect:non-scaling-stroke; }
.rmap .il { font-size:3.1px; fill:var(--maplab); text-anchor:middle; letter-spacing:.3px; }
.rmap .lk { stroke:var(--line-strong); stroke-width:.25; fill:none; }
.rmap .box { fill:none; stroke:var(--tw); stroke-width:.3; }
.rmap .scale path { stroke:var(--maplab); stroke-width:.3; fill:none; }
.rmap .scale text { font-size:2.9px; fill:var(--maplab); }

/* 主題卡片：每張卡片裡，第一行（圖示、名稱、數字、資料時間、箭頭）同一條基線；第二行（說明、數字名稱）同一條基線；
   趨勢圖上緣對齊卡片內容上緣、說明文字下緣對齊最後一行 */
.rows { display:grid; gap:12px; }
.row { display:grid; text-decoration:none; padding:22px 24px; column-gap:24px; row-gap:6px; align-items:baseline;
  grid-template-columns:44px minmax(0, 1fr) minmax(0, 1fr) 140px 96px 32px;
  grid-template-rows:auto auto 1fr;
  grid-template-areas:"ic t n viz w go" ". s l viz . ." ". . c viz . ."; transition:border-color .15s; }
.row:hover { border-color:var(--ink); }
.row:focus-visible { outline:2px solid var(--ink); outline-offset:2px; }
.nm, .fig { display:contents; }
.ic { grid-area:ic; align-self:center; width:44px; height:44px; border-radius:50%; display:grid; place-items:center; background:var(--fill); }
.ic svg { width:22px; height:22px; fill:var(--icon); }
.nm b { grid-area:t; font-size:19px; font-weight:700; line-height:1.35; color:var(--ink); letter-spacing:.04em; }
.nm span { grid-area:s; font-size:13.5px; color:var(--muted); line-height:1.5; }
.num { grid-area:n; font-size:34px; font-weight:700; line-height:1.05; color:var(--ink); white-space:nowrap; letter-spacing:-.01em; }
.num small { font-size:14px; font-weight:500; margin-left:4px; color:var(--muted); letter-spacing:0; }
.lbl { grid-area:l; font-size:13.5px; color:var(--text); line-height:1.5; }
.chg { grid-area:c; display:flex; flex-wrap:wrap; align-items:baseline; gap:2px 8px; font-size:12.5px; line-height:1.6; color:var(--muted); }
.chip { font-size:12.5px; font-weight:700; white-space:nowrap; color:var(--ink); }
.chip.up { color:var(--up); } .chip.down { color:var(--down); }
.lamp { display:inline-block; width:7px; height:7px; border-radius:50%; margin-right:6px; vertical-align:1px; }
.lamp.green { background:#2f8a4f; } .lamp.yellow { background:#d9a300; } .lamp.orange { background:#e07b1f; }
.viz { grid-area:viz; align-self:stretch; display:flex; flex-direction:column; min-width:0; }
.viz .chart { display:block; width:100%; flex:1; min-height:40px; overflow:visible; }
.viz .cap { display:block; font-size:11.5px; line-height:16px; color:var(--muted); margin-top:6px; letter-spacing:.04em; }
.chart .base { stroke:var(--line-strong); stroke-width:1; vector-effect:non-scaling-stroke; }
.chart .area { fill:rgba(0,0,0,.05); }
.chart .ln { fill:none; stroke:var(--ink); stroke-width:1.75; stroke-linejoin:round; stroke-linecap:round; vector-effect:non-scaling-stroke; }
.chart .pt { fill:none; stroke:var(--ink); stroke-width:7; stroke-linecap:round; vector-effect:non-scaling-stroke; }
.chart .b { fill:#d0d0d0; } .chart .last { fill:var(--ink); }
.when { grid-area:w; font-size:13.5px; color:var(--text); white-space:nowrap; }
.go { grid-area:go; align-self:center; justify-self:end; width:32px; height:32px; border-radius:50%; border:1px solid var(--line-strong); display:grid; place-items:center; transition:background .15s, border-color .15s; }
.go svg { width:16px; height:16px; fill:none; stroke:var(--ink); stroke-width:2; stroke-linecap:round; stroke-linejoin:round; }
.row:hover .go { background:var(--ink); border-color:var(--ink); }
.row:hover .go svg { stroke:#ffffff; }
@media (max-width:1099px) {
  .row { grid-template-columns:44px minmax(0, 1fr) minmax(0, 1fr) 132px 32px;
    grid-template-areas:"ic t n viz go" ". s l viz ." ". w c viz ."; }
  .when { font-size:12.5px; color:var(--muted); } }
@media (max-width:760px) {
  .grid { gap:28px; padding-top:36px; }
  .ctx { border:1px solid var(--line); border-radius:16px; padding:0 16px; }
  .ctx .sh { margin:0; font-size:16px; line-height:24px; }
  .ctx .sh button { padding:14px 0; cursor:pointer; }
  .ctx-in { border:0; border-radius:0; padding:0 0 16px; }
  .ctx.shut .ctx-in { display:none; }
  .row { padding:18px 16px; column-gap:12px; row-gap:0; align-items:start;
    grid-template-columns:40px minmax(0, 1fr) 112px; grid-template-rows:auto auto auto auto auto auto;
    grid-template-areas:"ic t go" "ic s s" "n n viz" "l l viz" "c c viz" "w w w"; }
  .ic { width:40px; height:40px; } .ic svg { width:20px; height:20px; }
  .nm b { font-size:17px; align-self:end; } .nm span { font-size:13px; }
  .num { font-size:32px; margin-top:16px; } .lbl { margin-top:6px; } .chg { margin-top:4px; }
  .viz { margin-top:16px; } .viz .cap { text-align:right; font-size:11px; margin-top:4px; }
  .when { margin-top:10px; padding-top:10px; border-top:1px solid var(--line); font-size:12.5px; color:var(--muted); }
  .go { width:30px; height:30px; } }

/* 頁尾 */
.foot { background:#ffffff; border-top:1px solid var(--line); padding:30px 0 44px; }
.foot .cols { display:grid; gap:20px; }
@media (min-width:761px) { .foot .cols { grid-template-columns:repeat(3, minmax(0, 1fr)); gap:24px; } }
@media (min-width:1100px) { .foot .cols { grid-template-columns:360px minmax(0, 1fr) minmax(0, 1fr); } }
.foot b { font-size:13px; color:var(--ink); letter-spacing:.04em; }
.foot p { margin:6px 0 0; font-size:13px; color:var(--muted); line-height:1.75; }
.foot a { color:var(--ink); text-decoration:none; font-weight:500; }
"""

# Shane 2026-11-01 選了「人文」（霞鶩文楷標題＋DM Sans 數字），配色只用黑白灰
FONTS = "LXGW+WenKai+TC:wght@400;700&family=DM+Sans:wght@400;500;700&family=Noto+Sans+TC:wght@400;500;700"
