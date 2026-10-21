"""旅客人次頁：/tourism/（中文）和 /en/tourism/（英文），數字和圖直接寫進 HTML。

資料：
- data/travel/（scripts/fetch_travel.py 從觀光署開放資料整理，每年）
- data/flights/airports.csv、segments.csv（民航局每月各機場旅客）
build_pages.py 部署時呼叫 build(out, head, nav)。
"""
import csv
import html
import json
import re
from collections import defaultdict
from pathlib import Path

import build_births as bb
import build_flights as bf
import geo
import i18n_ja
import worldmap

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data/travel"
SITE = "https://taiwandata.info"
e = html.escape
LANG, EN, JA = "zh", False, False
MON = bb.MON
PREFIX = bb.PREFIX
PURPOSE_EN = {"業務": "Business", "觀光": "Leisure", "探親": "Visiting relatives", "會議": "Conferences", "求學": "Study",
              "展覽": "Exhibitions", "醫療": "Medical", "其他": "Other"}
PORT = {"飛機桃園": ("桃園機場", "Taoyuan Airport"), "飛機高雄": ("高雄機場", "Kaohsiung Airport"),
        "飛機松山": ("松山機場", "Songshan Airport"), "飛機臺中": ("台中機場", "Taichung Airport"),
        "輪船小計": ("搭船", "By sea"), "飛機其他": ("其他機場", "Other airports")}
EN_FIX = {"HongKong. Macao": "Hong Kong & Macau", "U.K.": "UK", "USA": "USA", "UAE": "UAE", "S. Africa": "South Africa",
          "Russian Federation": "Russia", "Macao": "Macau"}
ZH_FIX = {"阿拉伯聯合大公國": "阿聯", "香港.澳門": "港澳"}
TOP5 = ["#1f7ad6", "#e07b28", "#2e9e5b", "#8a55dd", "#d4508f"]


def set_lang(lang):
    global LANG, EN, JA
    LANG, EN, JA = lang, lang == "en", lang == "ja"
    bf.set_lang(lang)


def tr(zh, en, ja):
    return en if EN else ja if JA else zh


def n(x):
    return f"{x:,}"


def sgn(now, before):
    """比去年：+3.0%（綠）、-3.0%（紅）。"""
    if not before:
        return ""
    d = (now - before) / before * 100
    cls = "up" if d > 0 else "down" if d < 0 else ""
    return f'<b class="{cls}">{"+" if d > 0 else "-" if d < 0 else ""}{abs(d):.1f}%</b>'


def ym_full(p):
    y, m = int(p[:4]), int(p[5:])
    return f"{MON[m - 1]} {y}" if EN else f"{y}年{m}月" if JA else f"{y} 年 {m} 月"


def ytd_prev(seg, y, m, keys):
    """去年 1～m 月合計：每月都有就直接加；否則用去年全年減掉 m+1～12 月（都是民航局公布的數字）。"""
    mm = [f"{y}-{i:02d}" for i in range(1, m + 1)]
    if all(k in seg for k in mm):
        return {k: sum(seg[x][k] for x in mm) for k in keys}
    rest = [f"{y}-{i:02d}" for i in range(m + 1, 13)]
    if str(y) in seg and all(k in seg for k in rest):
        return {k: seg[str(y)][k] - sum(seg[x][k] for x in rest) for k in keys}
    return None


def pct(now, before):
    if not before:
        return ""
    d = (now - before) / before * 100
    return f"{'▲' if d > 0 else '▼' if d < 0 else '▶'} {abs(d):.1f}%"


def split_name(s):
    """「日本 Japan」→ ("日本", "Japan")"""
    m = re.search(r"[A-Za-z]", s)
    if not m:
        return s, s
    en, zh = s[m.start():].strip(), s[:m.start()].strip()
    return ZH_FIX.get(zh, zh), EN_FIX.get(en, en)


def countable(place):
    return not any(k in place for k in ("合計", "小計", "總計", "未列明", "其他"))


def read(path):
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load():
    def by_year(rows, key="place"):
        out = defaultdict(dict)
        for r in rows:
            out[int(r["year"])][r[key]] = int(r["count"])
        return out
    inbound, outbound = by_year(read(DATA / "inbound.csv")), by_year(read(DATA / "outbound.csv"))
    totals = {int(r["year"]): (int(r["inbound"] or 0), int(r["outbound"] or 0)) for r in read(DATA / "totals.csv")}
    purpose, port = defaultdict(dict), defaultdict(dict)
    for r in read(DATA / "purpose.csv"):
        if r["place"].startswith("總計"):
            purpose[int(r["year"])][r["purpose"]] = int(r["count"])
    for r in read(DATA / "ports.csv"):
        if r["place"].startswith("總計"):
            port[int(r["year"])][r["port"]] = int(r["count"])
    return inbound, outbound, totals, purpose, port


