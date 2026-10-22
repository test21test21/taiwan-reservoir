"""今日電力頁：/power/（中文）、/en/power/（英文）、/jp/power/（日文），數字和圖直接寫進 HTML。

資料：data/power/（scripts/fetch_power.py 從台電開放資料整理）
build_pages.py 部署時呼叫 build(out, head, nav)。
"""
import csv
import html
import json
import re
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

import build_births as bb
import i18n_ja

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data/power"
SITE = "https://taiwandata.info"
e = html.escape
LANG, EN, JA = "zh", False, False
MON = bb.MON
PREFIX = bb.PREFIX
WEEK = "一二三四五六日"
WEEK_JA = "月火水木金土日"
WEEK_EN = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# 發電類別：(代號, 中文, 英文, 日文, 顏色)，圖和長條的順序
FUELS = [
    ("lng", "燃氣", "Gas (LNG)", "LNG火力", "#e8833a"),
    ("coal", "燃煤", "Coal", "石炭火力", "#6f6f6f"),
    ("nuclear", "核能", "Nuclear", "原子力", "#d64545"),
    ("cogen", "汽電共生", "Cogeneration", "コージェネ", "#a87b4f"),
    ("oil", "燃油", "Oil", "石油火力", "#8c5a9e"),
    ("solar", "太陽能", "Solar", "太陽光", "#f2c230"),
    ("wind", "風力", "Wind", "風力", "#2fb3a3"),
    ("hydro", "水力", "Hydro", "水力", "#2f7fd1"),
    ("other", "其他再生能源", "Other renewables", "その他再エネ", "#6dbb4a"),
    ("storage", "儲能", "Storage", "蓄電（揚水・電池）", "#c25b9a"),
]
RENEW = {"solar", "wind", "hydro", "other"}

# 台電供電燈號（依備轉容量率、備轉容量）
LIGHTS = [
    ("G", "綠燈", "供電充裕", "Green", "Ample supply", "#2e9e5b", "緑", "供給に余裕"),
    ("Y", "黃燈", "供電吃緊", "Yellow", "Tight supply", "#e2b600", "黄", "需給ひっ迫"),
    ("O", "橘燈", "供電警戒", "Orange", "Supply warning", "#f08a24", "橙", "需給警戒"),
    ("R", "紅燈", "限電警戒", "Red", "Rationing warning", "#d93c3c", "赤", "電力制限警戒"),
    ("B", "黑燈", "限電準備", "Black", "Rationing ready", "#222222", "黒", "電力制限準備"),
]

# 主要電廠英文名；沒列到的英文頁顯示中文
PLANTS_EN = {
    "大潭": "Datan", "台中": "Taichung", "興達": "Hsinta", "林口": "Linkou", "大林": "Talin", "通霄": "Tunghsiao",
    "南部": "Nanbu", "和平": "Ho-Ping", "麥寮": "Mailiao", "協和": "Hsieh-ho", "海湖": "Haihu", "新桃": "Hsin-Tao",
    "國光": "Kuo Kuang", "星彰": "Star Energy Changhua", "星元": "Star Energy Yuan", "嘉惠": "Chiahui", "豐德": "Fengde",
    "汽電共生": "Cogeneration plants", "核二": "Kuosheng (gas turbines)", "核三": "Maanshan (gas turbines)",
    "澎湖尖山": "Penghu Jianshan", "金門塔山": "Kinmen Tashan", "馬祖珠山": "Matsu Zhushan", "離島其它": "Other islands",
    "明潭": "Mingtan", "大觀二": "Takuan II", "大觀一": "Takuan I", "德基": "Techi", "青山": "Chingshan", "谷關": "Kukuan",
    "天輪": "Tienlun", "馬鞍": "Ma-an", "卓蘭": "Zhuolan", "萬大": "Wanta", "鉅工": "Chukung", "翡翠": "Feitsui",
    "石門": "Shihmen", "曾文": "Zengwen", "電池": "Batteries", "其它購電太陽能": "Other solar (purchased)",
    "其它購電風力": "Other wind (purchased)", "彰濱光": "Changbin Solar", "南鹽光": "Nanyan Solar",
}

