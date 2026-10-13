"""航班頁：/flights/（中文）和 /en/flights/（英文），數字和圖直接寫進 HTML。

資料：data/flights/（scripts/fetch_flights.py 從民航局「民航運輸統計」整理）
build_pages.py 部署時呼叫 build(out, head, nav)。
"""
import csv
import html
import json
from collections import defaultdict
from pathlib import Path

import build_births as bb
import i18n_en

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data/flights"
SITE = "https://taiwandata.info"
e = html.escape
EN = False
MON = bb.MON
SCOPES = ["ALL", "TPE", "KHH", "TSA", "RMQ"]  # 航線表、載客率圖可以選的機場


def tr(zh, en):
    return en if EN else zh


def n(x):
    return f"{x:,}"


def wan(x):
    """6,524,635 → 中文「652.5 萬」、英文「6.52M」"""
    if EN:
        return f"{x / 1e6:.2f}M" if x >= 1e6 else f"{x / 1e3:.0f}k" if x >= 1e4 else n(x)
    return f"{x / 1e4:,.1f} 萬" if x >= 1e4 else n(x)


def pct(now, before):
    if not before:
        return ""
    d = (now - before) / before * 100
    return f"{'▲' if d > 0 else '▼' if d < 0 else '▶'} {abs(d):.1f}%"


def ym_label(ym):
    return f"{MON[int(ym[5:]) - 1]} {int(ym[:4])}" if EN else f"{int(ym[:4])} 年 {int(ym[5:])} 月"


def ap(code):
    zh, en = i18n_en.AIRPORTS.get(code, (code, code))
    return en if EN else zh


def dest(x):
    return i18n_en.DESTS.get(x, x) if EN else x


def airline(x):
    return i18n_en.AIRLINES.get(x, x) if EN else x


def read(path):
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load():
    seg = {r["period"]: {k: int(v) for k, v in r.items() if k != "period"} for r in read(DATA / "segments.csv")}
    airports = defaultdict(dict)
    for r in read(DATA / "airports.csv"):
        airports[r["period"]][r["airport"]] = int(r["pax"])
    lf = defaultdict(dict)
    for r in read(DATA / "loadfactor.csv"):
        if r.get("region", "all") != "all":
            continue
        lf[r["scope"]][r["month"]] = {k: (float(v) if k == "lf" else int(v)) for k, v in r.items() if k not in ("month", "scope", "region")}
    routes = {}
    for p in sorted((DATA / "routes").glob("*.csv")):
        routes[p.stem] = read(p)
    meta = DATA / "routes/ytd.json"
    ytd_through = json.loads(meta.read_text()) if meta.exists() else {}
    return seg, airports, lf, routes, ytd_through