CSS = """
:root { --in:#1f7ad6; --out:#e07b28; --intl:#1f7ad6; --cross:#8a55dd; --dom:#2e9e5b; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --in:#4a90e2; --out:#ec8f45; --intl:#4a90e2; --cross:#a77ee8; --dom:#4cbb78; } }
:root[data-theme="dark"] { --in:#4a90e2; --out:#ec8f45; --intl:#4a90e2; --cross:#a77ee8; --dom:#4cbb78; }
.wrap { max-width:1840px; padding-inline:max(16px, env(safe-area-inset-left)) max(16px, env(safe-area-inset-right)); }
.top, .grid { display:grid; gap:12px; align-items:start; }
.top { align-items:stretch; }
.top > .box { display:flex; flex-direction:column; }
.top > .box > .note { margin-top:auto; padding-top:8px; }
.box h2 select { font:inherit; font-weight:700; border:1px solid var(--line); border-radius:8px; background:var(--surface); color:var(--fg); padding:1px 6px; margin-right:2px; }
.box .yoy b.up, .split b.up { color:#1f8a4c; } .box .yoy b.down, .split b.down { color:#d13c3c; }
.split dd small { display:block; font-size:13px; }
.split dd small b { font-weight:500; }
.top > .box, .grid > .box { margin-top:12px; min-width:0; }
@media (min-width:860px) { .top, .grid { grid-template-columns:1fr 1fr; column-gap:16px; row-gap:0; } }
@media (min-width:1360px) { .grid { grid-template-columns:1fr 1fr 1fr; } }
.duo { display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-top:8px; }
.duo .k { font-size:15px; font-weight:700; display:flex; align-items:center; gap:6px; }
.duo .k i { width:10px; height:10px; border-radius:50%; display:inline-block; }
.duo > div { min-width:0; }
.duo .v { font-size:clamp(22px,6.4vw,46px); white-space:nowrap; font-weight:700; line-height:1.1; }
.duo .v small { font-size:15px; color:var(--muted); font-weight:500; margin-left:2px; }
.duo .yoy { font-size:14px; color:var(--muted); }
.duo .yoy b { font-weight:500; color:var(--fg); }
.big { font-size:clamp(34px,9vw,56px); font-weight:700; line-height:1.1; white-space:nowrap; }
.big small { font-size:16px; color:var(--muted); font-weight:500; margin-left:4px; }
.box > .yoy { font-size:14px; color:var(--muted); }
.box > .yoy b { font-weight:500; color:var(--fg); }
.split { display:grid; grid-template-columns:repeat(3,1fr); gap:8px; margin:12px 0 0; }
.split div { min-width:0; }
.split dt { font-size:13px; color:var(--muted); display:flex; align-items:center; gap:5px; }
.split dt i { width:10px; height:10px; border-radius:50%; display:inline-block; flex:none; }
.split dd { margin:0; font-size:clamp(15px,4.4vw,18px); font-weight:700; white-space:nowrap; }
.bd .bar.i { fill:var(--intl); } .bd .bar.c { fill:var(--cross); } .bd .bar.o { fill:var(--dom); }
.legend .sq { width:12px; height:12px; border-radius:3px; display:inline-block; margin-left:8px; }
.legend .sq:first-child { margin-left:0; }
.note { font-size:13px; color:var(--muted); margin:8px 0 0; }
.tip { font-size:13px; color:var(--muted); margin:2px 0 0; min-height:1.6em; }
.chart.bd { max-height:none; }
.bd .line { stroke-width:2.5; }
.bd .line.b { stroke:var(--in); } .bd .line.d { stroke:var(--out); }
.bd .dot.b { fill:var(--in); } .bd .dot.d { fill:var(--out); }
.bd .lab { font-size:12px; font-weight:700; fill:var(--fg); }
.bd .hit { fill:transparent; }
.bd .hit:hover, .bd .hit:focus { fill:var(--fg); fill-opacity:.06; outline:none; }
.legend { flex-wrap:wrap; }
.legend .k.b { border-color:var(--in); } .legend .k.d { border-color:var(--out); }
.yearpick { margin:14px 0 0; font-size:15px; display:flex; align-items:center; gap:8px; flex-wrap:wrap; }
.yearpick select { font:inherit; font-size:17px; font-weight:700; padding:2px 8px; border-radius:8px; border:1px solid var(--line); background:var(--surface); color:var(--fg); }
.yearpick span { color:var(--muted); font-size:13px; }
.hbars { list-style:none; margin:4px 0 0; padding:0; display:grid; gap:6px; }
.hbars li { display:grid; grid-template-columns:7.5em 1fr auto; align-items:center; gap:8px; font-size:14px; }
html[lang="en"] .hbars li { grid-template-columns:9em 1fr auto; }
.hbars .nm { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.hbars .track { height:14px; background:var(--chip); border-radius:4px; overflow:hidden; }
.hbars .fill { display:block; height:100%; border-radius:4px; }
.hbars.in .fill { background:var(--in); } .hbars.out .fill { background:var(--out); }
.hbars .val { text-align:right; white-space:nowrap; min-width:8.5em; }
.hbars .val small { color:var(--muted); margin-left:6px; display:inline-block; min-width:4.6em; text-align:right; }
.hbars .up { color:#1f8a4c; } .hbars .down { color:#d13c3c; }
.legend .sw { width:18px; height:0; border-top:2.5px solid; display:inline-block; margin-left:8px; }
.legend .sw:first-child { margin-left:0; }
#tmap { margin-top:12px; }
.tm-year { position:absolute; left:12px; bottom:8px; font-size:clamp(28px,7vw,48px); font-weight:700; color:#e8eaed; line-height:1; pointer-events:none; font-variant-numeric:tabular-nums; }
.tm-year small { display:block; font-size:13px; font-weight:400; color:#aeb4bb; margin-top:4px; }
.wm .c.has { cursor:pointer; }
.wm .c.on { stroke:#fff; stroke-width:2; }
.tm-dot { stroke:#1b1d20; vector-effect:non-scaling-stroke; stroke-width:1.5; cursor:pointer; }
.tm-dot.on { stroke:#fff; stroke-width:2.5; }
.play { display:flex; align-items:center; gap:10px; margin-top:10px; }
.play button { font:inherit; font-size:15px; border:1px solid var(--line); background:var(--surface); color:var(--fg); border-radius:999px; padding:6px 14px; cursor:pointer; white-space:nowrap; min-width:5.5em; }
.play input { flex:1; min-width:0; accent-color:var(--in); height:28px; }
.tm-prof { display:grid; gap:4px 16px; }
@media (min-width:700px) { .tm-prof { grid-template-columns:minmax(0,1fr) minmax(0,1.4fr); align-items:center; } }
.tm-prof svg { width:100%; height:auto; max-height:120px; display:block; }
.tm-prof .ln { fill:none; stroke-width:2; vector-effect:non-scaling-stroke; }
.tm-prof .ln.in { stroke:var(--in); } .tm-prof .ln.out { stroke:var(--out); }
.tm-prof .ax { font-size:11px; fill:var(--muted); }
.wminfo b.up { color:#1f8a4c; font-weight:500; } .wminfo b.down { color:#d13c3c; font-weight:500; }
"""