# 日文固定文字：依英文查（tr 沒給日文時用）
JA_TXT = {
    " (": "（", ")": "）", " (solar ": "（太陽光 ", " · coal ": "・石炭 ", " · gas ": "・LNG ", " · renewables ": "・再エネ ",
    ", renewables ": "、再エネ ", ": ": "：", ": operating reserve ": "：予備率 ", ": peak demand ": "：最大電力 ",
    " (same day last year ": "（前年同日 ", "1 year": "1年", "90 days": "90日", "All": "すべて", "h": "時",
    "Daily operating reserve at peak": "日別のピーク時予備率", "Daily peak demand": "日別最大電力",
    "Electricity used each month": "月別の電力使用量", "Generation mix by hour today": "今日の時間別電源構成",
    "Homes and businesses": "民生用（家庭・業務）", "Industry": "産業用",
    "Hover or tap a bar for each month (TWh)": "棒にカーソルを合わせるかタップすると月別の数値を表示（単位：億kWh）",
    "Hover or tap a bar for that hour (GW)": "棒にカーソルを合わせるかタップすると時間別の数値を表示（単位：万kW）",
    "Hover or tap the chart to see each day (GW)": "グラフにカーソルを合わせるかタップすると日別の数値を表示（単位：万kW）",
    "Hover or tap the chart to see each day": "グラフにカーソルを合わせるかタップすると日別の数値を表示",
    "Lights follow Taipower’s rules: reserve margin 10% or more is green, 6–10% yellow, under 6% orange; reserve of 0.9 GW or less is red, 0.5 GW or less black. Figures in GW.":
        "ランプは台湾電力の基準による：予備率10%以上は緑、6～10%は黄、6%未満は橙、予備力90万kW以下は赤、50万kW以下は黒。単位：万kW。",
    "Load": "稼働率", "Monthly industrial and residential use": "月別の産業用・民生用電力",
    "Next 7 days (Taipower forecast)": "今後1週間（台湾電力の見通し）", "Operating reserve each day": "日別の予備率",
    "Output (GW)": "出力（万kW）", "Past year": "直近1年", "Peak demand each day": "日別の最大電力", "Peak demand": "最大電力",
    "Period": "期間", "Plant": "発電所", "Power demand right now": "いまの電力需要", "Power plants right now": "発電所別のいまの出力",
    "Power supply light": "電力需給ランプ", "Reserve ": "予備力 ", "Reserve": "予備率",
    "Reserve margin at each day’s peak (Taipower actuals). Dashed lines mark the yellow (10%) and orange (6%) thresholds.":
        "毎日のピーク時の予備率（台湾電力の実績）。破線は黄（10%）と橙（6%）の境目。",
    "Same day a year earlier": "前年同日", "Sum of Taipower daily industrial and residential use; complete months only.":
        "台湾電力の日別の産業用・民生用電力量の合計。データがそろった月のみ。",
    "Sum of net output of all generating units. Taipower updates every 10 minutes; this page refreshes hourly. Private plants are included with their fuel type.":
        "全発電機の送電端出力の合計。台湾電力は10分ごとに更新、このページは1時間ごとに更新。民間発電所（IPP）は同じ燃料に含む。",
    "Today’s generation, hour by hour": "今日の時間別発電量", "Type": "種類",
    "Units at the same plant are combined. Load = output ÷ installed capacity.": "同じ発電所の発電機は合算。稼働率＝出力÷設備容量。",
    "We record the generation mix every hour; the chart appears once today has 3 hours of records.":
        "当サイトは1時間ごとに電源構成を記録しています。今日の記録が3時間分たまるとグラフを表示します。",
    "operating reserve": "予備率",
}


def set_lang(lang):
    global LANG, EN, JA
    LANG, EN, JA = lang, lang == "en", lang == "ja"
    bb.set_lang(lang)


def tr(zh, en, ja=None):
    """日文沒給的話用 JA_TXT 依英文查（固定文字）。"""
    if JA:
        return ja if ja is not None else JA_TXT[en]
    return en if EN else zh


def fuel_name(k):
    for key, zh, en, ja, _ in FUELS:
        if key == k:
            return en if EN else ja if JA else zh
    return k


def gw(mw, d=1):
    """發電量：中文寫萬瓩、日文寫万kW、英文寫 GW（台電、新聞都用萬瓩）。"""
    return f"{mw / 1000:,.{d}f}" if EN else f"{mw / 10:,.{d}f}"


def unit():
    return tr("萬瓩", "GW", "万kW")


def light_of(rate, reserve):
    """台電燈號：備轉容量率 10% 以上綠、6～10% 黃、不到 6% 橘；備轉容量 90 萬瓩以下紅、50 萬瓩以下黑。"""
    if reserve is not None and reserve <= 50:
        return LIGHTS[4]
    if reserve is not None and reserve <= 90:
        return LIGHTS[3]
    if rate >= 10:
        return LIGHTS[0]
    if rate >= 6:
        return LIGHTS[1]
    return LIGHTS[2]


def lamp(li):
    return f'<i class="lamp" style="background:{li[5]}"></i>'


def light_text(li):
    return f"{li[3]} · {li[4]}" if EN else f"{li[6]}・{li[7]}" if JA else f"{li[1]}・{li[2]}"


def ddate(d, week=True):
    w = WEEK_EN[d.weekday()] if EN else WEEK_JA[d.weekday()] if JA else WEEK[d.weekday()]
    if JA:
        return f"{d.month}/{d.day}（{w}）" if week else f"{d.year}年{d.month}月{d.day}日"
    if EN:
        return f"{w} {MON[d.month - 1]} {d.day}" if week else f"{MON[d.month - 1]} {d.day}, {d.year}"
    return f"{d.month}/{d.day}（{w}）" if week else f"{d.year} 年 {d.month} 月 {d.day} 日"