CSS = """
:root { --intl:#1f7ad6; --cross:#8a55dd; --dom:#2e9e5b; --lfbar:#1f7ad6; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --intl:#4a90e2; --cross:#a77ee8; --dom:#4cbb78; --lfbar:#4a90e2; } }
:root[data-theme="dark"] { --intl:#4a90e2; --cross:#a77ee8; --dom:#4cbb78; --lfbar:#4a90e2; }
.wrap { max-width:1840px; padding-inline:max(16px, env(safe-area-inset-left)) max(16px, env(safe-area-inset-right)); }
.top, .grid { display:grid; gap:12px; align-items:start; }
.top > .box, .grid > .box { margin-top:12px; min-width:0; }
@media (min-width:860px) { .top, .grid { grid-template-columns:1fr 1fr; column-gap:16px; row-gap:0; } }
@media (min-width:1360px) { .grid { grid-template-columns:1fr 1fr 1fr; } .grid > .wide { grid-column:span 2; } }
.pagehead { margin:10px 0 0; font-size:24px; font-weight:700; }
.pagehead small { font-size:14px; font-weight:400; color:var(--muted); margin-left:8px; }
.hero .v { font-size:clamp(34px,9vw,56px); font-weight:700; line-height:1.1; white-space:nowrap; }
.hero .v small { font-size:16px; color:var(--muted); font-weight:500; margin-left:4px; }
.hero .yoy { font-size:14px; color:var(--muted); }
.hero .yoy b { font-weight:500; color:var(--fg); }
.split { display:grid; grid-template-columns:repeat(3,1fr); gap:8px; margin-top:12px; }
.split div { min-width:0; }
.split dt { font-size:13px; color:var(--muted); display:flex; align-items:center; gap:5px; }
.split dt i { width:10px; height:10px; border-radius:50%; display:inline-block; flex:none; }
.split dd { margin:0; font-size:clamp(15px,4.4vw,18px); font-weight:700; white-space:nowrap; }
.split dd small { display:block; font-size:12px; font-weight:400; color:var(--muted); }
.chart.bd { max-height:none; }
.bd .line.b { stroke:var(--intl); }
.bd .line.d { stroke:var(--muted); stroke-width:1.5; stroke-dasharray:5 4; }
.bd .dot.b { fill:var(--intl); }
.bd .bar.i { fill:var(--intl); } .bd .bar.c { fill:var(--cross); } .bd .bar.o { fill:var(--dom); }
.bd .hit { fill:transparent; }
.bd .hit:hover, .bd .hit:focus { fill:var(--fg); fill-opacity:.06; outline:none; }
.bd .lab { font-size:12px; font-weight:700; fill:var(--fg); }
.legend { flex-wrap:wrap; }
.legend .sq { width:12px; height:12px; border-radius:3px; display:inline-block; margin-left:8px; }
.legend .sq:first-child { margin-left:0; }
.legend .k.b { border-color:var(--intl); }
.legend .k.d { border-top:2px dashed var(--muted); }
.tip { font-size:13px; color:var(--muted); margin:2px 0 0; min-height:1.6em; }
.note { font-size:13px; color:var(--muted); margin:8px 0 0; }
.seg { display:inline-flex; flex-wrap:wrap; border:1px solid var(--line); border-radius:999px; padding:2px; gap:2px; margin:2px 6px 6px 0; }
.seg button { font:inherit; font-size:14px; border:0; background:none; color:var(--muted); padding:4px 11px; white-space:nowrap; border-radius:999px; cursor:pointer; }
.seg button[aria-pressed="true"] { background:var(--fg); color:var(--bg); }
.hbars { list-style:none; margin:4px 0 0; padding:0; display:grid; gap:6px; }
.hbars li { display:grid; grid-template-columns:7.5em 1fr auto; align-items:center; gap:8px; font-size:14px; }
html[lang="en"] .hbars li { grid-template-columns:9em 1fr auto; }
.hbars .nm { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.hbars .track { height:14px; background:var(--chip); border-radius:4px; overflow:hidden; }
.hbars .fill { display:block; height:100%; background:var(--intl); border-radius:4px; }
.hbars .val { text-align:right; white-space:nowrap; min-width:8.5em; }
.hbars .val small { color:var(--muted); margin-left:6px; display:inline-block; min-width:4.6em; text-align:right; }
.hbars .up { color:#1f8a4c; } .hbars .down { color:#d13c3c; }
.rt { margin-top:4px; }
.rt th, .rt td { white-space:nowrap; }
.rt td:nth-child(2) { white-space:normal; }
.tables > div:last-child .rt td:nth-child(2) { white-space:nowrap; }
.rt td.r { color:var(--muted); width:2.2em; }
.rt tr.main { cursor:pointer; }
.rt tr.main:hover td { background:var(--chip); }
.rt tr.main td:nth-child(2)::after { content:" ›"; color:var(--muted); }
.rt tr.main.open td:nth-child(2)::after { content:" ⌄"; }
.rt tr.sub td { font-size:13px; color:var(--muted); border-top:0; padding-top:2px; padding-bottom:2px; }
.rt tr.sub td:nth-child(2) { padding-left:20px; }
.rt .tag { font-size:11px; color:var(--cross); border:1px solid currentColor; border-radius:4px; padding:0 3px; margin-left:4px; vertical-align:1px; }
.rt .lfc { white-space:nowrap; }
.rt .lfc i { display:inline-block; width:44px; height:6px; border-radius:3px; background:var(--chip); margin-left:6px; vertical-align:middle; overflow:hidden; }
.rt .lfc i b { display:block; height:100%; background:var(--lfbar); }
@media (max-width:520px) { .rt .fl { display:none; } .rt .lfc i { width:28px; } }
.more { margin-top:8px; font:inherit; font-size:14px; border:1px solid var(--line); background:var(--surface); color:var(--fg); border-radius:999px; padding:6px 14px; cursor:pointer; }
.tables { display:grid; gap:16px; }
.tables > div { min-width:0; overflow-x:auto; }
@media (min-width:1100px) { .tables { grid-template-columns:3fr 2fr; } }
.tables h3 { font-size:15px; margin:8px 0 0; }
"""