JS = """<script>
(function () {
  var LG = document.documentElement.lang, EN = LG === "en", JA = LG === "ja";
  function L(zh, en, ja) { return EN ? en : JA ? ja : zh; }
  function f(x) { return x.toLocaleString("en-US"); }
  document.querySelectorAll("svg.bd").forEach(function (svg) {
    var tip = svg.closest(".box").querySelector(".tip"), def = tip.textContent;
    svg.querySelectorAll(".hit").forEach(function (h) {
      function on() { tip.textContent = h.getAttribute("data-tip"); }
      h.addEventListener("mouseenter", on); h.addEventListener("focus", on); h.addEventListener("click", on);
      h.addEventListener("mouseleave", function () { tip.textContent = def; });
    });
  });
  var D = JSON.parse(document.getElementById("tv-data").textContent);
  function bars(el, cur, prev, names) {
    var rows = Object.keys(cur).map(function (k) { return [k, cur[k]]; }).sort(function (a, b) { return b[1] - a[1]; }).slice(0, +el.getAttribute("data-n"));
    var top = rows.length ? rows[0][1] : 1;
    el.innerHTML = rows.map(function (r) {
      var p = prev && prev[r[0]], d = "", c = "";
      if (p) { var x = (r[1] - p) / p * 100; d = (x > 0 ? "▲ " : x < 0 ? "▼ " : "▶ ") + Math.abs(x).toFixed(1) + "%"; c = x > 0 ? "up" : x < 0 ? "down" : ""; }
      return '<li><span class="nm">' + (names[r[0]] || r[0]) + '</span><span class="track"><span class="fill" style="width:' + (r[1] / top * 100).toFixed(1) +
        '%"></span></span><span class="val">' + f(r[1]) + '<small class="' + c + '">' + d + "</small></span></li>";
    }).join("");
  }
  var sel = document.getElementById("ypick");
  function show() {
    var y = sel.value;
    document.querySelectorAll("[data-set]").forEach(function (el) {
      var k = el.getAttribute("data-set"); bars(el, D[k][y] || {}, D[k][y - 1], D.names);
    });
    document.querySelectorAll(".j-year").forEach(function (el) { el.textContent = y; });
  }
  var mp = document.getElementById("mpick");
  if (mp) mp.addEventListener("change", function () {
    document.querySelectorAll("[data-mpane]").forEach(function (p) { p.hidden = p.getAttribute("data-mpane") !== mp.value; });
  });
  sel.addEventListener("change", function () { show(); setYear(+sel.value); });

  // 世界地圖：各國依人數上色，年份可以播放
  var svg = document.getElementById("tm-map"), ov = svg.querySelector(".ov"), info = document.getElementById("tm-info");
  var slider = document.getElementById("tm-slider"), playB = document.getElementById("tm-play"), yl = document.getElementById("tm-year");
  var BINS = [1e6, 3e5, 1e5, 3e4, 1e4, 1];
  var PAL = { "in": ["#c2e0ff", "#7db6f2", "#4a90e2", "#2f6fb8", "#24538a", "#1e3a5c"], out: ["#ffd3a3", "#f4a35e", "#e07b28", "#a65f22", "#74441d", "#4a2e17"] };
  var M = { dir: "in", year: +slider.value, sel: null, timer: null };
  var paths = {}; svg.querySelectorAll(".land .c").forEach(function (p) { paths[p.getAttribute("data-id")] = p; });
  function color(v) { for (var i = 0; i < BINS.length; i++) if (v >= BINS[i]) return PAL[M.dir][i]; return null; }
  function pc(now, before) {
    if (!before) return "";
    var x = (now - before) / before * 100;
    return '<b class="' + (x > 0 ? "up" : x < 0 ? "down" : "") + '">' + (x > 0 ? "▲ " : x < 0 ? "▼ " : "▶ ") + Math.abs(x).toFixed(1) + "%</b>";
  }
  function paint() {
    var cur = D[M.dir][M.year] || {}, u = WM.unit(svg);
    slider.style.accentColor = "var(--" + M.dir + ")";
    document.querySelectorAll(".tm-sw").forEach(function (e) { e.style.background = PAL[M.dir][+e.getAttribute("data-i")]; });
    Object.keys(paths).forEach(function (k) { var p = paths[k]; p.style.fill = ""; p.classList.remove("has", "on"); p.removeAttribute("data-p"); });
    ov.innerHTML = "";
    Object.keys(cur).forEach(function (pl) {
      var c = color(cur[pl]), iso = D.iso[pl], dot = D.dot[pl];
      if (!c) return;
      if (iso && paths[iso]) {
        var p = paths[iso]; p.style.fill = c; p.classList.add("has"); p.setAttribute("data-p", pl);
        if (pl === M.sel) p.classList.add("on");
      }
      if (dot) {
        var e = WM.el("circle", { cx: dot[0], cy: dot[1], r: 6 * u, fill: c, "class": "tm-dot" + (pl === M.sel ? " on" : ""), "data-p": pl });
        var t = WM.el("title", {}); t.textContent = (D.names[pl] || pl) + " " + f(cur[pl]); e.appendChild(t);
        ov.appendChild(e);
      }
    });
    var tot = D.tot[M.year] ? D.tot[M.year][M.dir === "in" ? 0 : 1] : 0;
    yl.innerHTML = M.year + (tot ? "<small>" + (M.dir === "in" ? L("來台 ", "Visitors ", "訪台 ") : L("出國 ", "Trips abroad ", "出国 ")) + f(tot) + "</small>" : "");
    profile();
  }
  function spark(pl) {
    var ys = D.years, W = 500, H = 90, vals = ys.map(function (y) { return (D[M.dir][y] || {})[pl] || 0; });
    var mx = Math.max.apply(null, vals) || 1, pts = vals.map(function (v, i) { return (i / (ys.length - 1) * W).toFixed(1) + "," + (H - 14 - v / mx * (H - 22)).toFixed(1); });
    var i = ys.indexOf(M.year), cx = i / (ys.length - 1) * W, cy = H - 14 - vals[i] / mx * (H - 22);
    return '<svg viewBox="-6 0 ' + (W + 12) + " " + H + '"><polyline class="ln ' + M.dir + '" points="' + pts.join(" ") + '"/>' +
      '<circle cx="' + cx.toFixed(1) + '" cy="' + cy.toFixed(1) + '" r="4" fill="var(--' + M.dir + ')"/>' +
      '<text class="ax" x="0" y="' + (H - 1) + '">' + ys[0] + '</text><text class="ax" x="' + W + '" y="' + (H - 1) + '" text-anchor="end">' + ys[ys.length - 1] + "</text></svg>";
  }
  function profile() {
    var cur = D[M.dir][M.year] || {};
    if (!M.sel || !cur[M.sel]) {
      info.innerHTML = '<span class="muted">' + L("點國家看它歷年的人數。", "Tap a country to see its numbers over the years.", "国をタップすると、その国の年ごとの人数を表示します。") + "</span>";
      return;
    }
    var v = cur[M.sel], prev = (D[M.dir][M.year - 1] || {})[M.sel], pre = (D[M.dir][2019] || {})[M.sel];
    var rank = Object.keys(cur).filter(function (k) { return cur[k] > v; }).length + 1;
    var h = "<div><h3>" + (D.names[M.sel] || M.sel) + "</h3><div>" + M.year + L(" 年", ": ", "年 ") + (M.dir === "in" ? L("來台 ", "visitors to Taiwan ", "訪台 ") : L("國人前往 ", "Taiwanese arrivals ", "台湾からの渡航 ")) +
      "<b>" + f(v) + "</b>" + L(" 人次", "", " 人") + L("・第 ", " · rank ", "・") + rank + L(" 名", "", " 位") + "</div><div class='muted'>" +
      (prev ? L("比前一年 ", "vs previous year ", "前年比 ") + pc(v, prev) : "") + (pre && M.year > 2019 ? L("・", " · ", "・") + L("2019 年的 ", "", "2019年の ") + "<b>" + (v / pre * 100).toFixed(0) + "%</b>" + L("", " of 2019", "") : "") +
      "</div></div>" + spark(M.sel);
    info.innerHTML = '<div class="tm-prof">' + h + "</div>";
  }
  function setYear(y) { M.year = y; slider.value = y; if (+sel.value !== y && sel.querySelector('option[value="' + y + '"]')) { sel.value = y; show(); } paint(); }
  slider.addEventListener("input", function () { stop(); setYear(+slider.value); });
  function stop() { if (M.timer) { clearInterval(M.timer); M.timer = null; } playB.textContent = L("▶ 播放", "▶ Play", "▶ 再生"); }
  playB.addEventListener("click", function () {
    if (M.timer) { stop(); return; }
    if (M.year >= +slider.max) setYear(+slider.min);
    playB.textContent = L("❚❚ 暫停", "❚❚ Pause", "❚❚ 一時停止");
    M.timer = setInterval(function () { if (M.year >= +slider.max) { stop(); return; } setYear(M.year + 1); }, 800);
  });
  svg.addEventListener("click", function (ev) {
    var t = ev.target.closest("[data-p]"); M.sel = t && t.getAttribute("data-p") !== M.sel ? t.getAttribute("data-p") : null; paint();
  });
  document.querySelectorAll("[data-tmdir] button").forEach(function (b) {
    b.addEventListener("click", function () {
      b.parentNode.querySelectorAll("button").forEach(function (x) { x.setAttribute("aria-pressed", x === b); });
      M.dir = b.getAttribute("data-k"); M.sel = null; paint();
    });
  });
  svg.addEventListener("wmview", paint);
  WM.init(svg);
  show();
})();
</script>"""


