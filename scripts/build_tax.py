"""台灣稅收與所得頁：/tax/（中英日韓）＋ 各鄉鎮市區所得頁 /tax/town/<縣市鄉鎮>/（中文）。

資料：data/tax/（每月稅收、稅收與預算）、data/income/（各鄉鎮市區、村里綜合所得；town-map.json 鄉鎮界）
由 scripts/fetch_tax.py 從財政部統計處、財政資訊中心開放資料整理。
版面照全站 v3：一個問題、一句話、三個大數字、一張深色主圖、三張白卡、一個摺疊表。
build_pages.py 部署時呼叫 build(out, head, nav)。
"""
import csv
import html
import json
from collections import defaultdict
from pathlib import Path
from urllib.parse import quote

import build_births as bb
import i18n_en
import i18n_ja
import i18n_ko

ROOT = Path(__file__).resolve().parent.parent
TAX = ROOT / "data/tax"
INC = ROOT / "data/income"
SITE = "https://taiwandata.info"
PREFIX = bb.PREFIX
e = html.escape
LANG = "zh"
MON = bb.MON

# 主要稅目：(代號, 中, 英, 日, 韓)
TAXES = [
    ("income", "所得稅", "Income tax", "所得税", "소득세"),
    ("vat", "營業稅", "Business tax (VAT)", "営業税", "영업세"),
    ("stock", "證券交易稅", "Securities transaction tax", "証券取引税", "증권거래세"),
    ("commodity", "貨物稅", "Commodity tax", "貨物税", "화물세"),
    ("customs", "關稅", "Customs duties", "関税", "관세"),
    ("land", "土地稅", "Land tax", "土地税", "토지세"),
    ("tobacco", "菸酒稅", "Tobacco and alcohol tax", "たばこ・酒税", "담배·주류세"),
    ("estate", "遺產及贈與稅", "Estate and gift tax", "相続・贈与税", "상속·증여세"),
]
OTHER = ("other", "其他", "Other", "その他", "기타")


def L(zh, en, ja, ko):
    return {"zh": zh, "en": en, "ja": ja, "ko": ko}[LANG]


def tax_name(t):
    return L(*t[1:])


def county_name(c):
    return L(c, i18n_en.COUNTIES.get(c, c), i18n_ja.COUNTIES.get(c, c), i18n_ko.COUNTIES.get(c, c))


def read(path):
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def money(k):
    """千元 → 兆／億（中日）、조／억（韓）、trillion/billion（英）。"""
    yi = k / 1e5  # 億元
    if LANG == "en":
        b = k / 1e6
        return f"NT${b / 1000:.2f} trillion" if b >= 1000 else f"NT${b:,.1f} billion"
    if yi >= 10000:
        return L(f"{yi / 10000:.2f} 兆元", "", f"{yi / 10000:.2f}兆台湾元", f"{yi / 10000:.2f}조 대만달러")
    return L(f"{yi:,.0f} 億元", "", f"{yi:,.0f}億台湾元", f"{yi:,.0f}억 대만달러")


def wan(k):
    """所得（千元）→ 萬元。"""
    return L(f"{k / 10:,.1f} 萬元", f"NT${k:,.0f}k", f"{k / 10:,.1f}万台湾元", f"{k / 10:,.1f}만 대만달러")


def pct(a, b):
    return (a - b) / b * 100 if b else 0


def em(text, neg=False):
    return f'<em{" class=r" if neg else ""}>{text}</em>'


def ym_label(y, m):
    return L(f"{y} 年 {m} 月", f"{MON[m - 1]} {y}", f"{y}年{m}月", f"{y}년 {m}월")


def span_label(y, m):
    if m == 1:
        return ym_label(y, 1)
    return L(f"{y} 年 1～{m} 月", f"Jan–{MON[m - 1]} {y}", f"{y}年1～{m}月", f"{y}년 1~{m}월")


# ---------- 資料 ----------

def load():
    monthly = {}
    for r in read(TAX / "monthly.csv"):
        monthly[r["ym"]] = {k: float(v) for k, v in r.items() if k != "ym"}
    budget = defaultdict(dict)
    for r in read(TAX / "budget.csv"):
        budget[int(r["year"])][r["item"]] = (float(r["actual"]), float(r["budget"]), r["rate"])
    towns = defaultdict(dict)
    for r in read(INC / "towns.csv"):
        if r["town"].endswith("其他"):
            continue
        towns[int(r["year"])][r["town"]] = {k: float(r[k]) for k in ("households", "total", "mean", "median", "q1", "q3")}
    villages = defaultdict(list)
    for r in read(INC / "villages.csv"):
        villages[r["town"]].append({"name": r["village"], **{k: float(r[k]) for k in ("households", "total", "mean", "median", "q1", "q3")}})
    tmap = json.loads((INC / "town-map.json").read_text(encoding="utf-8")) if (INC / "town-map.json").exists() else {"towns": {}}
    return monthly, budget, towns, villages, tmap


def county_of(town):
    return town[:3]


def town_short(town):
    return town[3:]


def town_label(town, tmap):
    """鄉鎮名：中文、日文用漢字；英文、韓文用內政部英文名。"""
    if LANG in ("zh", "ja"):
        s = town_short(town)
        return s.replace("臺", "台") if LANG == "ja" else s
    t = tmap["towns"].get(town)
    return t["en"] if t else town_short(town)


def list_label(town, tmap):
    """排行榜用的短名：中日「竹北市 新竹縣」，英韓「Zhubei City, Hsinchu」。"""
    c = county_name(county_of(town))
    if LANG in ("en", "ko"):
        for s in (" County", " City"):
            c = c.replace(s, "")
        return f"{town_label(town, tmap)}, {c}"
    return f"{town_label(town, tmap)} {c}"


def town_url(town):
    return f"/tax/town/{quote(town)}/"


# ---------- 圖 ----------

W, H = 760, 300
PL, PR, PT, PB = 58, 70, 28, 28