JS = """<script>
(function () {
  var EN = document.documentElement.lang === "en";
  function f(x) { return x.toLocaleString("en-US"); }
  // 圖表：滑過／點，在圖上方顯示數字
  document.querySelectorAll("svg.bd").forEach(function (svg) {
    var tip = svg.closest(".box").querySelector(".tip"), def = tip.textContent;
    svg.querySelectorAll(".hit").forEach(function (h) {
      function on() { tip.textContent = h.getAttribute("data-tip"); }
      h.addEventListener("mouseenter", on); h.addEventListener("focus", on); h.addEventListener("click", on);
      h.addEventListener("mouseleave", function () { tip.textContent = def; });
    });
  });
  // 載客率圖：換機場
  document.querySelectorAll("[data-swap]").forEach(function (grp) {
    var box = grp.closest(".box");
    grp.querySelectorAll("button").forEach(function (b) {
      b.addEventListener("click", function () {
        grp.querySelectorAll("button").forEach(function (x) { x.setAttribute("aria-pressed", x === b); });
        box.querySelectorAll("[data-pane]").forEach(function (p) { p.hidden = p.getAttribute("data-pane") !== b.getAttribute("data-k"); });
      });
    });
  });

  // 航點、航空公司排行
  var D = JSON.parse(document.getElementById("rt-data").textContent);
  var st = { p: D.P[0][0], s: "ALL", o: "pax", all: false };
  var rbody = document.getElementById("rt-routes"), abody = document.getElementById("rt-airlines");
  var more = document.getElementById("rt-more"), note = document.getElementById("rt-note");
  function nm(list, i) { return (EN ? list[1][i] : null) || list[0][i]; }
  function lfCell(p, s) {
    var v = s ? p / s * 100 : 0;
    return '<td class="n lfc">' + v.toFixed(1) + '%<i><b style="width:' + Math.min(100, v).toFixed(0) + '%"></b></i></td>';
  }
  function agg(rows, key) {
    var m = {};
    rows.forEach(function (r) {
      var k = r[key], a = m[k] || (m[k] = { k: k, reg: r[0], f: 0, s: 0, p: 0, sub: [] });
      a.f += r[3]; a.s += r[4]; a.p += r[5]; a.sub.push(r);
    });
    return Object.keys(m).map(function (k) { return m[k]; });
  }
  function sort(list) {
    var min = D.min[st.p] || 0;
    if (st.o === "pax") return list.sort(function (a, b) { return b.p - a.p; });
    var ok = list.filter(function (a) { return a.f >= min; });
    return ok.sort(function (a, b) { return st.o === "hi" ? b.p / b.s - a.p / a.s : a.p / a.s - b.p / b.s; });
  }
  function render() {
    var rows = (D.D[st.p] || {})[st.s] || [];
    var routes = sort(agg(rows, 1)), lines = sort(agg(rows, 2));
    var lim = st.all ? 1e9 : 20, h = "";
    routes.slice(0, lim).forEach(function (a, i) {
      h += '<tr class="main" data-i="' + i + '"><td class="r">' + (i + 1) + "</td><td>" + nm(D.dn, a.k) +
        (a.reg === 1 ? '<span class="tag">' + (EN ? "China" : "兩岸") + "</span>" : "") + '</td><td class="n">' + f(a.p) +
        "</td>" + lfCell(a.p, a.s) + '<td class="n fl">' + f(a.f) + "</td></tr>";
      a.sub.sort(function (x, y) { return y[5] - x[5]; }).forEach(function (r) {
        h += '<tr class="sub" data-of="' + i + '" hidden><td></td><td>' + nm(D.an, r[2]) + '</td><td class="n">' + f(r[5]) + "</td>" +
          lfCell(r[5], r[4]) + '<td class="n fl">' + f(r[3]) + "</td></tr>";
      });
    });
    rbody.innerHTML = h;
    more.hidden = routes.length <= 20;
    more.textContent = st.all ? (EN ? "Show top 20" : "只看前 20 名") : (EN ? "Show all " + routes.length + " destinations" : "看全部 " + routes.length + " 個航點");
    h = "";
    lines.slice(0, st.all ? 1e9 : 20).forEach(function (a, i) {
      var d = {}; a.sub.forEach(function (r) { d[r[1]] = 1; });
      h += '<tr><td class="r">' + (i + 1) + "</td><td>" + nm(D.an, a.k) + '</td><td class="n">' + f(a.p) + "</td>" + lfCell(a.p, a.s) +
        '<td class="n fl">' + Object.keys(d).length + "</td></tr>";
    });
    abody.innerHTML = h;
    note.textContent = st.o === "pax" ? "" : (EN ? "Only routes and airlines with at least " + f(D.min[st.p]) + " flights in this period."
      : "只列這段期間至少 " + f(D.min[st.p]) + " 個航班的航點和航空公司。");
  }
  rbody.addEventListener("click", function (ev) {
    var tr = ev.target.closest("tr.main"); if (!tr) return;
    var open = !tr.classList.contains("open"); tr.classList.toggle("open", open);
    rbody.querySelectorAll('tr.sub[data-of="' + tr.getAttribute("data-i") + '"]').forEach(function (s) { s.hidden = !open; });
  });
  more.addEventListener("click", function () { st.all = !st.all; render(); });
  document.querySelectorAll("[data-st]").forEach(function (grp) {
    var key = grp.getAttribute("data-st");
    grp.querySelectorAll("button").forEach(function (b) {
      b.addEventListener("click", function () {
        grp.querySelectorAll("button").forEach(function (x) { x.setAttribute("aria-pressed", x === b); });
        st[key] = b.getAttribute("data-k"); st.all = false; render();
      });
    });
  });
  render();
})();
</script>"""