def bars_html(cur, prev, names, limit):
    rows = sorted(cur.items(), key=lambda x: -x[1])[:limit]
    top = rows[0][1] if rows else 1
    out = ""
    for k, v in rows:
        d = pct(v, prev.get(k)) if prev else ""
        cls = "up" if d.startswith("▲") else "down" if d.startswith("▼") else ""
        out += (f'<li><span class="nm">{names.get(k, k)}</span><span class="track"><span class="fill" style="width:{v / top * 100:.1f}%"></span></span>'
                f'<span class="val">{n(v)}<small class="{cls}">{d}</small></span></li>')
    return out


def build(out, head, nav):
    if not (DATA / "totals.csv").exists():
        return []
    data = load()
    seg, airports = bf.load()[:2]
    urls = []
    for lang in ("zh", "en", "ja"):
        set_lang(lang)
        urls.append(page(out, head, nav, *data, seg, airports))
    set_lang("zh")
    return urls


def page(out, head, nav, inbound, outbound, totals, purpose, port, seg, airports):
    y = max(yy for yy, (i, o) in totals.items() if i and o)
    ti, to = totals[y]
    pi, po = totals.get(y - 1, (0, 0))
    pre = totals.get(2019)

    def one(label, cls, v, before, pre_v):
        rec = (f'<div class="yoy">{tr("疫情前 2019 年的", "", "コロナ前の2019年の")} <b>{v / pre_v * 100:.0f}%</b>{tr("", " of the 2019 (pre-Covid) level", "")}</div>'
               if pre_v and y > 2019 else "")
        return (f'<div><div class="k"><i style="background:var(--{cls})"></i>{label}</div>'
                f'<div class="v">{n(v)}<small>{tr("人次", "", "人")}</small></div>'
                f'<div class="yoy">{tr("比前一年", "vs previous year", "前年比")} <b>{pct(v, before)}</b></div>{rec}</div>')

    hero = (f'<section class="box"><h2>{tr(f"{y} 年全年", f"Full year {y}", f"{y}年（通年）")}</h2><div class="duo">'
            f'{one(tr("來台旅客", "Visitors to Taiwan", "訪台客"), "in", ti, pi, pre and pre[0])}'
            f'{one(tr("國人出國", "Outbound trips by Taiwanese", "台湾人の出国"), "out", to, po, pre and pre[1])}</div>'
            f'<p class="note">{tr("觀光署每年公布一次全年統計。", "Published once a year by the Tourism Administration.", "交通部観光署が年1回、通年の統計を発表します。")}</p></section>')

    # 機場旅客（民航局，每月）：左邊單月（可選），右邊今年累計
    latest = air_box = bars_box = ytd_box = ""
    months = sorted(p for p in seg if len(p) == 7)
    if months:
        last = months[-1]
        ly, lm = int(last[:4]), int(last[5:])
        items = [(tr("國際", "International", "国際線"), "intl", "pax_intl"), (tr("兩岸", "Mainland China", "中国大陸線"), "cross", "pax_cross"),
                 (tr("國內", "Domestic", "国内線"), "dom", "pax_dom")]
        keys = ["pax"] + [k for _, _, k in items]

        def block(x, prev, vs):
            d = sgn(x["pax"], prev and prev["pax"])
            split = '<dl class="split">' + "".join(
                f'<div><dt><i style="background:var(--{c})"></i>{k}</dt><dd>{bf.wan(x[f])}'
                f'{"<small>" + sgn(x[f], prev[f]) + "</small>" if prev else ""}</dd></div>' for k, c, f in items) + "</dl>"
            return (f'<div class="big">{n(x["pax"])}<small>{tr("人次", "", "人")}</small></div>'
                    f'<div class="yoy">{vs} {d if d else tr("（去年資料尚未收錄）", "(no data for last year yet)", "（前年のデータは未収録）")}</div>{split}')

        def prev_month(p):
            return seg.get(f"{int(p[:4]) - 1}-{p[5:]}")

        pick_m = [p for p in months if prev_month(p)] or [last]  # 只列能和去年同月比較的月份
        panes = "".join(
            f'<div data-mpane="{p}"{"" if p == last else " hidden"}>{block(seg[p], prev_month(p), tr("比去年同月", "vs same month last year", "前年同月比"))}</div>'
            for p in pick_m)
        opts = "".join(f'<option value="{p}"{" selected" if p == last else ""}>{ym_full(p)}</option>' for p in reversed(pick_m))
        latest = (f'<section class="box"><h2><select id="mpick" aria-label="{tr("月份", "Month", "月")}">{opts}</select>'
                  f'{tr("・全台機場旅客", " · airport passengers in Taiwan", "・台湾の空港の旅客数")}</h2>{panes}'
                  f'<p class="note">{tr("含入境、出境及過境旅客；民航局每月公布。", "Arrivals, departures and transit; published monthly by the Civil Aeronautics Administration.", "到着・出発・乗り継ぎの旅客を含む。民用航空局が毎月発表。")}</p></section>')
        ytd = {k: sum(seg[f"{ly}-{i:02d}"][k] for i in range(1, lm + 1)) for k in keys} if all(f"{ly}-{i:02d}" in seg for i in range(1, lm + 1)) else None
        if ytd:
            ytd_box = (f'<section class="box"><h2>{tr(f"{ly} 年 1～{lm} 月累計・全台機場旅客", f"Year to date (Jan–{MON[lm - 1]} {ly}): airport passengers", f"{ly}年1～{lm}月の累計・台湾の空港の旅客数")}</h2>'
                       + block(ytd, ytd_prev(seg, ly - 1, lm, keys), tr("比去年同期", "vs same period last year", "前年同期比"))
                       + f'<p class="note">{tr("今年到最新月份的合計。", "Total from January to the latest month.", "1月から最新月までの合計。")}</p></section>')
        air_box = (f'<section class="box"><h2>{tr(f"各機場旅客（{ly} 年 {lm} 月）", f"Passengers by airport ({MON[lm - 1]} {ly})", f"空港別の旅客数（{ly}年{lm}月）")}</h2>'
                   f'<p class="note" style="margin:0 0 6px">{tr("右邊是比去年同月", "Right: change vs. the same month last year", "右側は前年同月比")}</p>'
                   f'<ul class="hbars in">{bf.airport_list(airports, last)}</ul></section>')
        recent = months[-24:]
        bars_box = (f'<section class="box"><h2>{tr("每月機場旅客", "Airport passengers per month", "空港の月別旅客数")}</h2>'
                    f'<p class="legend"><i class="sq" style="background:var(--intl)"></i>{tr("國際", "International", "国際線")}'
                    f'<i class="sq" style="background:var(--cross)"></i>{tr("兩岸", "Mainland China", "中国大陸線")}<i class="sq" style="background:var(--dom)"></i>{tr("國內", "Domestic", "国内線")}</p>'
                    f'<p class="tip">{tr("滑過或點長條看當月數字", "Hover or tap a bar to see that month", "棒にカーソルを合わせるかタップすると、その月の数値を表示")}</p>'
                    f'<svg class="chart bd" viewBox="0 0 {bb.W} {bb.H}" role="img" aria-label="{tr("每月機場旅客人次", "Airport passengers per month", "空港の月別旅客数")}">{bf.pax_bars(seg, recent)}</svg></section>')

    # 歷年趨勢
    yrs = [yy for yy in sorted(totals) if yy >= 1990 and yy <= y]
    tips = [tr(f"{yy} 年：來台 {n(totals[yy][0])}、出國 {n(totals[yy][1])}", f"{yy}: {n(totals[yy][0])} visitors, {n(totals[yy][1])} trips abroad", f"{yy}年：訪台 {n(totals[yy][0])}、出国 {n(totals[yy][1])}") for yy in yrs]
    labels = [(i, str(yy)) for i, yy in enumerate(yrs) if (yy % 10 == 0 and yy < yrs[-1] - 4) or i == len(yrs) - 1]
    trend = bb.box(
        tr(f"歷年來台與出國人次（{yrs[0]}～{y}）", f"Visitors and trips abroad, {yrs[0]}–{y}", f"訪台客数と出国者数の推移（{yrs[0]}～{y}年）"),
        f'<p class="legend"><span class="k b"></span>{tr("來台旅客", "Visitors to Taiwan", "訪台客")}<span class="k d"></span>{tr("國人出國", "Outbound trips", "台湾人の出国")}</p>',
        bb.lines_chart(len(yrs), [("b", [totals[yy][0] for yy in yrs]), ("d", [totals[yy][1] for yy in yrs])], labels, tips, zero=True),
        tr("歷年來台旅客與國人出國人次折線圖", "Visitors to Taiwan and trips abroad by year", "訪台客数と台湾人の出国者数の推移の折れ線グラフ"),
        tr("滑過或點圖看每年數字", "Hover or tap the chart to see each year", "グラフにカーソルを合わせるかタップすると、各年の数値を表示")).replace(" 萬<", "萬<")

    # 名稱對照（中文頁顯示中文，英文頁顯示英文）
    EN_FIX = {"China": "Mainland China", "Korea": "South Korea"}  # 觀光署英文名太簡略
    names = {}
    for d in (inbound, outbound):
        for yy in d:
            for p in d[yy]:
                zh, en = split_name(p)
                names[p] = EN_FIX.get(en, en) if EN else i18n_ja.PLACES.get(zh, zh) if JA else zh
    for k in PURPOSE_EN:
        names[k] = PURPOSE_EN[k] if EN else i18n_ja.PURPOSE.get(k, k) if JA else k
    for k, (zh, en) in PORT.items():
        names[k] = en if EN else i18n_ja.PORT.get(k, zh) if JA else zh

    def only(d):
        return {yy: {p: v for p, v in d[yy].items() if countable(p)} for yy in d}
    ib, ob = only(inbound), only(outbound)
    years = sorted(set(ib) & set(ob), reverse=True)
    pick = (f'<div class="yearpick"><label for="ypick">{tr("看哪一年：", "Year:", "年を選択：")}</label><select id="ypick">'
            + "".join(f'<option value="{yy}"{" selected" if yy == y else ""}>{yy}</option>' for yy in years)
            + f'</select><span>{tr("下面四張圖跟著換；右邊是比前一年", "Applies to the four charts below. Right column: change vs. the previous year.", "下の4つのグラフが切り替わります。右側は前年比")}</span></div>')

    def hbox(title, key, d, cls, limit, note=""):
        return (f'<section class="box"><h2>{title}{tr("（", " (", "（")}<span class="j-year">{y}</span>{tr("）", ")", "）")}</h2>'
                f'<ul class="hbars {cls}" data-set="{key}" data-n="{limit}">{bars_html(d.get(y, {}), d.get(y - 1), names, limit)}</ul>'
                + (f'<p class="note">{note}</p>' if note else "") + "</section>")

    blocks = [
        hbox(tr("來台旅客來源", "Visitor origins", "訪台客の居住国・地域"), "in", ib, "in", 15, tr("依旅客居住地。", "By country of residence.", "旅客の居住地別。")),
        hbox(tr("出國目的地", "Destinations abroad", "台湾からの渡航先"), "out", ob, "out", 15, tr("依出國後第一站抵達的地方。", "By first destination after leaving Taiwan.", "出国後に最初に到着した国・地域別。")),
        hbox(tr("來台目的", "Purpose of visit", "訪台目的"), "purpose", purpose, "in", 8),
        hbox(tr("入境地點", "Ports of entry", "入国地点"), "port", port, "in", 6),
    ]

    # 主要來源地近 10 年
    top = sorted(ib.get(y, {}).items(), key=lambda x: -x[1])[:5]
    ys = [yy for yy in range(y - 10, y + 1) if yy in ib]
    series = [(f"c{i}", [ib[yy].get(p) for yy in ys]) for i, (p, _) in enumerate(top)]
    tips = [tr(f"{yy} 年：", f"{yy}: ", f"{yy}年：") + tr("、", ", ", "、").join(f"{names[p]} {n(ib[yy].get(p, 0))}" for p, _ in top) for yy in ys]
    style = "".join(f".bd .line.c{i} {{ stroke:{c}; }}" for i, c in enumerate(TOP5))
    legend = '<p class="legend">' + "".join(f'<span class="sw" style="border-color:{TOP5[i]}"></span>{names[p]}' for i, (p, _) in enumerate(top)) + "</p>"
    blocks.append(bb.box(tr(f"前五大來源地：近 {len(ys)} 年", f"Top five source markets, last {len(ys)} years", f"訪台客の上位5か国・地域：直近{len(ys)}年"), legend,
                         bb.lines_chart(len(ys), series, [(i, str(yy)) for i, yy in enumerate(ys) if i % 2 == 0 or i == len(ys) - 1], tips, zero=True),
                         tr("前五大來台旅客來源地歷年人次", "Visitors from the top five markets by year", "訪台客の上位5か国・地域の推移"),
                         tr("滑過或點圖看每年數字", "Hover or tap the chart to see each year", "グラフにカーソルを合わせるかタップすると、各年の数値を表示")))

    # 世界地圖
    years_all = sorted(set(ib) & set(ob))
    iso, dot = {}, {}
    for yy in years_all:
        for p in list(ib[yy]) + list(ob[yy]):
            zh = split_name(p)[0]
            if zh in geo.PLACE_ISO:
                iso[p] = geo.PLACE_ISO[zh]
            if zh in geo.SMALL:
                dot[p] = worldmap.xy(*geo.SMALL[zh])
    bins = [(1e6, tr("100 萬以上", "1M+", "100万以上")), (3e5, tr("30～100 萬", "300k–1M", "30～100万")), (1e5, tr("10～30 萬", "100k–300k", "10～30万")),
            (3e4, tr("3～10 萬", "30k–100k", "3～10万")), (1e4, tr("1～3 萬", "10k–30k", "1～3万")), (1, tr("1 萬以下", "under 10k", "1万未満"))]
    pal_in = ["#c2e0ff", "#7db6f2", "#4a90e2", "#2f6fb8", "#24538a", "#1e3a5c"]
    tmap = (f'<section class="box" id="tmap"><h2>{tr("世界地圖：來台旅客來源與出國目的地", "World map: visitor origins and destinations abroad", "世界地図：訪台客の居住国と台湾からの渡航先")}</h2>'
            + bf.seg_buttons('data-tmdir aria-label="' + tr("方向", "Direction", "方向") + '"', [("in", tr("來台旅客來源", "Visitor origins", "訪台客の居住国")), ("out", tr("出國目的地", "Destinations abroad", "台湾からの渡航先"))], "in")
            + bf.seg_buttons('data-wmview aria-label="' + tr("地圖範圍", "Map view", "地図の範囲") + '"', [("asia", tr("亞洲", "Asia", "アジア")), ("world", tr("全球", "World", "世界"))], "asia")
            + worldmap.svg("tm-map", tr("各國旅客人數世界地圖", "World map of travellers by country", "国別旅客数の世界地図"), extra='<div class="tm-year" id="tm-year"></div>')
            + f'<div class="play"><button type="button" id="tm-play">{tr("▶ 播放", "▶ Play", "▶ 再生")}</button>'
            + f'<input type="range" id="tm-slider" min="{years_all[0]}" max="{years_all[-1]}" step="1" value="{y}" aria-label="{tr("年份", "Year", "年")}"></div>'
            + '<div class="wmleg"><span>' + tr("人次：", "Travellers:", "人数：") + "</span>"
            + "".join(f'<span><i class="tm-sw" data-i="{i}" style="background:{pal_in[i]}"></i>{t}</span>' for i, (_, t) in enumerate(bins)) + "</div>"
            + '<div class="wminfo" id="tm-info" aria-live="polite"></div>'
            + f'<p class="note">{tr("觀光署每年統計：來台依居住地，出國依第一站抵達地。灰色是沒有單獨統計的國家；香港、澳門等小地方畫成圓點。", "Tourism Administration yearly figures: visitors by country of residence, trips abroad by first destination. Grey countries are not counted separately; small places such as Hong Kong and Macau are shown as dots.", "交通部観光署の年間統計：訪台客は居住地別、出国者は最初の到着地別。灰色は個別に集計されていない国です。香港・マカオなど小さな地域は円で表示しています。")}</p></section>')

    pj = {"names": names, "in": ib, "out": ob, "purpose": purpose, "port": port, "iso": iso, "dot": dot, "years": years_all,
          "tot": {yy: totals[yy] for yy in years_all if yy in totals}}
    path = "tourism/"
    url = f"{SITE}/{PREFIX[LANG]}{path}"
    top3 = "、".join(names[p] for p, _ in top[:3]) if not EN else ", ".join(names[p] for p, _ in top[:3])
    if EN:
        title = f"Taiwan Tourism and Travellers {y}: {ti / 1e6:.2f}M Visitors, {to / 1e6:.2f}M Trips Abroad | Taiwan Data"
        desc = (f"Taiwan welcomed {n(ti)} visitors in {y} ({pct(ti, pi)}) and Taiwanese made {n(to)} trips abroad ({pct(to, po)}). "
                f"Top markets: {top3}. Visitors by country, purpose and port of entry, destinations of Taiwanese travellers, and trends since {yrs[0]}.")
        foot = ("<div>Sources: Tourism Administration, Ministry of Transportation and Communications, tourism statistics open data (yearly); "
                "monthly airport passengers from the Civil Aeronautics Administration. Checked daily.</div>\n"
                "    <div>An independent site, not affiliated with the government. All figures come from government open data.</div>")
    elif JA:
        title = f"台湾の旅客数：{y}年の訪台客 {ti / 1e4:,.0f}万人、台湾人の出国 {to / 1e4:,.0f}万人｜Taiwan Data"
        desc = (f"交通部観光署の最新統計：{y}年の訪台客は {n(ti)}人（{pct(ti, pi)}）、台湾人の出国者は {n(to)}人（{pct(to, po)}）。"
                f"空港別の旅客数、主な居住国・地域（{top3}）、訪台目的、入国地点、台湾からの渡航先、{yrs[0]}年以降の推移。")
        foot = ("<div>出典：交通部観光署 観光統計オープンデータ（年次）、空港の月別旅客数は交通部民用航空局。毎日確認しています。</div>\n"
                f"    <div>{i18n_ja.FOOT}</div>")
    else:
        title = f"台灣旅客人次：{y} 年來台 {ti / 1e4:,.0f} 萬人次、出國 {to / 1e4:,.0f} 萬人次｜Taiwan Data 台灣數據"
        desc = (f"觀光署最新統計：{y} 年來台旅客 {n(ti)} 人次（{pct(ti, pi)}），國人出國 {n(to)} 人次（{pct(to, po)}）。"
                f"各機場旅客、主要來源地{top3}；來台目的、入境港口、國人出國目的地與 {yrs[0]} 年以來趨勢。")
        foot = ("<div>資料來源：交通部觀光署觀光統計開放資料（每年）；每月機場旅客來自交通部民用航空局。每天檢查一次。</div>\n"
                "    <div>本站為個人經營，非政府網站；所有數據皆來自政府開放資料。</div>")
    html_ = f"""{head(title, desc, url, "og.png", LANG, "/" + path)}
<body>
<style>{CSS}{style}{worldmap.CSS}</style>
{nav(LANG, "/" + path)}
<div class="wrap">
  <div class="top">{latest}{ytd_box}</div>
  {tmap}
  <div class="grid">{hero}{air_box}{bars_box}{trend}{blocks[-1]}</div>
  {pick}
  <div class="grid">{"".join(blocks[:-1])}</div>
  <footer>
    {foot}
  </footer>
</div>
<script type="application/json" id="tv-data">{json.dumps(pj, ensure_ascii=False, separators=(",", ":"))}</script>
{worldmap.JS}
{JS}
</body>
</html>
"""
    d = Path(out) / PREFIX[LANG] / path
    d.mkdir(parents=True, exist_ok=True)
    (d / "index.html").write_text(html_, encoding="utf-8")
    return url