def read(path):
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def fl(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def load():
    latest = json.loads((DATA / "latest.json").read_text(encoding="utf-8"))
    reserve = [(date.fromisoformat(r["date"]), fl(r["reserve"]), fl(r["rate"])) for r in read(DATA / "reserve.csv") if fl(r["rate"]) is not None]
    daily = [(date.fromisoformat(r["date"]), {k: fl(v) for k, v in r.items() if k != "date"}) for r in read(DATA / "daily.csv")]
    daily = [(d, x) for d, x in daily if x.get("peak")]
    forecast = [(date.fromisoformat(r["date"]), {k: fl(v) for k, v in r.items() if k != "date"}) for r in read(DATA / "forecast.csv")]
    hourly = []
    for p in sorted((DATA / "hourly").glob("*.csv")):
        hourly += read(p)
    return latest, reserve, daily, forecast, hourly


def plant_of(name):
    name = re.sub(r"\(註\d+\)", "", name).strip()
    base = re.sub(r"(新)?(CC|GT)?#.*$", "", name)
    base = re.sub(r"Gas.*$", "", base).strip()
    return base or name


def plants(units):
    agg = {}
    for u in units:
        if u["fuel"] == "storage_load":
            continue
        k = (plant_of(u["name"]), u["fuel"])
        a = agg.setdefault(k, {"name": k[0], "fuel": k[1], "mw": 0.0, "cap": 0.0, "n": 0, "notes": set()})
        a["mw"] += u["mw"] or 0
        a["cap"] += u["cap"] or 0
        a["n"] += 1
        if u["note"]:
            a["notes"].add(u["note"])
    return sorted(agg.values(), key=lambda a: -a["mw"])


CSS = """
[hidden] { display:none !important; }
.wrap { max-width:1840px; padding-inline:max(16px, env(safe-area-inset-left)) max(16px, env(safe-area-inset-right)); }
.top, .grid { display:grid; gap:12px; align-items:start; }
.top > .box, .grid > .box { margin-top:12px; min-width:0; }
@media (min-width:860px) { .top, .grid { grid-template-columns:1fr 1fr; column-gap:16px; row-gap:0; } }
@media (min-width:1360px) { .grid { grid-template-columns:1fr 1fr 1fr; } .grid > .wide { grid-column:span 2; } }
.hero .v { font-size:clamp(34px,9vw,56px); font-weight:700; line-height:1.1; white-space:nowrap; }
.hero .v small { font-size:16px; color:var(--muted); font-weight:500; margin-left:4px; }
.hero .sub { font-size:14px; color:var(--muted); }
.hero .sub b { font-weight:500; color:var(--fg); }
.chart.bd { max-height:none; }
.bd .line.r { stroke:var(--fg); stroke-width:2; }
.bd .line.b { stroke:#1f7ad6; }
.bd .line.y1 { stroke:#2e9e5b; stroke-width:2; }
.bd .dot.b { fill:#1f7ad6; }
.bd .th { stroke-width:1.5; stroke-dasharray:4 4; }
.bd .thl { font-size:11px; font-weight:500; }
.bd .hit { fill:transparent; }
.bd .hit:hover, .bd .hit:focus { fill:var(--fg); fill-opacity:.06; outline:none; }
.bd .lab { font-size:12px; font-weight:700; fill:var(--fg); }
.legend { flex-wrap:wrap; }
.legend .sq { width:12px; height:12px; border-radius:3px; display:inline-block; margin-left:8px; }
.legend .sq:first-child { margin-left:0; }
.legend .k.b { border-color:#1f7ad6; }
.legend .k.y1 { border-color:#2e9e5b; }
.legend .k.r { border-color:var(--fg); }
.tip { font-size:13px; color:var(--muted); margin:2px 0 0; min-height:1.6em; }
.note { font-size:13px; color:var(--muted); margin:8px 0 0; }
.seg { display:inline-flex; flex-wrap:wrap; border:1px solid var(--line); border-radius:999px; padding:2px; gap:2px; margin:2px 6px 6px 0; }
.seg button { font:inherit; font-size:14px; border:0; background:none; color:var(--muted); padding:4px 11px; white-space:nowrap; border-radius:999px; cursor:pointer; }
.seg button[aria-pressed="true"] { background:var(--fg); color:var(--bg); }
.mix { display:flex; height:22px; border-radius:6px; overflow:hidden; margin:14px 0 10px; }
.mix span { display:block; height:100%; }
.hbars { list-style:none; margin:4px 0 0; padding:0; display:grid; gap:6px; }
.hbars li { display:grid; grid-template-columns:7.5em 1fr auto; align-items:center; gap:8px; font-size:14px; }
html[lang="en"] .hbars li, html[lang="ja"] .hbars li { grid-template-columns:10em 1fr auto; }
.hbars .nm { display:flex; align-items:center; gap:6px; overflow:hidden; white-space:nowrap; }
.hbars .nm i { width:10px; height:10px; border-radius:3px; flex:none; }
.hbars .track { height:14px; background:var(--chip); border-radius:4px; overflow:hidden; }
.hbars .fill { display:block; height:100%; border-radius:4px; }
.hbars .val { text-align:right; white-space:nowrap; min-width:7.5em; }
.hbars .val small { color:var(--muted); margin-left:6px; display:inline-block; min-width:3.6em; text-align:right; }
.lamp { width:14px; height:14px; border-radius:50%; display:inline-block; flex:none; box-shadow:0 0 0 1px rgba(0,0,0,.08) inset; }
.lightnow { display:flex; align-items:center; gap:10px; margin-top:6px; }
.lightnow .lamp { width:28px; height:28px; }
.lightnow b { font-size:20px; }
.fc { margin-top:14px; }
.fc td, .fc th { white-space:nowrap; }
.fc td .lamp { vertical-align:-2px; margin-right:6px; }
.pl td:nth-child(2) i { width:10px; height:10px; border-radius:3px; display:inline-block; margin-right:6px; vertical-align:0; }
.pl td.nt { color:var(--muted); font-size:13px; white-space:normal; }
.pl td, .pl th { white-space:nowrap; }
.pl td.r { color:var(--muted); width:2.2em; }
.plwrap { overflow-x:auto; }
@media (max-width:520px) { .pl .nt, .fc .rs { display:none; } }
details.more summary { margin-top:8px; font-size:14px; font-weight:500; color:var(--fg); }
"""

JS = """<script>
(function () {
  document.querySelectorAll("svg.bd").forEach(function (svg) {
    var tip = svg.closest(".box").querySelector(".tip"), def = tip.textContent;
    svg.querySelectorAll(".hit").forEach(function (h) {
      function on() { tip.textContent = h.getAttribute("data-tip"); }
      h.addEventListener("mouseenter", on); h.addEventListener("focus", on); h.addEventListener("click", on);
      h.addEventListener("mouseleave", function () { tip.textContent = def; });
    });
  });
  document.querySelectorAll("[data-swap]").forEach(function (grp) {
    var box = grp.closest(".box");
    grp.querySelectorAll("button").forEach(function (b) {
      b.addEventListener("click", function () {
        grp.querySelectorAll("button").forEach(function (x) { x.setAttribute("aria-pressed", x === b); });
        box.querySelectorAll("[data-pane]").forEach(function (p) { p.hidden = p.getAttribute("data-pane") !== b.getAttribute("data-k"); });
      });
    });
  });
})();
</script>"""

W, H, L, R, T, B = bb.W, bb.H, bb.L, bb.R, bb.T, bb.B


def seg(attrs, opts, cur):
    return (f'<div class="seg" role="group" {attrs}>' + "".join(
        f'<button type="button" data-k="{k}" aria-pressed="{"true" if k == cur else "false"}">{t}</button>' for k, t in opts) + "</div>")


def reserve_chart(rows):
    """每日尖峰備轉容量率：一條線，加 10%、6% 兩條燈號界線。"""
    vals = [r for _, _, r in rows]
    lo, hi, step = bb.nice_scale(0, max(vals + [12]), zero=True)
    n = len(rows)
    X = lambda i: L + (W - L - R) * i / max(1, n - 1)
    Y = lambda v: T + (H - T - B) * (hi - v) / (hi - lo)
    svg, g = "", lo
    while g <= hi + 1e-9:
        svg += (f'<line x1="{L}" x2="{W - R}" y1="{Y(g):.1f}" y2="{Y(g):.1f}" class="g"/>'
                f'<text x="{L - 5}" y="{Y(g) + 4:.1f}" text-anchor="end">{g:g}%</text>')
        g += step
    for v, li in ((10, LIGHTS[1]), (6, LIGHTS[2])):
        svg += (f'<line x1="{L}" x2="{W - R}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" class="th" stroke="{li[5]}"/>'
                f'<text x="{W - R - 2}" y="{Y(v) - 3:.1f}" text-anchor="end" class="thl" fill="{li[5]}">{v}%</text>')
    svg += '<path d="' + " ".join(f'{"M" if i == 0 else "L"}{X(i):.1f},{Y(r):.1f}' for i, (_, _, r) in enumerate(rows)) + '" class="line r"/>'
    for i, (d, res, r) in enumerate(rows):  # 低於 10% 的日子畫燈號顏色的點
        li = light_of(r, res)
        if li[0] != "G":
            svg += f'<circle cx="{X(i):.1f}" cy="{Y(r):.1f}" r="3.5" fill="{li[5]}"/>'
    k = n - 1
    labels = [(0, f"{rows[0][0].year}/{rows[0][0].month}")]
    if n > 1:
        labels.append((k, f"{rows[-1][0].month}/{rows[-1][0].day}"))
    if n > 200:
        for i, (d, _, _) in enumerate(rows):
            if d.month == 1 and d.day == 1 and 30 < i < k - 30:
                labels.append((i, str(d.year)))
    svg += bb.xlabels(X, sorted(labels))
    cw = (X(1) - X(0)) if n > 1 else W - L - R
    svg += "".join(
        f'<rect x="{X(i) - cw / 2:.1f}" y="{T}" width="{max(cw, .5):.1f}" height="{H - T - B}" class="hit" '
        f'data-tip="{e(ddate(d, False))}{tr("：備轉容量率 ", ": operating reserve ")}{r:.2f}%'
        f'{tr("（", " (")}{gw(res * 10) if res is not None else "–"} {unit()}{tr("）", ")")}・{e(light_text(light_of(r, res)))}"/>'
        for i, (d, res, r) in enumerate(rows))
    return svg


def peak_chart(daily):
    """每日尖峰負載：最近一年（藍）和前一年同一天（綠）。"""
    last = daily[-1][0]
    by = {d: x["peak"] for d, x in daily}
    days = [last - timedelta(days=i) for i in range(364, -1, -1)]
    days = [d for d in days if d in by]
    if len(days) < 30:
        return ""
    cur = [by.get(d) for d in days]

    def ly(d):
        try:
            return by.get(d.replace(year=d.year - 1))
        except ValueError:
            return None
    prev = [ly(d) for d in days]
    series = [("y1", prev), ("b", cur)] if any(prev) else [("b", cur)]
    labels = [(0, f"{days[0].year}/{days[0].month}"), (len(days) - 1, f"{days[-1].month}/{days[-1].day}")]
    tips = [f"{ddate(d, False)}{tr('：尖峰用電 ', ': peak demand ')}{gw(v * 10)} {unit()}"
            + (f"{tr('（去年同一天 ', ' (same day last year ')}{gw(p * 10)}{tr('）', ')')}" if p else "")
            for d, v, p in zip(days, cur, prev)]
    if EN:
        series = [(c, [v / 100 if v else None for v in s]) for c, s in series]
    return bb.lines_chart(len(days), series, labels, tips)


def month_use(daily):
    """每月用電量：工業（下）＋民生（上），單位億度。"""
    m = defaultdict(lambda: [0.0, 0.0, 0])
    def fix(v):  # 台電原始資料偶爾漏小數點（例如 37069 應為 370.69 百萬度）
        return v / 100 if v and v > 2000 else (v or 0)
    for d, x in daily:
        k = f"{d.year}-{d.month:02d}"
        m[k][0] += fix(x.get("industry"))
        m[k][1] += fix(x.get("home"))
        m[k][2] += 1
    months = [k for k in sorted(m) if m[k][2] >= 28]
    if len(months) < 3:
        return "", None
    tot = [(m[k][0] + m[k][1]) / 100 for k in months]  # 百萬度 → 億度
    lo, hi, step = bb.nice_scale(0, max(tot), zero=True)
    n = len(months)
    slot = (W - L - R) / n
    bw = max(2, slot - 3)
    X = lambda i: L + slot * (i + .5)
    Y = lambda v: T + (H - T - B) * (hi - v) / (hi - lo)
    svg = ""
    g = lo
    while g <= hi + 1e-9:
        lab = f"{g / 10:g}" if EN else f"{g:g}"  # 英文：十億度（TWh）；中文、日文：億度（億kWh）
        svg += (f'<line x1="{L}" x2="{W - R}" y1="{Y(g):.1f}" y2="{Y(g):.1f}" class="g"/>'
                f'<text x="{L - 5}" y="{Y(g) + 4:.1f}" text-anchor="end">{lab}</text>')
        g += step
    for i, k in enumerate(months):
        ind, home = m[k][0] / 100, m[k][1] / 100
        x = X(i) - bw / 2
        svg += (f'<rect x="{x:.1f}" y="{Y(ind):.1f}" width="{bw:.1f}" height="{Y(0) - Y(ind):.1f}" fill="#6f6f6f"/>'
                f'<rect x="{x:.1f}" y="{Y(ind + home):.1f}" width="{bw:.1f}" height="{max(0, Y(ind) - Y(ind + home) - 1):.1f}" rx="2" fill="#1f7ad6"/>')
    labels = [(i, f"{int(k[:4])}/{int(k[5:])}") for i, k in enumerate(months) if i in (0, n - 1) or (k[5:] == "01" and 2 <= i <= n - 3)]
    svg += bb.xlabels(X, labels)

    def lab(k):
        return bb.ym_label(k)
    svg += "".join(
        f'<rect x="{X(i) - slot / 2:.1f}" y="{T}" width="{slot:.1f}" height="{H - T - B}" class="hit" tabindex="0" data-tip="'
        + (f"{lab(k)}: {(m[k][0] + m[k][1]) / 1000:.1f} TWh (industry {m[k][0] / 1000:.1f}, homes and businesses {m[k][1] / 1000:.1f})" if EN
           else f"{lab(k)}：{(m[k][0] + m[k][1]) / 100:,.1f} 億kWh（産業用 {m[k][0] / 100:,.1f}、民生用 {m[k][1] / 100:,.1f}）" if JA
           else f"{lab(k)}：{(m[k][0] + m[k][1]) / 100:,.1f} 億度（工業 {m[k][0] / 100:,.1f}、民生 {m[k][1] / 100:,.1f}）")
        + '"/>' for i, k in enumerate(months))
    return svg, months[-1]


def today_chart(hourly, day):
    """今天每小時的發電組成（堆疊長條）。"""
    rows = [r for r in hourly if r["time"][:10] == day]
    if len(rows) < 3:
        return ""
    keys = [k for k, *_ in FUELS]
    vals = [{k: max(0.0, fl(r.get(k)) or 0) for k in keys} for r in rows]
    tot = [sum(v.values()) for v in vals]
    lo, hi, step = bb.nice_scale(0, max(tot) / (1000 if EN else 10), zero=True)
    slot = (W - L - R) / 24
    bw = max(2, slot - 2)
    X = lambda h: L + slot * (h + .5)
    Y = lambda v: T + (H - T - B) * (hi - v) / (hi - lo)
    sc = (lambda mw: mw / 1000) if EN else (lambda mw: mw / 10)
    svg = ""
    g = lo
    while g <= hi + 1e-9:
        svg += (f'<line x1="{L}" x2="{W - R}" y1="{Y(g):.1f}" y2="{Y(g):.1f}" class="g"/>'
                f'<text x="{L - 5}" y="{Y(g) + 4:.1f}" text-anchor="end">{g:,g}</text>')
        g += step
    for r, v, t in zip(rows, vals, tot):
        h = int(r["time"][11:13])
        acc = 0.0
        for k, zh, en, ja, c in FUELS:
            if v[k] <= 0:
                continue
            y0, y1 = Y(sc(acc)), Y(sc(acc + v[k]))
            svg += f'<rect x="{X(h) - bw / 2:.1f}" y="{y1:.1f}" width="{bw:.1f}" height="{max(0, y0 - y1):.1f}" fill="{c}"/>'
            acc += v[k]
        ren = sum(v[k] for k in RENEW)
        tip = (f"{r['time'][11:16]}{tr('：發電 ', ': ')}{gw(t)} {unit()}{tr('，再生能源 ', ', renewables ')}{ren / t * 100:.1f}%"
               + tr("（太陽能 ", " (solar ") + f"{v['solar'] / t * 100:.1f}%" + tr("）", ")"))
        svg += f'<rect x="{X(h) - slot / 2:.1f}" y="{T}" width="{slot:.1f}" height="{H - T - B}" class="hit" tabindex="0" data-tip="{e(tip)}"/>'
    svg += bb.xlabels(X, [(0, "0"), (6, "6"), (12, "12"), (18, "18"), (23, "23" + tr(" 時", "h"))])
    return svg


def page(out, head, nav, latest, reserve, daily, forecast, hourly):
    units = latest["units"]
    t = latest["time"]
    tday = date.fromisoformat(t[:10])
    tot = defaultdict(float)
    for u in units:
        tot[u["fuel"]] += u["mw"] or 0
    gen = sum(v for k, v in tot.items() if k != "storage_load")
    load = gen + tot.get("storage_load", 0)
    ren = sum(tot[k] for k in RENEW)
    order = sorted([f for f in FUELS if tot.get(f[0], 0) > 0.5], key=lambda f: -tot[f[0]])

    when = (f"{MON[tday.month - 1]} {tday.day}, {t[11:16]}" if EN else f"{tday.month}月{tday.day}日 {t[11:16]}" if JA
            else f"{tday.month} 月 {tday.day} 日 {t[11:16]}")
    mix = "".join(f'<span style="width:{tot[k] / gen * 100:.2f}%;background:{c}" title="{e(fuel_name(k))}"></span>' for k, _, _, _, c in order)
    bars = "".join(
        f'<li><span class="nm"><i style="background:{c}"></i>{e(fuel_name(k))}</span>'
        f'<span class="track"><span class="fill" style="width:{tot[k] / tot[order[0][0]] * 100:.1f}%;background:{c}"></span></span>'
        f'<span class="val">{gw(tot[k], 2 if EN else 1)}<small>{tot[k] / gen * 100:.1f}%</small></span></li>' for k, _, _, _, c in order)
    charge = -tot.get("storage_load", 0)
    hero = (f'<section class="box hero"><h2>{tr("現在用電", "Power demand right now")}</h2>'
            f'<div class="v">{gw(load)}<small>{unit()}</small></div>'
            f'<div class="sub">{when}{tr("・再生能源 ", " · renewables ")}<b>{ren / gen * 100:.1f}%</b>'
            f'{tr("・燃氣 ", " · gas ")}<b>{tot["lng"] / gen * 100:.1f}%</b>{tr("・燃煤 ", " · coal ")}<b>{tot["coal"] / gen * 100:.1f}%</b></div>'
            f'<div class="mix" aria-hidden="true">{mix}</div><ul class="hbars">{bars}</ul>'
            + (f'<p class="note">{tr(f"另有 {gw(charge)} 萬瓩用來替儲能充電（抽蓄、電池），已從用電扣除。", f"Another {gw(charge, 2)} GW is charging storage (pumped hydro, batteries) and is not counted as demand.",
                                      f"このほか {gw(charge)} 万kW を蓄電（揚水・電池）の充電に使っており、需要からは除いています。")}</p>' if charge > 0.5 else "")
            + f'<p class="note">{tr("各類機組淨發電量加總，台電每 10 分鐘更新，本站每小時抓一次。民營電廠併入同燃料。", "Sum of net output of all generating units. Taipower updates every 10 minutes; this page refreshes hourly. Private plants are included with their fuel type.")}</p></section>')

    # 供電燈號：昨天實際、未來一週預估
    light_box = ""
    if reserve:
        d, res, r = reserve[-1]
        li = light_of(r, res)
        fc_rows = "".join(
            f'<tr><td>{ddate(fd)}</td><td>{lamp(light_of(x["rate"], x.get("reserve")))}{x["rate"]:.2f}%</td>'
            f'<td class="n">{gw((x.get("peak") or 0) * 10, 0 if not EN else 1)}</td><td class="n rs">{gw((x.get("reserve") or 0) * 10, 0 if not EN else 2)}</td></tr>'
            for fd, x in forecast if fd > d and x.get("rate") is not None)
        light_box = (
            f'<section class="box hero"><h2>{tr("供電燈號", "Power supply light")}</h2>'
            f'<div class="sub">{tr(f"{ddate(d)}尖峰時段", f"Peak hours, {ddate(d)}", f"{ddate(d)}のピーク時")}</div>'
            f'<div class="lightnow">{lamp(li)}<b>{e(light_text(li))}</b></div>'
            f'<div class="v" style="margin-top:6px">{r:.2f}<small>% {tr("備轉容量率", "operating reserve")}</small></div>'
            f'<div class="sub">{tr("備轉容量 ", "Reserve ")}<b>{gw(res * 10)}</b> {unit()}</div>'
            + (f'<table class="fc"><thead><tr><th>{tr("未來一週（台電預估）", "Next 7 days (Taipower forecast)")}</th><th>{tr("備轉容量率", "Reserve")}</th>'
               f'<th class="n">{tr("尖峰用電", "Peak demand")}</th><th class="n rs">{tr("備轉容量", "Reserve", "予備力")}</th></tr></thead><tbody>{fc_rows}</tbody></table>' if fc_rows else "")
            + '<p class="note">' + "　".join(f'{lamp(x)} {x[3] if EN else x[6] if JA else x[1]}' for x in LIGHTS) + "</p>"
            + f'<p class="note">{tr("燈號依台電標準：備轉容量率 10% 以上綠燈、6～10% 黃燈、6% 以下橘燈；備轉容量 90 萬瓩以下紅燈、50 萬瓩以下黑燈。單位：萬瓩。", "Lights follow Taipower’s rules: reserve margin 10% or more is green, 6–10% yellow, under 6% orange; reserve of 0.9 GW or less is red, 0.5 GW or less black. Figures in GW.")}</p></section>')

    blocks = []
    if reserve:
        opts, panes = [], ""
        for key, label, days in (("90", tr("90 天", "90 days"), 90), ("365", tr("1 年", "1 year"), 365), ("all", tr("全部", "All"), 99999)):
            rows = [x for x in reserve if x[0] > reserve[-1][0] - timedelta(days=days)]
            opts.append((key, label))
            panes += (f'<svg class="chart bd" viewBox="0 0 {W} {H}" role="img" data-pane="{key}"{"" if key == "90" else " hidden"} '
                      f'aria-label="{e(tr("每日尖峰備轉容量率", "Daily operating reserve at peak"))}">{reserve_chart(rows)}</svg>')
        blocks.append(f'<section class="box"><h2>{tr("每天的備轉容量率", "Operating reserve each day")}</h2>'
                      + seg('data-swap aria-label="' + tr("期間", "Period") + '"', opts, "90")
                      + f'<p class="tip">{tr("滑過或點圖看每天數字", "Hover or tap the chart to see each day")}</p>{panes}'
                      + f'<p class="note">{tr("每天用電尖峰時段的備轉容量率（台電公布的實績）。虛線是黃燈（10%）和橘燈（6%）的界線。", "Reserve margin at each day’s peak (Taipower actuals). Dashed lines mark the yellow (10%) and orange (6%) thresholds.")}</p></section>')

    tc = today_chart(hourly, t[:10])
    leg = "".join(f'<span class="sq" style="background:{c}"></span>{e(fuel_name(k))}' for k, _, _, _, c in FUELS if tot.get(k, 0) > 0.5)
    blocks.append(
        f'<section class="box"><h2>{tr("今天每小時的發電", "Today’s generation, hour by hour")}</h2>'
        + (f'<p class="legend">{leg}</p><p class="tip">{tr("滑過或點長條看每小時數字（單位：萬瓩）", "Hover or tap a bar for that hour (GW)")}</p>'
           f'<svg class="chart bd" viewBox="0 0 {W} {H}" role="img" aria-label="{e(tr("今天每小時發電組成", "Generation mix by hour today"))}">{tc}</svg>' if tc
           else f'<p class="note">{tr("本站從 2026 年 10 月起每小時記錄一次各類發電量，今天記錄滿 3 個小時後這裡會出現圖表。", "We record the generation mix every hour; the chart appears once today has 3 hours of records.")}</p>')
        + "</section>")

    if daily:
        pc = peak_chart(daily)
        if pc:
            has_ly = 'class="line y1"' in pc
            leg = (f'<p class="legend"><span class="k b"></span>{tr("最近一年", "Past year")}'
                   + (f'<span class="k y1"></span>{tr("前一年同一天", "Same day a year earlier")}' if has_ly else "") + "</p>")
            blocks.append(f'<section class="box"><h2>{tr("每天的尖峰用電", "Peak demand each day")}</h2>{leg}'
                          f'<p class="tip">{tr("滑過或點圖看每天數字（單位：萬瓩）", "Hover or tap the chart to see each day (GW)")}</p>'
                          f'<svg class="chart bd" viewBox="0 0 {W} {H}" role="img" aria-label="{e(tr("每日尖峰負載", "Daily peak demand"))}">{pc}</svg>'
                          f'<p class="note">{tr(f"台電每日尖峰負載，目前公布到 {ddate(daily[-1][0], False)}。", f"Taipower daily peak load, published up to {ddate(daily[-1][0], False)}.",
                              f"台湾電力の日別最大電力。{ddate(daily[-1][0], False)}まで公表済み。")}</p></section>')
        mu, mlast = month_use(daily)
        if mu:
            blocks.append(f'<section class="box"><h2>{tr("每月用電量", "Electricity used each month")}</h2>'
                          f'<p class="legend"><span class="sq" style="background:#6f6f6f"></span>{tr("工業", "Industry")}'
                          f'<span class="sq" style="background:#1f7ad6"></span>{tr("民生（住宅、商業）", "Homes and businesses")}</p>'
                          f'<p class="tip">{tr("滑過或點長條看每月數字（單位：億度）", "Hover or tap a bar for each month (TWh)")}</p>'
                          f'<svg class="chart bd" viewBox="0 0 {W} {H}" role="img" aria-label="{e(tr("每月工業與民生用電", "Monthly industrial and residential use"))}">{mu}</svg>'
                          f'<p class="note">{tr("台電每日工業、民生用電加總，只列資料完整的月份。", "Sum of Taipower daily industrial and residential use; complete months only.")}</p></section>')

    pl = plants(units)
    prow = ""
    for i, a in enumerate(pl):
        c = next((c for k, _, _, _, c in FUELS if k == a["fuel"]), "#999")
        nm = PLANTS_EN.get(a["name"], a["name"]) if EN else a["name"]
        cap = f'{a["mw"] / a["cap"] * 100:.0f}%' if a["cap"] and a["mw"] <= a["cap"] * 1.2 else "–"
        prow += (f'<tr{" hidden" if i >= 15 else ""} class="{"x" if i >= 15 else ""}"><td class="r">{i + 1}</td><td><i style="background:{c}"></i>{e(nm)}</td>'
                 f'<td>{e(fuel_name(a["fuel"]))}</td><td class="n">{gw(a["mw"])}</td><td class="n cap">{cap}</td>'
                 f'<td class="nt">{e("、".join(sorted(a["notes"]))) if not (EN or JA) else ""}</td></tr>')
    blocks.append(
        f'<section class="box wide"><h2>{tr("各電廠現在發電", "Power plants right now")}</h2>'
        f'<div class="plwrap"><table class="pl"><thead><tr><th></th><th>{tr("電廠", "Plant")}</th><th>{tr("類別", "Type")}</th>'
        f'<th class="n">{tr("發電（萬瓩）", "Output (GW)")}</th><th class="n cap">{tr("出力", "Load")}</th><th>{"" if EN or JA else "備註"}</th></tr></thead>'
        f'<tbody>{prow}</tbody></table></div>'
        + (f'<button type="button" class="seg-more" onclick="this.parentNode.querySelectorAll(\'tr.x\').forEach(function(r){{r.hidden=false}});this.remove()" '
           f'style="margin-top:8px;font:inherit;font-size:14px;border:1px solid var(--line);background:var(--surface);color:var(--fg);border-radius:999px;padding:6px 14px;cursor:pointer">'
           f'{tr(f"看全部 {len(pl)} 座", f"Show all {len(pl)}", f"全 {len(pl)} か所を見る")}</button>' if len(pl) > 15 else "")
        + f'<p class="note">{tr("同一電廠的機組合併計算；出力＝發電÷裝置容量。備註為台電標示（歲修、檢修、環保停機等）。", "Units at the same plant are combined. Load = output ÷ installed capacity.")}</p></section>')

    path = "power/"
    url = f"{SITE}/{PREFIX[LANG]}{path}"
    rtxt = f"{reserve[-1][2]:.2f}%" if reserve else ""
    if EN:
        title = "Taiwan Electricity Today: Live Power Demand, Operating Reserve and Energy Mix | Taiwan Data"
        desc = (f"Taiwan's power demand right now ({gw(load)} GW), the official supply light and operating reserve ({rtxt} yesterday), "
                f"Taipower's 7-day forecast, and the live mix of gas, coal, solar, wind and hydro (renewables {ren / gen * 100:.1f}%). Updated hourly.")
        foot = ("<div>Source: Taiwan Power Company (Taipower) open data: live generation by unit, daily operating reserve, daily supply and demand, "
                "and the 7-day forecast. This page refreshes hourly.</div>\n"
                "    <div>An independent site, not affiliated with the government. All figures come from government open data.</div>")
    elif JA:
        title = "台湾の電力需給：リアルタイムの電力需要・予備率・電源構成｜Taiwan Data"
        desc = (f"台湾のいまの電力需要 {gw(load)} 万kW、台湾電力の需給ランプと昨日の予備率（{rtxt}）、今後1週間の見通し、"
                f"LNG・石炭・太陽光・風力・水力のリアルタイム電源構成（再エネ {ren / gen * 100:.1f}%）と発電所別の出力。1時間ごとに更新。")
        foot = ("<div>出典：台湾電力公司（台湾電力）オープンデータ（発電機別リアルタイム出力、日別予備率、過去の電力需給、今後1週間の需給見通し）。このページは1時間ごとに更新します。</div>\n"
                f"    <div>{i18n_ja.FOOT}</div>")
    else:
        title = "今日電力：台灣即時用電、備轉容量率、供電燈號、發電來源｜Taiwan Data 台灣數據"
        desc = (f"台灣現在用電 {gw(load)} 萬瓩，昨天尖峰備轉容量率 {rtxt}。台電供電燈號、未來一週預估、"
                f"燃氣、燃煤、太陽能、風力、水力即時發電佔比（再生能源 {ren / gen * 100:.1f}%）與各電廠發電，每小時更新。")
        foot = ("<div>資料來源：台灣電力公司開放資料（各機組即時發電量、每日備轉容量率、過去電力供需資訊、未來一週電力供需預測）。本頁每小時更新。</div>\n"
                "    <div>本站為個人經營，非政府網站；所有數據皆來自政府開放資料。</div>")
    html_ = f"""{head(title, desc, url, "og.png", LANG, "/" + path)}
<body>
<style>{CSS}</style>
{nav(LANG, "/" + path)}
<div class="wrap">
  <div class="top">{hero}{light_box}</div>
  <div class="grid">{"".join(blocks)}</div>
  <footer>
    {foot}
  </footer>
</div>
{JS}
</body>
</html>
"""
    d = Path(out) / PREFIX[LANG] / path
    d.mkdir(parents=True, exist_ok=True)
    (d / "index.html").write_text(html_, encoding="utf-8")
    return url


def build(out, head, nav):
    """nav(lang, path)：頂欄。"""
    if not (DATA / "latest.json").exists():
        return []
    data = load()
    urls = []
    for lang in ("zh", "en", "ja"):
        set_lang(lang)
        urls.append(page(out, head, nav, *data))
    set_lang("zh")
    return urls