def seg_buttons(attr, items, on):
    return (f'<div class="seg" role="group" {attr}>' + "".join(
        f'<button type="button" data-k="{k}" aria-pressed="{"true" if k == on else "false"}">{label}</button>' for k, label in items)
        + "</div>")


def scale(hi, ticks=4):
    raw = hi / ticks
    mag = 10 ** (len(str(int(raw))) - 1)
    step = next(k * mag for k in (1, 2, 2.5, 5, 10) if k * mag >= raw)
    return 0, -(-hi // step) * step, step


def axis(v):
    """座標軸：中文「600 萬」、英文「6M」"""
    if v == 0:
        return "0"
    if EN:
        return f"{v / 1e6:g}M" if v >= 1e6 else f"{v / 1e3:g}k"
    return f"{v / 1e4:g} 萬" if v >= 1e4 else n(v)


def frame(lo, hi, step, Y):
    W, L, R = bb.W, bb.L, bb.R
    out, g = "", lo
    while g <= hi + 1e-9:
        out += (f'<line x1="{L}" x2="{W - R}" y1="{Y(g):.1f}" y2="{Y(g):.1f}" class="g"/>'
                f'<text x="{L - 5}" y="{Y(g) + 4:.1f}" text-anchor="end">{axis(g)}</text>')
        g += step
    return out


def month_ticks(months):
    k = len(months) - 1
    return [(i, f"{int(mm[:4])}/{int(mm[5:])}") for i, mm in enumerate(months)
            if i in (0, k) or (mm[5:] == "01" and 2 <= i <= k - 2)]


def pax_bars(seg, months):
    """每月旅客：國際（下）＋兩岸＋國內（上）堆疊長條。"""
    W, H, L, R, T, B = bb.W, bb.H, bb.L, bb.R, bb.T, bb.B
    tot = [seg[m]["pax_intl"] + seg[m]["pax_cross"] + seg[m]["pax_dom"] for m in months]
    lo, hi, step = scale(max(tot))
    slot = (W - L - R) / len(months)
    bw = max(2, slot * 0.7)
    X = lambda i: L + slot * (i + 0.5)
    Y = lambda v: T + (H - T - B) * (hi - v) / (hi - lo)
    svg = frame(lo, hi, step, Y)
    for i, m in enumerate(months):
        s, y = seg[m], 0
        for key, cls in (("pax_intl", "i"), ("pax_cross", "c"), ("pax_dom", "o")):
            y1, y2 = Y(y), Y(y + s[key])
            svg += f'<rect x="{X(i) - bw / 2:.1f}" y="{y2:.1f}" width="{bw:.1f}" height="{max(0, y1 - y2 - .6):.1f}" class="bar {cls}"/>'
            y += s[key]
    svg += bb.xlabels(X, month_ticks(months))
    for i, m in enumerate(months):
        s = seg[m]
        t = tr(f"{ym_label(m)}：共 {n(tot[i])} 人次（國際 {n(s['pax_intl'])}、兩岸 {n(s['pax_cross'])}、國內 {n(s['pax_dom'])}）",
               f"{ym_label(m)}: {n(tot[i])} passengers (international {n(s['pax_intl'])}, China {n(s['pax_cross'])}, domestic {n(s['pax_dom'])})")
        svg += f'<rect x="{X(i) - slot / 2:.1f}" y="{T}" width="{slot:.1f}" height="{H - T - B}" class="hit" tabindex="0" data-tip="{e(t)}"/>'
    return svg


def year_lf(routes, year, scope):
    rows = [r for r in routes.get(str(year), []) if r["scope"] == scope]
    seats = sum(int(r["seats"]) for r in rows)
    return sum(int(r["pax"]) for r in rows) / seats * 100 if seats else None


def lf_chart(lf, routes, scope):
    d = lf.get(scope, {})
    months = sorted(d)[-24:]
    if not months:
        return ""
    avg = year_lf(routes, int(months[0][:4]) - 1, scope)
    series = [("b", [d[m]["lf"] for m in months])]
    if avg:
        series.append(("d", [avg] * len(months)))
    vals = [v for _, s in series for v in s]
    lo, hi = min(60, int(min(vals) // 5 * 5)), max(95, -(-int(max(vals)) // 5) * 5)
    W, H, L, R, T, B = bb.W, bb.H, bb.L, bb.R, bb.T, bb.B
    k = max(1, len(months) - 1)
    X = lambda i: L + (W - L - R - 40) * i / k
    Y = lambda v: T + (H - T - B) * (hi - v) / (hi - lo)
    svg = "".join(f'<line x1="{L}" x2="{W - R}" y1="{Y(g):.1f}" y2="{Y(g):.1f}" class="g"/>'
                  f'<text x="{L - 5}" y="{Y(g) + 4:.1f}" text-anchor="end">{g}%</text>' for g in range(lo, hi + 1, 5 if hi - lo <= 25 else 10))
    for cls, s in series:
        svg += f'<path d="{" ".join(("M" if i == 0 else "L") + f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(s))}" class="line {cls}"/>'
    svg += f'<circle cx="{X(len(months) - 1):.1f}" cy="{Y(series[0][1][-1]):.1f}" r="4" class="dot b"/>'
    svg += f'<text x="{X(len(months) - 1) + 8:.1f}" y="{Y(series[0][1][-1]) + 4:.1f}" class="lab">{series[0][1][-1]:.1f}%</text>'
    labels = [(i, tr(f"{int(m[5:])}月", MON[int(m[5:]) - 1])) for i, m in enumerate(months)] if len(months) <= 12 else month_ticks(months)
    svg += bb.xlabels(X, labels)
    cw = (X(1) - X(0)) if len(months) > 1 else W - L - R
    for i, m in enumerate(months):
        x = d[m]
        in_lf = x["in_pax"] / x["in_seats"] * 100 if x["in_seats"] else 0
        out_lf = x["out_pax"] / x["out_seats"] * 100 if x["out_seats"] else 0
        t = tr(f"{ym_label(m)}：載客率 {x['lf']:.1f}%（入境 {in_lf:.1f}%、出境 {out_lf:.1f}%），{n(x['flights'])} 個航班、{n(x['pax'])} 人次",
               f"{ym_label(m)}: {x['lf']:.1f}% full (arrivals {in_lf:.1f}%, departures {out_lf:.1f}%), {n(x['flights'])} flights, {n(x['pax'])} passengers")
        svg += f'<rect x="{X(i) - cw / 2:.1f}" y="{T}" width="{cw:.1f}" height="{H - T - B}" class="hit" tabindex="0" data-tip="{e(t)}"/>'
    legend = (f'<p class="legend"><span class="k b"></span>{tr("每月載客率", "Monthly load factor")}'
              + (f'<span class="k d"></span>{tr(f"{int(months[0][:4]) - 1} 年全年平均 {avg:.1f}%", f"{int(months[0][:4]) - 1} average {avg:.1f}%")}' if avg else "")
              + "</p>")
    return (f'<div data-pane="{scope}"{"" if scope == "ALL" else " hidden"}>{legend}'
            f'<svg class="chart bd" viewBox="0 0 {W} {H}" role="img" aria-label="{e(tr(f"{ap(scope)}國際及兩岸定期航班每月載客率", f"Monthly load factor, {ap(scope)}"))}">{svg}</svg></div>')


def airport_list(airports, last):
    prev = f"{int(last[:4]) - 1}-{last[5:]}"
    now, before = airports.get(last, {}), airports.get(prev, {})
    rows = sorted(((c, v) for c, v in now.items() if c != "ALL" and v > 0), key=lambda x: -x[1])
    top = rows[0][1] if rows else 1
    out = ""
    for c, v in rows:
        d = pct(v, before.get(c))
        cls = "up" if d.startswith("▲") else "down" if d.startswith("▼") else ""
        out += (f'<li><span class="nm">{ap(c)}</span><span class="track"><span class="fill" style="width:{v / top * 100:.1f}%"></span></span>'
                f'<span class="val">{n(v)}<small class="{cls}">{d}</small></span></li>')
    return out


def route_data(routes, periods):
    """給網頁 JS：每段期間、每個機場的 [區域, 航點編號, 航空公司編號, 架次, 座位, 旅客]。"""
    dn, an, packed = [], [], {}
    di, ai = {}, {}
    for key, _ in periods:
        packed[key] = {}
        for r in routes.get(key, []):
            if r["scope"] not in SCOPES:
                continue
            if r["dest"] not in di:
                di[r["dest"]] = len(dn); dn.append(r["dest"])
            if r["airline"] not in ai:
                ai[r["airline"]] = len(an); an.append(r["airline"])
            packed[key].setdefault(r["scope"], []).append(
                [0 if r["region"] == "intl" else 1, di[r["dest"]], ai[r["airline"]], int(r["flights"]), int(r["seats"]), int(r["pax"])])
    return {"dn": [dn, [i18n_en.DESTS.get(x) for x in dn]], "an": [an, [i18n_en.AIRLINES.get(x) for x in an]], "D": packed}


def build(out, head, nav):
    """nav(lang, alt)：頂欄。"""
    global EN
    if not (DATA / "segments.csv").exists():
        return []
    data = load()
    urls = []
    for EN in (False, True):
        bb.EN = EN
        urls.append(page(out, head, nav, *data))
    EN = bb.EN = False
    return urls


def page(out, head, nav, seg, airports, lf, routes, ytd_through):
    last = max(lf.get("ALL", {}) or [p for p in seg if len(p) == 7])
    y, m = int(last[:4]), int(last[5:])

    lfa = lf.get("ALL", {})

    def stat(title, x, sub):
        in_lf = x["in_pax"] / x["in_seats"] * 100 if x["in_seats"] else 0
        out_lf = x["out_pax"] / x["out_seats"] * 100 if x["out_seats"] else 0
        return (f'<section class="box hero"><h2>{title}</h2>'
                f'<div class="v">{x["pax"] / x["seats"] * 100:.1f}<small>% {tr("載客率", "full")}</small></div>{sub}'
                f'<dl class="split"><div><dt>{tr("航班", "Flights")}</dt><dd>{n(x["flights"])}</dd></div>'
                f'<div><dt>{tr("座位", "Seats")}</dt><dd>{wan(x["seats"])}</dd></div>'
                f'<div><dt>{tr("載客", "Passengers")}</dt><dd>{wan(x["pax"])}</dd></div></dl>'
                f'<p class="note">{tr(f"入境 {in_lf:.1f}%・出境 {out_lf:.1f}%。國際及兩岸定期航班。", f"Arrivals {in_lf:.1f}% · departures {out_lf:.1f}%. Scheduled international and China flights.")}</p></section>')

    cur = lfa.get(last)
    avg = year_lf(routes, y - 1, "ALL")
    hero = stat(tr(f"{ym_label(last)}・航班載客率", f"{ym_label(last)}: how full the flights were"), cur,
                f'<div class="yoy">{tr(f"{y - 1} 年平均", f"{y - 1} average")} <b>{avg:.1f}%</b></div>' if avg else "") if cur else ""
    ytd_m = [f"{y}-{i:02d}" for i in range(1, m + 1)]
    ytd_box = ""
    if m > 1 and all(mm in lfa for mm in ytd_m):
        agg = {k: sum(lfa[mm][k] for mm in ytd_m) for k in ("flights", "seats", "pax", "in_pax", "in_seats", "out_pax", "out_seats")}
        ytd_box = stat(tr(f"{y} 年 1～{m} 月累計", f"{y} so far (Jan–{MON[m - 1]})"), agg, "")

    blocks = []
    # 航點／航空公司排行（最重要，放最前面）
    periods = [(last, tr(f"{y} 年 {m} 月", f"{MON[m - 1]} {y}"))]
    yk = f"{y}-ytd"
    if yk in routes and ytd_through.get(yk, 0) > 1:
        t = ytd_through[yk]
        periods.append((yk, tr(f"今年 1～{t} 月", f"Jan–{MON[t - 1]}")))
    if str(y - 1) in routes:
        periods.append((str(y - 1), tr(f"{y - 1} 全年", f"{y - 1}")))
    periods = [p for p in periods if p[0] in routes]
    rd = route_data(routes, periods)
    rd["P"] = periods
    months_in = {last: 1, yk: ytd_through.get(yk, 1), str(y - 1): 12}
    rd["min"] = {k: 30 * months_in.get(k, 1) for k, _ in periods}
    th = (f'<tr><th></th><th>{tr("航點", "Destination")}</th><th class="n">{tr("旅客", "Passengers")}</th>'
          f'<th class="n">{tr("載客率", "Load factor")}</th><th class="n fl">{tr("航班", "Flights")}</th></tr>')
    tha = (f'<tr><th></th><th>{tr("航空公司", "Airline")}</th><th class="n">{tr("旅客", "Passengers")}</th>'
           f'<th class="n">{tr("載客率", "Load factor")}</th><th class="n fl">{tr("航點", "Routes")}</th></tr>')
    blocks.append(
        f'<section class="box wide" id="routes"><h2>{tr("熱門航點與航空公司", "Top destinations and airlines")}</h2>'
        + seg_buttons('data-st="p" aria-label="' + tr("期間", "Period") + '"', periods, periods[0][0])
        + seg_buttons('data-st="s" aria-label="' + tr("機場", "Airport") + '"', [(c, ap(c) if c != "ALL" else tr("全部", "All")) for c in SCOPES], "ALL")
        + seg_buttons('data-st="o" aria-label="' + tr("排序", "Sort") + '"',
                      [("pax", tr("旅客最多", "Most passengers")), ("hi", tr("最滿", "Fullest")), ("lo", tr("最空", "Emptiest"))], "pax")
        + f'<p class="note" id="rt-note"></p><div class="tables">'
        + f'<div><h3>{tr("航點（點一下看各航空公司）", "Destinations (tap for airlines)")}</h3><table class="rt">{th}<tbody id="rt-routes"></tbody></table>'
        + f'<button type="button" class="more" id="rt-more" hidden></button></div>'
        + f'<div><h3>{tr("航空公司", "Airlines")}</h3><table class="rt">{tha}<tbody id="rt-airlines"></tbody></table></div></div>'
        + f'<p class="note">{tr("國際及兩岸定期航班，含所有機場進出（入境＋出境）。載客率＝載客人數÷座位數。", "Scheduled international and China flights, arrivals plus departures. Load factor = passengers ÷ seats.")}</p></section>')

    # 載客率
    scopes = [c for c in SCOPES if lf.get(c)]
    blocks.append(
        f'<section class="box"><h2>{tr("定期航班載客率", "How full are the flights")}</h2>'
        + seg_buttons('data-swap aria-label="' + tr("機場", "Airport") + '"', [(c, ap(c) if c != "ALL" else tr("全部", "All")) for c in scopes], "ALL")
        + f'<p class="tip">{tr("滑過或點圖看每月數字", "Hover or tap the chart to see each month")}</p>'
        + "".join(lf_chart(lf, routes, c) for c in scopes)
        + f'<p class="note">{tr("國際及兩岸定期航班。", "Scheduled international and China flights.")}</p></section>')

    path = "flights/"
    zh_url, en_url = f"{SITE}/{path}", f"{SITE}/en/{path}"
    top_dest = sorted(defaultdict_sum(routes.get(last, []), "ALL").items(), key=lambda x: -x[1])[:3]
    lf_txt = f"{cur['pax'] / cur['seats'] * 100:.1f}%" if cur else ""
    if EN:
        title = f"Taiwan Flight Load Factors by Route and Airline, {ym_label(last)} | Taiwan Data"
        desc = (f"How full were flights to and from Taiwan in {ym_label(last)}? Scheduled international and China flights were {lf_txt} full. "
                f"Rankings of the busiest, fullest and emptiest routes ({', '.join(dest(d) for d, _ in top_dest)}…) and airlines, "
                "by airport, from Civil Aeronautics Administration data.")
        foot = ("<div>Source: Civil Aeronautics Administration (CAA), Ministry of Transportation and Communications, civil aviation "
                "statistics (open data). Figures cover scheduled "
                "international and China flights. Checked daily; the CAA usually publishes each month's figures near the end of the following month.</div>\n"
                "    <div>An independent site, not affiliated with the government. All figures come from government open data.</div>")
    else:
        title = f"台灣航班載客率：{ym_label(last)}各航線、航空公司排行｜Taiwan Data 台灣數據"
        desc = (f"民航局最新統計：{ym_label(last)}國際及兩岸定期航班載客率 {lf_txt}。"
                f"熱門航點（{'、'.join(d for d, _ in top_dest)}…）與航空公司的旅客、載客率排行，可依機場、最滿、最空查看。")
        foot = ("<div>資料來源：交通部民用航空局「民航運輸統計」開放資料。數字為國際及兩岸定期航班。"
                "每天檢查一次，民航局通常在次月月底公布上個月數字。</div>\n"
                "    <div>本站為個人經營，非政府網站；所有數據皆來自政府開放資料。</div>")
    html_ = f"""{head(title, desc, en_url if EN else zh_url, "og.png", "en" if EN else "zh", (zh_url, en_url))}
<body>
<style>{CSS}</style>
{nav("en" if EN else "zh", "/" + path if EN else "/en/" + path)}
<div class="wrap">
  <div class="top">{hero}{ytd_box}</div>
  <div class="grid">{"".join(blocks)}</div>
  <footer>
    {foot}
  </footer>
</div>
<script type="application/json" id="rt-data">{json.dumps(rd, ensure_ascii=False, separators=(",", ":"))}</script>
{JS}
</body>
</html>
"""
    d = Path(out) / ("en" if EN else "") / path
    d.mkdir(parents=True, exist_ok=True)
    (d / "index.html").write_text(html_, encoding="utf-8")
    return en_url if EN else zh_url


def defaultdict_sum(rows, scope):
    out = defaultdict(int)
    for r in rows:
        if r["scope"] == scope:
            out[r["dest"]] += int(r["pax"])
    return out