def nice(hi, n=4):
    raw = hi / n
    mag = 10 ** len(str(int(raw))) / 10 if raw >= 1 else 1
    step = next(s * mag for s in (1, 2, 2.5, 5, 10) if s * mag >= raw)
    return step, step * -(-hi // step)


def cum_chart(series, unit_div, unit_lab, dark=True, W=760, H=300, fs=11):
    """累計稅收：每條線 12 個月（未到的月份 None）。series：[(標籤, 顏色, 值, 粗細)]"""
    vals = [v for _, _, s, _ in series for v in s if v is not None]
    step, top = nice(max(vals) / unit_div)
    PR_ = PR if W > 500 else 44
    X = lambda i: PL + (W - PL - PR_) * i / 11
    Y = lambda v: PT + (H - PT - PB) * (1 - v / top)
    grid = "#33373c" if dark else "#e6e8eb"
    txt = "#9aa0a6" if dark else "#676d73"
    svg = ""
    g = 0
    while g <= top + 1e-9:
        svg += (f'<line x1="{PL}" x2="{W - PR_}" y1="{Y(g):.1f}" y2="{Y(g):.1f}" stroke="{grid}"/>'
                f'<text x="{PL - 6}" y="{Y(g) + 4:.1f}" text-anchor="end" fill="{txt}" font-size="{fs}">{g:,g}</text>')
        g += step
    svg += f'<text x="{PL - 6}" y="12" text-anchor="end" fill="{txt}" font-size="{fs}">{unit_lab}</text>'
    ends = []
    for i in range(12):
        if W < 500 and i % 2:
            continue
        svg += f'<text x="{X(i):.1f}" y="{H - 8}" text-anchor="middle" fill="{txt}" font-size="{fs}">{L(f"{i + 1}月", MON[i], f"{i + 1}月", f"{i + 1}월")}</text>'
    for lab, col, s, wdt in series:
        pts = [(X(i), Y(v / unit_div)) for i, v in enumerate(s) if v is not None]
        if not pts:
            continue
        svg += f'<path d="M{" L".join(f"{x:.1f},{y:.1f}" for x, y in pts)}" fill="none" stroke="{col}" stroke-width="{wdt}" stroke-linejoin="round" stroke-linecap="round"/>'
        x, y = pts[-1]
        svg += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{3.5 if wdt > 2 else 2.5}" fill="{col}"/>'
        ends.append([x, y, col, lab])
    # 線尾標籤：同一處的往上下推開，不重疊
    ends.sort(key=lambda a: a[1])
    for k in range(1, len(ends)):
        if abs(ends[k][0] - ends[k - 1][0]) < 40 and ends[k][1] - ends[k - 1][1] < fs + 4:
            ends[k][1] = ends[k - 1][1] + fs + 4
    for x, y, col, lab in ends:
        svg += f'<text x="{x + 7:.1f}" y="{y + 4:.1f}" fill="{col}" font-size="{fs + 1}" font-weight="700">{lab}</text>'
    return f'<svg viewBox="0 0 {W} {H}" class="ch" role="img">{svg}</svg>'


def hbars(items, color="#1f7ad6", fmt=lambda v: f"{v:,.0f}", link=None, maxv=None):
    """items：[(標籤, 值, 右側小字)]"""
    maxv = maxv or max(v for _, v, _ in items) or 1
    out = ""
    for lab, v, small in items:
        name = f'<a href="{link(lab)}">{e(lab[1])}</a>' if link else e(lab)
        out += (f'<li><span class="nm">{name}</span><span class="tr"><i style="width:{max(0, v) / maxv * 100:.1f}%;background:{color}"></i></span>'
                f'<span class="vl">{fmt(v)}<small>{small}</small></span></li>')
    return f'<ul class="hb">{out}</ul>'


def year_bars(years, vals, hl, unit_div, lab_unit, budget=None):
    n = len(years)
    top_raw = max(max(vals), max(budget or [0])) / unit_div
    step, top = nice(top_raw)
    w, h, pl, pr, pt, pb = 420, 230, 40, 8, 24, 24
    slot = (w - pl - pr) / n
    X = lambda i: pl + slot * (i + .5)
    Y = lambda v: pt + (h - pt - pb) * (1 - v / top)
    svg = ""
    g = 0
    while g <= top + 1e-9:
        svg += f'<line x1="{pl}" x2="{w - pr}" y1="{Y(g):.1f}" y2="{Y(g):.1f}" stroke="#e6e8eb"/><text x="{pl - 5}" y="{Y(g) + 4:.1f}" text-anchor="end" fill="#676d73" font-size="10">{g:,g}</text>'
        g += step
    svg += f'<text x="{pl - 5}" y="11" text-anchor="end" fill="#676d73" font-size="10">{lab_unit}</text>'
    for i, (yr, v) in enumerate(zip(years, vals)):
        bw = max(2, slot - 3)
        col = "#1f7ad6" if yr == hl else "#c9cdd2"
        svg += f'<rect x="{X(i) - bw / 2:.1f}" y="{Y(v / unit_div):.1f}" width="{bw:.1f}" height="{Y(0) - Y(v / unit_div):.1f}" fill="{col}" rx="1.5"><title>{yr}: {v / unit_div:,.2f}</title></rect>'
        if budget and budget[i]:
            yb = Y(budget[i] / unit_div)
            svg += f'<line x1="{X(i) - bw / 2 - 1:.1f}" x2="{X(i) + bw / 2 + 1:.1f}" y1="{yb:.1f}" y2="{yb:.1f}" stroke="#1d2125" stroke-width="1.5"/>'
        if i in (0, n - 1) or yr % 5 == 0:
            svg += f'<text x="{X(i):.1f}" y="{h - 7}" text-anchor="middle" fill="#676d73" font-size="10">{yr}</text>'
    return f'<svg viewBox="0 0 {w} {h}" class="ch" role="img">{svg}</svg>'


def month_bars(labels, vals, unit_div, lab_unit):
    n = len(vals)
    step, top = nice(max(vals) / unit_div)
    w, h, pl, pr, pt, pb = 420, 210, 40, 8, 24, 24
    slot = (w - pl - pr) / n
    X = lambda i: pl + slot * (i + .5)
    Y = lambda v: pt + (h - pt - pb) * (1 - v / top)
    svg = ""
    g = 0
    while g <= top + 1e-9:
        svg += f'<line x1="{pl}" x2="{w - pr}" y1="{Y(g):.1f}" y2="{Y(g):.1f}" stroke="#e6e8eb"/><text x="{pl - 5}" y="{Y(g) + 4:.1f}" text-anchor="end" fill="#676d73" font-size="10">{g:,g}</text>'
        g += step
    svg += f'<text x="{pl - 5}" y="11" text-anchor="end" fill="#676d73" font-size="10">{lab_unit}</text>'
    for i, (lb, v) in enumerate(zip(labels, vals)):
        bw = max(2, slot - 2)
        col = "#1f7ad6" if i >= n - 12 else "#c9cdd2"
        svg += f'<rect x="{X(i) - bw / 2:.1f}" y="{Y(max(v, 0) / unit_div):.1f}" width="{bw:.1f}" height="{Y(0) - Y(max(v, 0) / unit_div):.1f}" fill="{col}" rx="1.5"><title>{lb}: {v / unit_div:,.1f}</title></rect>'
        if (i == n - 1 and not lb.endswith(("-01", "-02", "-03", "-04"))) or lb.endswith("-01"):
            svg += f'<text x="{X(i):.1f}" y="{h - 7}" text-anchor="{"end" if i == n - 1 else "middle"}" fill="#676d73" font-size="10">{lb[:4]}/{int(lb[5:])}</text>'
    return f'<svg viewBox="0 0 {w} {h}" class="ch" role="img">{svg}</svg>'


def line_chart(years, series, unit_div, lab_unit, w=420, h=220):
    vals = [v for _, _, s in series for v in s if v]
    step, top = nice(max(vals) / unit_div)
    pl, pr, pt, pb = 40, 64, 24, 24
    n = len(years)
    X = lambda i: pl + (w - pl - pr) * i / max(1, n - 1)
    Y = lambda v: pt + (h - pt - pb) * (1 - v / top)
    svg = ""
    g = 0
    while g <= top + 1e-9:
        svg += f'<line x1="{pl}" x2="{w - pr}" y1="{Y(g):.1f}" y2="{Y(g):.1f}" stroke="#e6e8eb"/><text x="{pl - 5}" y="{Y(g) + 4:.1f}" text-anchor="end" fill="#676d73" font-size="10">{g:,g}</text>'
        g += step
    svg += f'<text x="{pl - 5}" y="11" text-anchor="end" fill="#676d73" font-size="10">{lab_unit}</text>'
    for lab, col, s in series:
        pts = [(X(i), Y(v / unit_div)) for i, v in enumerate(s) if v]
        svg += f'<path d="M{" L".join(f"{x:.1f},{y:.1f}" for x, y in pts)}" fill="none" stroke="{col}" stroke-width="2.5" stroke-linejoin="round"/>'
        x, y = pts[-1]
        svg += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" fill="{col}"/><text x="{x + 6:.1f}" y="{y + 4:.1f}" fill="{col}" font-size="11" font-weight="700">{lab}</text>'
    for i, yr in enumerate(years):
        if n <= 8 or i in (0, n - 1) or yr % 2 == 0:
            svg += f'<text x="{X(i):.1f}" y="{h - 7}" text-anchor="middle" fill="#676d73" font-size="10">{yr}</text>'
    return f'<svg viewBox="0 0 {w} {h}" class="ch" role="img">{svg}</svg>'


# 財政部 2019 年起的所得數字和 2018 年以前落差很大（全台平均一年少約 21%），兩段不直接比，趨勢只畫 2019 年起
BREAK = 2019

BLUES = ["#d6e6f7", "#a9cbef", "#6fa6e3", "#3a7fd0", "#1c5aa6"]


def town_map(cur, tmap, year):
    """各鄉鎮市區中位數地圖（本島），分 5 級，每級鄉鎮數差不多。"""
    meds = sorted(v["median"] for v in cur.values())
    br = [meds[len(meds) * q // 5] for q in (1, 2, 3, 4)]

    def cls(v):
        k = 0
        while k < 4 and v >= br[k]:
            k += 1
        return k
    paths = ""
    for town, t in tmap["towns"].items():
        if not t["d"] or town not in cur:
            continue
        v = cur[town]
        tip = f'{county_name(county_of(town))} {town_label(town, tmap)}{L("：中位數 ", ": median ", "：中央値 ", ": 중위수 ")}{wan(v["median"])}'
        paths += (f'<path d="{t["d"]}" fill="{BLUES[cls(v["median"])]}" data-t="{e(tip)}" data-u="{town_url(town)}" tabindex="0"/>')
    edges = [meds[0]] + br + [meds[-1]]
    leg = "".join(f'<span><i style="background:{c}"></i>{edges[k] / 10:,.0f}～{edges[k + 1] / 10:,.0f}</span>' for k, c in enumerate(BLUES)) if LANG != "en" else \
        "".join(f'<span><i style="background:{c}"></i>{edges[k]:,.0f}–{edges[k + 1]:,.0f}k</span>' for k, c in enumerate(BLUES))
    return (f'<svg viewBox="0 0 {tmap.get("width", 720)} {tmap.get("height", 1220)}" class="tmap" role="img" '
            f'aria-label="{e(L("各鄉鎮市區綜合所得中位數地圖", "Map of median income by township", "郷鎮市区別の所得中央値地図", "향·진·시·구별 소득 중위수 지도"))}">{paths}</svg>'
            f'<div class="mleg">{L("中位數（萬元）", "Median (NT$)", "中央値（万台湾元）", "중위수(만 대만달러)")} {leg}</div>')


# ---------- 版面 ----------

CSS = """
body { background:#f2f3f5; }
.stage { background:#1b1d20; color:#e8eaed; }
.w { max-width:1200px; margin:0 auto; padding:0 16px; }
.hero { padding-top:26px; padding-bottom:22px; }
.q { font-size:13px; color:#9aa0a6; letter-spacing:.08em; margin:0 0 6px; }
.lede { font-size:clamp(21px,2.6vw,30px); line-height:1.4; margin:0 0 18px; font-weight:700; max-width:920px; }
.lede em { font-style:normal; color:#4fb0f0; } .lede em.r { color:#ff6b6b; }
.lt .lede em { color:#1f7ad6; } .lt .lede em.r { color:#d9534f; }
.kns { display:flex; gap:28px; flex-wrap:wrap; margin:0 0 16px; }
.kn b { display:block; font-size:30px; line-height:1.1; font-weight:700; }
.kn span { display:block; font-size:12px; color:#9aa0a6; margin-top:2px; }
.lt .kn span { color:#676d73; }
.ch { display:block; width:100%; height:auto; }
.stage .legend { color:#9aa0a6; }
.legend { display:flex; gap:16px; flex-wrap:wrap; font-size:12px; color:#676d73; margin:0 0 6px; }
.legend i { display:inline-block; width:14px; height:3px; vertical-align:middle; margin-right:5px; border-radius:2px; }
.src { font-size:12px; color:#9aa0a6; margin:10px 0 0; }
.lt .src { color:#676d73; }
.cards { display:grid; grid-template-columns:repeat(3,1fr); gap:16px; padding:18px 0 8px; }
.card { background:#fff; border:1px solid #e6e8eb; border-radius:14px; padding:16px 18px 12px; min-width:0; }
.card h2 { font-size:16px; margin:0 0 10px; line-height:1.45; font-weight:700; }
.card h2 em { font-style:normal; color:#1f7ad6; } .card h2 em.r { color:#d9534f; }
.card .note { font-size:12px; color:#676d73; margin:8px 0 0; }
.hb { list-style:none; margin:0; padding:0; display:grid; gap:6px; }
.hb li { display:grid; grid-template-columns:8.5em 1fr auto; gap:8px; align-items:center; font-size:13px; }
.hb .nm { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.hb .nm a { color:#1d2125; text-decoration:none; } .hb .nm a:hover { text-decoration:underline; }
.hb .tr { height:12px; background:#eef0f2; border-radius:3px; overflow:hidden; }
.hb .tr i { display:block; height:100%; border-radius:3px; }
.hb .vl { text-align:right; white-space:nowrap; min-width:5.5em; }
.hb .vl small { color:#676d73; margin-left:6px; }
.sec2 { padding-top:30px; padding-bottom:6px; }
.split { display:grid; grid-template-columns:minmax(0,5fr) minmax(0,4fr); gap:16px; align-items:start; }
.stack { display:grid; gap:16px; }
.hero .ch { max-width:1000px; }
.tmap { display:block; width:100%; max-height:760px; height:auto; }
.tmap path { stroke:#fff; stroke-width:.6; cursor:pointer; }
.tmap path:hover, .tmap path:focus { stroke:#1d2125; stroke-width:2; outline:none; }
.mleg { display:flex; flex-wrap:wrap; gap:4px 12px; font-size:12px; color:#676d73; margin-top:6px; }
.mleg span { display:inline-flex; align-items:center; gap:4px; } .mleg i { width:12px; height:12px; border-radius:2px; display:inline-block; }
.mtip { min-height:1.6em; font-size:14px; margin:4px 0; }
.mtip a { color:#1f7ad6; }
.fold { margin-top:8px; margin-bottom:40px; } .fold summary { cursor:pointer; font-size:14px; color:#676d73; padding:10px 0; }
.fold .inner { background:#fff; border:1px solid #e6e8eb; border-radius:14px; padding:14px 18px; overflow-x:auto; }
table.tb { width:100%; border-collapse:collapse; font-size:13px; }
table.tb th { text-align:left; color:#676d73; font-weight:500; padding:6px 8px; border-bottom:1px solid #e6e8eb; white-space:nowrap; }
table.tb td { padding:6px 8px; border-bottom:1px solid #eef0f2; white-space:nowrap; }
table.tb td.n, table.tb th.n { text-align:right; }
table.tb a { color:#1f7ad6; text-decoration:none; }
.cty { display:flex; flex-wrap:wrap; gap:6px; margin:0 0 10px; }
.cty a { padding:4px 10px; border-radius:999px; background:#eef0f2; color:#1d2125; text-decoration:none; font-size:13px; }
html[lang=en] .hb li, html[lang=ko] .hb li { grid-template-columns:14em 1fr auto; }
footer { font-size:12px; color:#676d73; padding:0 0 40px; }
.ch.narrow { display:none; }
@media (max-width:600px) { .ch.wide { display:none; } .ch.narrow { display:block; } }
@media (max-width:860px) { .cards, .split { grid-template-columns:1fr; } .kn b { font-size:25px; } .kns { gap:18px; } .hb li { grid-template-columns:7em 1fr auto; } }
"""

JS = """<script>
(function () {
  var tip = document.getElementById("mtip"); if (!tip) return;
  var def = tip.innerHTML, picked = null;
  document.querySelectorAll(".tmap path").forEach(function (p) {
    function show() { tip.innerHTML = p.getAttribute("data-t") + ' <a href="' + p.getAttribute("data-u") + '">' + tip.getAttribute("data-more") + "</a>"; }
    p.addEventListener("mouseenter", show); p.addEventListener("focus", show);
    p.addEventListener("click", function () { if (picked === p) { location.href = p.getAttribute("data-u"); } picked = p; show(); });
    p.addEventListener("keydown", function (ev) { if (ev.key === "Enter") location.href = p.getAttribute("data-u"); });
  });
})();
</script>"""


def foot():
    src = L("資料來源：財政部統計處「全國賦稅收入實徵淨額」、「賦稅收入實徵淨額與預算數之比較」；財政部財政資訊中心「綜稅綜合所得總額全國各縣市鄉鎮村里統計分析表」（政府資料開放平臺）。每天檢查一次。",
            "Source: Ministry of Finance, Department of Statistics (net tax revenue by tax, and compared with budget); Fiscal Information Agency (consolidated income tax returns by township and village). Checked daily.",
            "出典：財政部統計処「税収実績（税目別）」「税収と予算の比較」、財政部財政資訊中心「総合所得税の所得総額・郷鎮市区村里別統計」（政府オープンデータ）。毎日確認。",
            "출처: 재정부 통계처 '세수 실적(세목별)', '세수와 예산 비교', 재정부 재정정보센터 '종합소득세 소득 총액 향·진·시·구·촌·리별 통계'(정부 오픈 데이터). 매일 확인.")
    foot2 = L("本站為個人經營，非政府網站；所有數據皆來自政府開放資料。",
              "An independent site, not affiliated with the government. All figures come from government open data.",
              i18n_ja.FOOT, getattr(i18n_ko, "FOOT", "개인이 운영하는 비공식 사이트로, 정부와 관계가 없습니다. 모든 수치는 정부 오픈 데이터입니다."))
    return f"<footer class=w><div>{src}</div><div>{foot2}</div></footer>"


def page(out, head, nav, monthly, budget, towns, villages, tmap):
    last = max(monthly)
    y, m = int(last[:4]), int(last[5:])

    def ytd(year, key="total", upto=m):
        return sum(monthly.get(f"{year}-{i:02d}", {}).get(key, 0) for i in range(1, upto + 1))

    cur, prev = ytd(y), ytd(y - 1)
    ch = pct(cur, prev)
    mon_cur = monthly[last]["total"]

    def cum(year, upto=12):
        s, out = 0, []
        for i in range(1, 13):
            k = f"{year}-{i:02d}"
            if i > upto or k not in monthly:
                out.append(None)
                continue
            s += monthly[k]["total"]
            out.append(s)
        return out
    unit_div = 1e5 if LANG != "en" else 1e6  # 億元 / NT$ billion
    unit_lab = L("億元", "NT$ bn", "億元", "억 원")
    ser = [(str(y - 2), "#55595e", cum(y - 2), 1.5), (str(y - 1), "#9aa0a6", cum(y - 1), 2), (str(y), "#4fb0f0", cum(y, m), 3)]
    # 桌機一張寬圖，手機另一張窄圖（字才不會太小）
    hero_chart = (cum_chart(ser, unit_div, unit_lab).replace('class="ch"', 'class="ch wide"')
                  + cum_chart(ser, unit_div, unit_lab, W=380, H=300, fs=12).replace('class="ch"', 'class="ch narrow"'))
    up = ch >= 0
    chs = f"{abs(ch):.1f}%"
    inc_share = ytd(y, "income") / cur * 100
    lede = L(f"{span_label(y, m)}全國稅收 {em(money(cur))}，比去年同期{'多' if up else '少'} {em(chs, not up)}；所得稅佔 {em(f'{inc_share:.0f}%')}。",
             f"Taiwan collected {em(money(cur))} in taxes in {span_label(y, m)}, {em(chs, not up)} {'more' if up else 'less'} than a year earlier; income tax made up {em(f'{inc_share:.0f}%')}.",
             f"{span_label(y, m)}の税収は{em(money(cur))}、前年同期比 {em(('+' if up else '−') + chs, not up)}。所得税が{em(f'{inc_share:.0f}%')}を占めます。",
             f"{span_label(y, m)} 세수는 {em(money(cur))}로 전년 동기 대비 {em(('+' if up else '−') + chs, not up)}, 소득세가 {em(f'{inc_share:.0f}%')}를 차지합니다.")
    kn = [(money(cur), L(f"{span_label(y, m)}累計", f"{span_label(y, m)}", f"{span_label(y, m)}累計", f"{span_label(y, m)} 누계")),
          (("+" if up else "−") + chs, L("比去年同期", "vs same period last year", "前年同期比", "전년 동기 대비")),
          (money(mon_cur), L(f"{m} 月單月", f"{MON[m - 1]} alone", f"{m}月単月", f"{m}월 한 달"))]
    kns = "".join(f'<div class="kn"><b>{a}</b><span>{b}</span></div>' for a, b in kn)
    legend = (f'<div class="legend"><span><i style="background:#4fb0f0"></i>{y}</span><span><i style="background:#9aa0a6"></i>{y - 1}</span>'
              f'<span><i style="background:#55595e"></i>{y - 2}</span></div>')
    hero = (f'<section class="stage"><div class="w hero"><p class="q">{L("政府今年收了多少稅？", "How much tax has Taiwan collected this year?", "台湾政府は今年どれだけ税を集めた？", "대만 정부는 올해 세금을 얼마나 걷었나?")}</p>'
            f'<p class="lede">{lede}</p><div class="kns">{kns}</div>{legend}{hero_chart}'
            f'<p class="src">{L("每月累計的全國賦稅收入實徵淨額（含中央與地方稅），財政部每月公布。", "Cumulative net tax revenue by month (national and local taxes), published monthly by the Ministry of Finance.", "月ごとの税収実績（国税・地方税）の累計。財政部が毎月発表。", "월별 세수 실적(국세·지방세) 누계. 재정부가 매월 발표.")}</p></div></section>')

    # 卡片 1：稅目
    parts = [(t, ytd(y, t[0])) for t in TAXES]
    other = cur - sum(v for _, v in parts)
    parts = sorted(parts, key=lambda x: -x[1]) + [(OTHER, other)]
    top2 = parts[1]
    c1 = (f'<div class="card"><h2>{L(f"所得稅 {em(money(parts[0][1]))} 最多，其次是{tax_name(top2[0])}", f"Income tax brought in {em(money(parts[0][1]))}, followed by {tax_name(top2[0]).lower()}", f"最大は所得税の{em(money(parts[0][1]))}、次いで{tax_name(top2[0])}", f"소득세 {em(money(parts[0][1]))}가 가장 많고 다음은 {tax_name(top2[0])}") if parts[0][0][0] == "income" else tax_name(parts[0][0])}</h2>'
          + hbars([(tax_name(t), v / unit_div, f"{v / cur * 100:.0f}%") for t, v in parts], fmt=lambda v: f"{v:,.0f}")
          + f'<p class="note">{L(f"{span_label(y, m)}累計，單位：億元。所得稅含房地合一稅。", f"{span_label(y, m)}, NT$ billion. Income tax includes the real-estate income tax.", f"{span_label(y, m)}累計、単位：億台湾元。所得税には不動産譲渡所得税を含む。", f"{span_label(y, m)} 누계, 단위: 억 대만달러. 소득세에 부동산 양도소득세 포함.")}</p></div>')

    # 卡片 2：歷年全年稅收與預算
    years = sorted(yr for yr in budget if "總計" in budget[yr] and yr < y)
    years = years[-20:]
    acts = [budget[yr]["總計"][0] for yr in years]
    buds = [budget[yr]["總計"][1] for yr in years]
    ly = years[-1]
    a, bgt, rate = budget[ly]["總計"]
    diff = a - bgt
    over = diff >= 0
    c2 = (f'<div class="card"><h2>{L(f"{ly} 年稅收 {em(money(a))}，比預算{'多' if over else '少'} {em(money(abs(diff)), not over)}", f"{ly} revenue was {em(money(a))}, {em(money(abs(diff)), not over)} {'above' if over else 'below'} budget", f"{ly}年の税収は{em(money(a))}、予算より{em(money(abs(diff)), not over)}{'多い' if over else '少ない'}", f"{ly}년 세수는 {em(money(a))}로 예산보다 {em(money(abs(diff)), not over)} {'많음' if over else '적음'}")}</h2>'
          + year_bars(years, acts, ly, 1e8 if LANG != "en" else 1e9, L("兆元", "NT$ tn", "兆元", "조 원"), buds)
          + f'<p class="note">{L("長條是實徵淨額，黑線是預算數。", "Bars: actual net revenue. Black ticks: budget.", "棒は実績、黒線は予算額。", "막대는 실적, 검은 선은 예산.")} {L("達成率", "Achieved", "達成率", "달성률")} {rate}%</p></div>')

    # 卡片 3：證券交易稅（最近 36 個月）
    ks = sorted(monthly)[-36:]
    st_cur, st_prev = ytd(y, "stock"), ytd(y - 1, "stock")
    sc = pct(st_cur, st_prev)
    c3 = (f'<div class="card"><h2>{L(f"證券交易稅今年 {em(money(st_cur))}，比去年同期{'多' if sc >= 0 else '少'} {em(f'{abs(sc):.0f}%', sc < 0)}", f"Securities transaction tax: {em(money(st_cur))} so far this year, {em(f'{abs(sc):.0f}%', sc < 0)} {'more' if sc >= 0 else 'less'} than last year", f"証券取引税は今年{em(money(st_cur))}、前年同期比 {em(('+' if sc >= 0 else '−') + f'{abs(sc):.0f}%', sc < 0)}", f"증권거래세는 올해 {em(money(st_cur))}, 전년 동기 대비 {em(('+' if sc >= 0 else '−') + f'{abs(sc):.0f}%', sc < 0)}")}</h2>'
          + month_bars(ks, [monthly[k]["stock"] for k in ks], unit_div, unit_lab)
          + f'<p class="note">{L("每月證券交易稅，股市成交量越大越多。藍色是最近 12 個月。", "Monthly securities transaction tax; it rises with stock-market turnover. Blue: last 12 months.", "月別の証券取引税。株式の売買代金が多いほど増える。青は直近12か月。", "월별 증권거래세. 주식 거래대금이 많을수록 늘어남. 파란색은 최근 12개월.")}</p></div>')

    # 摺疊：每月稅收表（最近 24 個月）
    rows = ""
    for k in sorted(monthly)[-24:][::-1]:
        d = monthly[k]
        rows += f'<tr><td>{ym_label(int(k[:4]), int(k[5:]))}</td>' + "".join(f'<td class="n">{d.get(c, 0) / unit_div:,.1f}</td>' for c in ["total"] + [t[0] for t in TAXES]) + "</tr>"
    fold1 = (f'<details class="fold w"><summary>{L("看每月各稅目數字（最近 24 個月）", "Monthly revenue by tax (last 24 months)", "月別・税目別の数値（直近24か月）", "월별·세목별 수치(최근 24개월)")}</summary><div class="inner"><table class="tb"><tr><th></th>'
             f'<th class="n">{L("總計", "Total", "合計", "합계")}</th>' + "".join(f'<th class="n">{tax_name(t)}</th>' for t in TAXES) + f'</tr>{rows}</table>'
             f'<p class="src">{L("單位：億元", "NT$ billion", "単位：億台湾元", "단위: 억 대만달러")}</p></div></details>')

    # ---- 所得 ----
    iy = max(towns)
    cur_t = towns[iy]
    ranked = sorted(cur_t.items(), key=lambda kv: -kv[1]["median"])
    hi, lo = ranked[0], ranked[-1]
    hh = sum(v["households"] for v in cur_t.values())
    tot = sum(v["total"] for v in cur_t.values())
    mean_all = tot / hh
    lede2 = L(f"{iy} 年所得（{iy + 1 - 1911 + 1911 - 1911 if False else ''}）中位數最高的是{county_name(county_of(hi[0]))}{town_label(hi[0], tmap)} {em(wan(hi[1]['median']))}，最低是{county_name(county_of(lo[0]))}{town_label(lo[0], tmap)} {em(wan(lo[1]['median']), True)}。",
              f"In {iy}, the highest median income per tax return was in {town_label(hi[0], tmap)}, {county_name(county_of(hi[0]))} ({em(wan(hi[1]['median']))}); the lowest was in {town_label(lo[0], tmap)}, {county_name(county_of(lo[0]))} ({em(wan(lo[1]['median']), True)}).",
              f"{iy}年の所得中央値が最も高いのは{county_name(county_of(hi[0]))}{town_label(hi[0], tmap)}の{em(wan(hi[1]['median']))}、最も低いのは{county_name(county_of(lo[0]))}{town_label(lo[0], tmap)}の{em(wan(lo[1]['median']), True)}。",
              f"{iy}년 소득 중위수가 가장 높은 곳은 {county_name(county_of(hi[0]))} {town_label(hi[0], tmap)}({em(wan(hi[1]['median']))}), 가장 낮은 곳은 {county_name(county_of(lo[0]))} {town_label(lo[0], tmap)}({em(wan(lo[1]['median']), True)}).")
    lede2 = lede2.replace("（）", "")
    kn2 = [(wan(mean_all), L("全台平均每戶所得", "Average income per tax unit", "全国平均（1申告単位）", "전국 평균(납세 단위당)")),
           (f"{hh / 1e4:,.0f}{L(' 萬', '', '万', '만')}" if LANG != "en" else f"{hh / 1e6:.2f}M", L("申報戶數", "Tax filing units", "申告単位数", "신고 단위 수")),
           (str(len(cur_t)), L("個鄉鎮市區", "townships", "郷鎮市区", "향·진·시·구"))]
    kns2 = "".join(f'<div class="kn"><b>{a}</b><span>{b}</span></div>' for a, b in kn2)
    more = L("看各村里 ›", "Villages ›", "村里別を見る ›", "촌·리별 보기 ›")
    top10 = hbars([((t, list_label(t, tmap)), v["median"] / (10 if LANG != "en" else 1), "") for t, v in ranked[:10]],
                  fmt=lambda v: f"{v:,.1f}" if LANG != "en" else f"{v:,.0f}k", link=lambda lab: town_url(lab[0]))
    bot10 = hbars([((t, list_label(t, tmap)), v["median"] / (10 if LANG != "en" else 1), "") for t, v in ranked[-10:][::-1]],
                  color="#9aa0a6", fmt=lambda v: f"{v:,.1f}" if LANG != "en" else f"{v:,.0f}k", link=lambda lab: town_url(lab[0]),
                  maxv=ranked[0][1]["median"] / (10 if LANG != "en" else 1))
    # 歷年全台平均
    ys = [yy for yy in sorted(towns) if yy >= BREAK]
    means = [sum(v["total"] for v in towns[yy].values()) / sum(v["households"] for v in towns[yy].values()) for yy in ys]
    gm = pct(means[-1], means[0])
    unit_w = L("萬元", "NT$k", "万元", "만 원")
    trend = line_chart(ys, [(L("平均", "Average", "平均", "평균"), "#1f7ad6", means)], 10 if LANG != "en" else 1, unit_w)
    c4 = (f'<div class="card"><h2>{L(f"中位數最高的 10 個鄉鎮市區", "Top 10 townships by median income", "所得中央値が高い郷鎮市区トップ10", "소득 중위수 상위 10개 향·진·시·구")}</h2>{top10}'
          f'<p class="note">{L("單位：萬元", "NT$ thousand", "単位：万台湾元", "단위: 만 대만달러")}</p></div>')
    c5 = (f'<div class="card"><h2>{L("中位數最低的 10 個鄉鎮市區", "Bottom 10 townships by median income", "所得中央値が低い郷鎮市区10", "소득 중위수 하위 10개 향·진·시·구")}</h2>{bot10}'
          f'<p class="note">{L("單位：萬元；長條長度和上面同一把尺。", "NT$ thousand; same scale as the top-10 list.", "単位：万台湾元。棒の長さは上位10と同じ尺度。", "단위: 만 대만달러. 막대 길이는 상위 10과 같은 기준.")}</p></div>')
    c6 = (f'<div class="card"><h2>{L(f"全台平均每戶所得 {ys[0]}～{ys[-1]} 年{'增加' if gm >= 0 else '減少'} {em(f'{abs(gm):.0f}%', gm < 0)}", f"Average income per tax unit {'rose' if gm >= 0 else 'fell'} {em(f'{abs(gm):.0f}%', gm < 0)} from {ys[0]} to {ys[-1]}", f"全国平均は{ys[0]}～{ys[-1]}年で{em(('+' if gm >= 0 else '−') + f'{abs(gm):.0f}%', gm < 0)}", f"전국 평균은 {ys[0]}~{ys[-1]}년 {em(('+' if gm >= 0 else '−') + f'{abs(gm):.0f}%', gm < 0)}")}</h2>{trend}'
          f'<p class="note">{L("全台所得總額÷申報戶數。財政部沒有公布全台中位數。2018 年以前的數字和之後落差很大，不直接相比，只畫 2019 年起。", "Total income ÷ filing units. The ministry does not publish a national median. Figures before 2019 are not comparable with later years, so the chart starts in 2019.", "所得総額÷申告単位数。全国の中央値は公表されていない。2018年以前は以降と大きく食い違うため、2019年から表示。", "소득 총액÷신고 단위 수. 전국 중위수는 공표되지 않음. 2018년 이전 수치는 이후와 차이가 커서 2019년부터 표시.")}</p></div>')
    # 縣市表（含連結）
    by_c = defaultdict(list)
    for t, v in cur_t.items():
        by_c[county_of(t)].append((t, v))
    trs = ""
    for c, _ in bb.COUNTIES:
        lst = sorted(by_c.get(c, []), key=lambda kv: -kv[1]["median"])
        if not lst:
            continue
        ch_hh = sum(v["households"] for _, v in lst)
        ch_m = sum(v["total"] for _, v in lst) / ch_hh
        links = "、".join(f'<a href="{town_url(t)}">{e(town_label(t, tmap))}</a>' for t, _ in lst) if LANG in ("zh", "ja") else \
            ", ".join(f'<a href="{town_url(t)}">{e(town_label(t, tmap))}</a>' for t, _ in lst)
        trs += f'<tr><td><b>{county_name(c)}</b></td><td class="n">{wan(ch_m)}</td><td class="n">{ch_hh:,.0f}</td><td style="white-space:normal">{links}</td></tr>'
    fold2 = (f'<details class="fold w"><summary>{L("看各縣市與全部鄉鎮市區（點名稱看各村里）", "All counties and townships (tap a name for its villages)", "県・市別とすべての郷鎮市区（名前を押すと村里別）", "현·시별 및 모든 향·진·시·구(이름을 누르면 촌·리별)")}</summary><div class="inner"><table class="tb">'
             f'<tr><th>{L("縣市", "County/city", "県・市", "현·시")}</th><th class="n">{L("平均每戶所得", "Average", "平均", "평균")}</th><th class="n">{L("申報戶數", "Units", "申告単位", "신고 단위")}</th><th>{L("鄉鎮市區（依中位數高到低）", "Townships (highest median first)", "郷鎮市区（中央値の高い順）", "향·진·시·구(중위수 높은 순)")}</th></tr>{trs}</table></div></details>')
    sec2 = (f'<section class="lt"><div class="w sec2"><p class="q" style="color:#676d73">{L("各地收入差多少？", "How does income differ across Taiwan?", "地域でどれだけ所得が違う？", "지역별 소득은 얼마나 다를까?")}</p>'
            f'<p class="lede">{lede2}</p><div class="kns">{kns2}</div>'
            f'<div class="split"><div class="card"><p class="mtip" id="mtip" data-more="{e(more)}">{L("滑過或點地圖看各鄉鎮市區；再點一次進入該區頁面。", "Hover or tap the map for each township; tap again to open it.", "地図にカーソルを合わせるかタップで表示、もう一度押すとページへ。", "지도에 마우스를 올리거나 누르면 표시, 한 번 더 누르면 페이지로 이동.")}</p>'
            f'{town_map(cur_t, tmap, iy)}<p class="note">{L(f"{iy} 年綜合所得稅申報資料（{iy + 2} 年公布），以「納稅單位」（一份申報書，可能是一個人或一家人）計算。中位數＝排在正中間那一戶。澎湖、金門、馬祖不在地圖範圍，見下方表格。", f"Consolidated income tax returns for {iy} (published {iy + 2}), per tax filing unit (one return: a person or a household). Median = the unit in the middle. Penghu, Kinmen and Matsu are off the map; see the table below.", f"{iy}年分の総合所得税申告データ（{iy + 2}年公表）。「申告単位」（申告書1件、個人または世帯）ごと。中央値＝真ん中の申告単位。澎湖・金門・馬祖は地図外、下の表を参照。", f"{iy}년분 종합소득세 신고 자료({iy + 2}년 공표). '납세 단위'(신고서 1건, 개인 또는 가구) 기준. 중위수=가운데 단위. 펑후·진먼·마쭈는 지도 밖, 아래 표 참고.")}</p></div>'
            f'<div class="stack">{c4}{c5}{c6}</div></div></div></section>')

    path = "tax/"
    url = f"{SITE}/{PREFIX[LANG]}{path}"
    title = L(f"台灣稅收與所得：{span_label(y, m)}全國稅收、各鄉鎮市區所得中位數排名｜Taiwan Data 台灣數據",
              f"Taiwan Tax Revenue and Income by Township: {span_label(y, m)} | Taiwan Data",
              f"台湾の税収と所得：{span_label(y, m)}の税収、郷鎮市区別の所得中央値｜Taiwan Data",
              f"대만 세수와 소득: {span_label(y, m)} 세수, 향·진·시·구별 소득 중위수 | Taiwan Data")
    desc = L(f"{span_label(y, m)}全國稅收 {money(cur)}，比去年同期{'多' if up else '少'} {chs}。各稅目、歷年稅收與預算、證券交易稅；{iy} 年全台 {len(cur_t)} 個鄉鎮市區綜合所得中位數地圖與排名，每區可看各村里。資料來源：財政部。",
             f"Taiwan's tax revenue in {span_label(y, m)}: {money(cur)} ({'+' if up else '−'}{chs} year on year), by tax, versus budget, plus median income for all {len(cur_t)} townships in {iy}. Source: Ministry of Finance.",
             f"{span_label(y, m)}の台湾の税収は{money(cur)}（前年同期比{'+' if up else '−'}{chs}）。税目別、予算比、{iy}年の郷鎮市区別所得中央値の地図とランキング。出典：財政部。",
             f"{span_label(y, m)} 대만 세수 {money(cur)}(전년 동기 대비 {'+' if up else '−'}{chs}). 세목별, 예산 대비, {iy}년 향·진·시·구별 소득 중위수 지도와 순위. 출처: 재정부.")
    html_ = f"""{head(title, desc, url, "og.png", LANG, "/" + path)}
<body>
<style>{CSS}</style>
{nav(LANG, "/" + path)}
{hero}
<div class="w"><div class="cards">{c1}{c2}{c3}</div></div>
{fold1}
{sec2}
{fold2}
{foot()}
{JS}
</body>
</html>
"""
    d = Path(out) / PREFIX[LANG] / path
    d.mkdir(parents=True, exist_ok=True)
    (d / "index.html").write_text(html_, encoding="utf-8")
    return url


def town_page(out, head, nav, town, towns, villages, tmap):
    """各鄉鎮市區頁（中文）：歷年中位數、平均數，各村里排行。"""
    iy = max(towns)
    v = towns[iy][town]
    ranked = sorted(towns[iy], key=lambda t: -towns[iy][t]["median"])
    rank = ranked.index(town) + 1
    c = county_of(town)
    same = sorted([t for t in towns[iy] if county_of(t) == c], key=lambda t: -towns[iy][t]["median"])
    crank = same.index(town) + 1
    ys = [yy for yy in sorted(towns) if town in towns[yy] and yy >= BREAK]
    meds = [towns[yy][town]["median"] for yy in ys]
    means = [towns[yy][town]["mean"] for yy in ys]
    gm = pct(meds[-1], meds[0]) if len(meds) > 1 else 0
    name = f"{c}{town_short(town)}"
    lede = (f"{iy} 年{name}每戶所得中位數 {em(wan(v['median']))}，平均 {em(wan(v['mean']))}；"
            f"中位數全台第 {em(str(rank))} 高（共 {len(ranked)} 區），{c}第 {crank} 高。")
    kn = [(wan(v["median"]), "中位數"), (wan(v["mean"]), "平均數"), (f"{v['households']:,.0f}", "申報戶數")]
    kns = "".join(f'<div class="kn"><b>{a}</b><span>{b}</span></div>' for a, b in kn)
    chart = line_chart(ys, [("平均", "#9aa0a6", means), ("中位數", "#1f7ad6", meds)], 10, "萬元", w=760, h=260)
    vil = sorted(villages.get(town, []), key=lambda x: -x["median"])
    mx = vil[0]["median"] if vil else 1
    vrows = "".join(
        f'<tr><td>{i + 1}</td><td>{e(x["name"])}</td><td class="n">{x["median"] / 10:,.1f}</td><td style="min-width:120px"><span style="display:block;height:10px;border-radius:3px;background:#1f7ad6;width:{x["median"] / mx * 100:.0f}%"></span></td>'
        f'<td class="n">{x["mean"] / 10:,.1f}</td><td class="n">{x["q1"] / 10:,.1f}</td><td class="n">{x["q3"] / 10:,.1f}</td><td class="n">{x["households"]:,.0f}</td></tr>'
        for i, x in enumerate(vil))
    others = "".join(f'<a href="{town_url(t)}">{e(town_short(t))}</a>' for t in same if t != town)
    hi_v = f"最高是{vil[0]['name']}（{wan(vil[0]['median'])}），最低是{vil[-1]['name']}（{wan(vil[-1]['median'])}）。" if len(vil) > 1 else ""
    body = (f'<section class="lt"><div class="w hero"><p class="q" style="color:#676d73">{c} › 綜合所得</p>'
            f'<h1 class="lede">{lede}</h1><div class="kns">{kns}</div>'
            f'<div class="card"><h2>{name}所得中位數 {ys[0]}～{ys[-1]} 年{"增加" if gm >= 0 else "減少"} {em(f"{abs(gm):.0f}%", gm < 0)}</h2>'
            f'<div class="legend"><span><i style="background:#1f7ad6"></i>中位數</span><span><i style="background:#9aa0a6"></i>平均數</span></div>{chart}'
            f'<p class="note">單位：萬元。平均數會被少數高所得拉高，中位數比較接近一般家戶。</p></div>'
            f'<div class="card" style="margin-top:16px"><h2>{len(vil)} 個村里的所得中位數：{hi_v}</h2><div style="overflow-x:auto"><table class="tb">'
            f'<tr><th></th><th>村里</th><th class="n">中位數</th><th></th><th class="n">平均數</th><th class="n">第一四分位</th><th class="n">第三四分位</th><th class="n">申報戶數</th></tr>{vrows}</table></div>'
            f'<p class="note">單位：萬元。第一、第三四分位數＝由低到高排在第 25%、第 75% 的那一戶。</p></div>'
            f'<div class="card" style="margin-top:16px"><h2>{c}其他鄉鎮市區</h2><div class="cty">{others}</div>'
            f'<p class="note"><a href="/tax/">← 回台灣稅收與所得</a></p></div></div></section>')
    path = f"tax/town/{town}/"
    url = f"{SITE}/tax/town/{quote(town)}/"
    title = f"{name}所得中位數 {wan(v['median'])}：各村里綜合所得排名（{iy} 年）｜Taiwan Data 台灣數據"
    desc = f"{iy} 年{name}綜合所得中位數 {wan(v['median'])}、平均 {wan(v['mean'])}，全台第 {rank} 高。{len(vil)} 個村里所得中位數排名與歷年變化。資料來源：財政部財政資訊中心。"
    html_ = f"""{head(title, desc, url, "og.png", "zh")}
<body>
<style>{CSS}</style>
{nav("zh", "")}
{body}
{foot()}
</body>
</html>
"""
    d = Path(out) / path
    d.mkdir(parents=True, exist_ok=True)
    (d / "index.html").write_text(html_, encoding="utf-8")
    return url


def build(out, head, nav, nav_zh_only=None):
    """nav(lang, path)：頂欄。回傳 sitemap 網址。"""
    global LANG
    if not (TAX / "monthly.csv").exists() or not (INC / "towns.csv").exists():
        return []
    data = load()
    urls = []
    for lang in ("zh", "en", "ja", "ko"):
        LANG = lang
        bb.set_lang(lang)
        urls.append(page(out, head, nav, *data))
    LANG = "zh"
    bb.set_lang("zh")
    monthly, budget, towns, villages, tmap = data
    for town in towns[max(towns)]:
        urls.append(town_page(out, head, nav_zh_only or nav, town, towns, villages, tmap))
    return urls
