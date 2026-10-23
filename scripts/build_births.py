"""出生與死亡頁：/births/（全台）和 /births/<縣市>/（22 縣市各一頁），數字和圖直接寫進 HTML。

資料：data/births/monthly.csv（scripts/fetch_births.py 從內政部戶政司抓的各縣市每月出生、死亡數）
build_pages.py 部署時呼叫 build(out, head, nav)。
"""
import csv
import html
import json
from collections import defaultdict
from pathlib import Path

import i18n_en
import i18n_ja
import i18n_ko

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data/births/monthly.csv"
SITE = "https://taiwandata.info"
e = html.escape

# 縣市網址代號（依官方排列順序）
COUNTIES = [
    ("臺北市", "taipei"), ("新北市", "new-taipei"), ("桃園市", "taoyuan"), ("臺中市", "taichung"),
    ("臺南市", "tainan"), ("高雄市", "kaohsiung"), ("基隆市", "keelung"), ("新竹市", "hsinchu-city"),
    ("新竹縣", "hsinchu-county"), ("苗栗縣", "miaoli"), ("彰化縣", "changhua"), ("南投縣", "nantou"),
    ("雲林縣", "yunlin"), ("嘉義市", "chiayi-city"), ("嘉義縣", "chiayi-county"), ("屏東縣", "pingtung"),
    ("宜蘭縣", "yilan"), ("花蓮縣", "hualien"), ("臺東縣", "taitung"), ("澎湖縣", "penghu"),
    ("金門縣", "kinmen"), ("連江縣", "lienchiang"),
]
SLUG = dict(COUNTIES)

# 外文版：build() 產生 /en/births/、/jp/births/、/kr/births/ 時用 set_lang() 換語言，下面的 tr() 就回該語言
LANG, EN, JA, KO = "zh", False, False, False
MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
PREFIX = {"zh": "", "en": "en/", "ja": "jp/", "ko": "kr/"}  # 各語言網址開頭


def set_lang(lang):
    global LANG, EN, JA, KO
    LANG, EN, JA, KO = lang, lang == "en", lang == "ja", lang == "ko"


def tr(zh, en, ja, ko):
    return en if EN else ja if JA else ko if KO else zh


def cname(c):
    """縣市顯示名稱（英文版用英文，連江縣寫 Matsu；日文版用日文漢字）。"""
    if JA:
        return "台湾全体" if c == "全台" else i18n_ja.COUNTIES.get(c, c)
    if KO:
        return "대만 전체" if c == "全台" else i18n_ko.COUNTIES.get(c, c)
    if not EN:
        return c
    return "All Taiwan" if c == "全台" else "Matsu" if c == "連江縣" else i18n_en.COUNTIES.get(c, c)
MAP = ROOT / "reservoir/taiwan-map.json"  # 本島縣市界（scripts/build_map.py 產生，和水庫地圖同一份）
ISLANDS = [("連江縣", 24), ("金門縣", 134), ("澎湖縣", 244)]  # 離島畫成左上海面的小方塊（y 座標）

# 出生藍、死亡橘；男藍、女粉（色盲也分得出來；深色模式另一組）
CSS = """
:root { --birth:#1f7ad6; --death:#cf6526; --male:#2a7fd4; --female:#d4508f; --y1:#2e9e5b; --y2:#e2a700; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --birth:#3d8fdb; --death:#d0702c; --male:#4a90e2; --female:#d9609b; --y1:#4cbb78; --y2:#f0c43a; } }
:root[data-theme="dark"] { --birth:#3d8fdb; --death:#d0702c; --male:#4a90e2; --female:#d9609b; --y1:#4cbb78; --y2:#f0c43a; }
.wrap { max-width:1840px; padding-inline:max(16px, env(safe-area-inset-left)) max(16px, env(safe-area-inset-right)); }
.top, .grid { display:grid; gap:12px; align-items:start; }
.top > .box, .grid > .box { margin-top:12px; }
.top { margin-top:0; }
@media (min-width:860px) { .top { grid-template-columns:1fr 1fr; } .grid { grid-template-columns:1fr 1fr; } .top, .grid { column-gap:16px; row-gap:0; } }
@media (min-width:1360px) { .grid { grid-template-columns:1fr 1fr 1fr; } }
.chart.bd { max-height:none; }
.pick { position:relative; margin:6px 0 2px; }
#pickbtn { display:inline-flex; align-items:center; gap:8px; font:inherit; font-size:24px; font-weight:700; color:var(--fg); background:none; border:0; padding:4px 0; cursor:pointer; }
#pickbtn svg { width:20px; height:20px; fill:none; stroke:currentColor; stroke-width:2.5; stroke-linecap:round; stroke-linejoin:round; }
#pickbtn small { font-size:14px; font-weight:400; color:var(--muted); }
#pickbtn:hover small { color:var(--fg); text-decoration:underline; }
.pickpanel { position:absolute; z-index:40; top:100%; left:0; width:min(420px, calc(100vw - 32px)); background:var(--surface); border:1px solid var(--line); border-radius:16px; box-shadow:0 8px 24px rgba(12,30,46,.16); padding:12px; }
.pickpanel h4 { margin:10px 0 6px; font-size:12px; font-weight:500; color:var(--muted); }
.pickpanel .g { display:grid; grid-template-columns:repeat(4,1fr); gap:6px; }
.pickpanel a { text-align:center; padding:8px 0; border-radius:10px; background:var(--chip); color:var(--fg); text-decoration:none; font-size:15px; }
.pickpanel a:hover { outline:1.5px solid var(--fg); }
html[lang="en"] .pickpanel .g { grid-template-columns:repeat(3,1fr); }
html[lang="en"] .pickpanel a { font-size:14px; padding:8px 4px; }
.pickpanel a.on { background:var(--fg); color:var(--bg); font-weight:700; }
.duo { display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-top:8px; }
.duo .k { font-size:15px; font-weight:700; display:flex; align-items:center; gap:6px; }
.duo .k i, .sex i { width:10px; height:10px; border-radius:50%; display:inline-block; }
.duo .v { font-size:clamp(28px,8.4vw,52px); white-space:nowrap; font-weight:700; line-height:1.1; }
.duo .v small { font-size:16px; color:var(--muted); font-weight:500; margin-left:2px; }
.duo .yoy, .duo .sex { font-size:14px; color:var(--muted); }
.duo .yoy b { font-weight:500; color:var(--fg); }
.sex { display:flex; flex-wrap:wrap; gap:2px 10px; }
.sex span { display:inline-flex; align-items:center; gap:4px; }
.bd .line.b { stroke:var(--birth); }
.bd .line.d { stroke:var(--death); }
/* 前兩年：去年綠、前年黃（實線） */
.bd .line.b1, .bd .line.d1 { stroke:var(--y1); stroke-width:2; }
.bd .line.b2, .bd .line.d2 { stroke:var(--y2); stroke-width:2; }
.bd .dot.b { fill:var(--birth); }
.bd .dot.d { fill:var(--death); }
.bd .lab { font-size:12px; font-weight:700; fill:var(--fg); }
.bd .bar.m { fill:var(--male); }
.bd .bar.f { fill:var(--female); }
.bd .hit { fill:transparent; }
.bd .hit:hover, .bd .hit:focus { fill:var(--fg); fill-opacity:.06; outline:none; }
.legend { flex-wrap:wrap; }
.legend .k.b { border-color:var(--birth); }
.legend .k.d { border-color:var(--death); }
.legend .k.b1, .legend .k.d1 { border-color:var(--y1); }
.legend .k.b2, .legend .k.d2 { border-color:var(--y2); }
.legend .sq { width:12px; height:12px; border-radius:3px; display:inline-block; margin-left:8px; }
.legend .sq:first-child { margin-left:0; }
.tw .neg { color:var(--muted); }
.tw a { font-weight:500; }
.tw tr.me td { background:var(--chip); font-weight:700; }
.note { font-size:13px; color:var(--muted); margin:8px 0 0; }
.mhead select { font:inherit; font-size:17px; font-weight:700; padding:2px 8px; margin-left:-2px; border-radius:8px; border:1px solid var(--line); background:var(--surface); color:var(--fg); }
.seg { display:inline-flex; border:1px solid var(--line); border-radius:999px; padding:2px; gap:2px; margin:2px 0 4px; }
.seg button { font:inherit; font-size:14px; border:0; background:none; color:var(--muted); padding:4px 12px; border-radius:999px; cursor:pointer; }
.seg button[aria-pressed="true"] { background:var(--fg); color:var(--bg); }
.tmap { display:block; width:100%; height:auto; max-height:780px; margin:4px auto 0; }
.tmap path, .tmap rect.isl { stroke:var(--surface); stroke-width:1.5; cursor:pointer; fill:var(--chip); }
.tmap .me { stroke:var(--fg); stroke-width:4; }
.tmap [tabindex]:focus { outline:none; }
.tmap path:hover, .tmap rect.isl:hover, .tmap .on { stroke:var(--fg); stroke-width:3; }
.tmap text { font-size:22px; fill:var(--fg); font-family:var(--f-body); pointer-events:none; }
.mleg { display:flex; flex-wrap:wrap; gap:4px 12px; font-size:13px; color:var(--muted); margin:6px 0 0; }
.mleg span { display:inline-flex; align-items:center; gap:4px; }
.mleg .u { flex-basis:100%; font-size:12px; }
.mleg i { width:14px; height:14px; border-radius:3px; display:inline-block; }
.bd .xs { display:none; }
@media (max-width:600px) { .bd .xl { display:none; } .bd .xs { display:inline; } }
@media (min-width:1360px) { .grid { align-items:stretch; } .grid > .mapbox { grid-row:span 2; } .tmap { max-height:600px; } }
.tip a { color:var(--fg); font-weight:500; }
.tip { font-size:13px; color:var(--muted); margin:2px 0 0; min-height:1.6em; }
"""

# 滑過／點圖上的長條或點，在圖上方顯示那一期的數字（每個 .hit 帶 data-tip）
JS = """<script>
(function () {
  // 圖表：滑過／點長條或點，在圖上方顯示那一期的數字（每個 .hit 帶 data-tip）
  document.querySelectorAll("svg.bd").forEach(function (svg) {
    var tip = svg.previousElementSibling, def = tip.textContent;
    svg.querySelectorAll(".hit").forEach(function (h) {
      function on() { tip.textContent = h.getAttribute("data-tip"); }
      h.addEventListener("mouseenter", on); h.addEventListener("focus", on); h.addEventListener("click", on);
      h.addEventListener("mouseleave", function () { tip.textContent = def; });
    });
  });

  // 換縣市的格子
  var pb = document.getElementById("pickbtn"), pp = document.getElementById("pickpanel");
  function setPick(open) { pp.hidden = !open; pb.setAttribute("aria-expanded", open); }
  pb.addEventListener("click", function (ev) { ev.stopPropagation(); setPick(pp.hidden); });
  document.addEventListener("click", function (ev) { if (!pp.hidden && !pp.contains(ev.target)) setPick(false); });
  document.addEventListener("keydown", function (ev) { if (ev.key === "Escape") setPick(false); });

  var LG = document.documentElement.lang, EN = LG === "en", JA = LG === "ja", KO = LG === "ko";
  var MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  var D = JSON.parse(document.getElementById("bd-data").textContent);
  var cur = D.m.length - 1, key = "b";
  function f(x) { return x.toLocaleString("en-US"); }
  function lab(ym) { return EN ? MON[ym.slice(5) - 1] + " " + (+ym.slice(0, 4)) : JA ? (+ym.slice(0, 4)) + "年" + (+ym.slice(5)) + "月" : KO ? (+ym.slice(0, 4)) + "년 " + (+ym.slice(5)) + "월" : (+ym.slice(0, 4)) + " 年 " + (+ym.slice(5)) + " 月"; }
  function B(a) { return a[0] + a[1]; }
  function Dd(a) { return a[2] + a[3]; }
  function pct(v, p) { if (!p) return ""; var d = (v - p) / p * 100; return (d > 0 ? "▲ " : d < 0 ? "▼ " : "▶ ") + Math.abs(d).toFixed(1) + "%"; }

  // 單月：選過去 36 個月
  var box = document.getElementById("mbox");
  function setMonth(i) {
    cur = i;
    var a = D.t[i], p = i >= 12 ? D.t[i - 12] : null;
    if (a) {
      [["birth", 0, B], ["death", 2, Dd]].forEach(function (x) {
        var el = box.querySelector(".j-" + x[0]);
        el.querySelector(".j-v").textContent = f(x[2](a));
        el.querySelector(".j-m").textContent = f(a[x[1]]);
        el.querySelector(".j-f").textContent = f(a[x[1] + 1]);
        var y = p ? pct(x[2](a), x[2](p)) : "";
        el.querySelector(".j-yoy").textContent = y;
        el.querySelector(".yoy").hidden = !y;
      });
    }
    document.querySelector(".j-mapmonth").textContent = lab(D.m[i]);
    paint();
  }
  document.getElementById("mpick").addEventListener("change", function () { setMonth(D.m.indexOf(this.value)); });

  // 各縣市地圖：各縣市人口差很多，所以看「每千人」比率（近 12 個月合計 ÷ 人口 × 1000，就是一年的粗出生率／粗死亡率）
  // 顏色：最低到最高平均切 5 級，數字取到 0.5，圖例一看就懂
  var RAMP = { b: ["#d6e6f7", "#a9cbef", "#6fa6e3", "#3a7fd0", "#1c5aa6"], d: ["#f8dcc8", "#f1b88f", "#e48e55", "#cf6526", "#9c4518"] };
  var shapes = document.querySelectorAll(".tmap [data-c]"), tip = document.getElementById("maptip"), leg = document.getElementById("mapleg");
  var tipDef = tip.textContent, picked = null;
  function sum12(c, g) {  // 到所選月份為止 12 個月的合計；不足 12 個月就按比例放大
    var t = 0, k = 0;
    for (var i = Math.max(0, cur - 11); i <= cur; i++) { var a = D.c[c] && D.c[c][i]; if (a) { t += g(a); k++; } }
    return k ? t * 12 / k : null;
  }
  function rates(c) {
    var p = D.p[c] && D.p[c][cur], b = sum12(c, B), d = sum12(c, Dd);
    if (!p || b === null) return null;
    return { b: b / p * 1000, d: d / p * 1000, g: (b - d) / p * 1000 };
  }
  function val(c) { var r = rates(c); return r ? r[key] : null; }
  function r1(x) { return x.toFixed(1); }
  function paint() {
    var vals = [];
    shapes.forEach(function (s) { var v = val(s.getAttribute("data-c")); if (v !== null) vals.push(v); });
    var lo = Math.floor(Math.min.apply(null, vals) * 2) / 2, hi = Math.ceil(Math.max.apply(null, vals) * 2) / 2;
    var ramp, edges, colorOf;
    if (key === "g") {  // 自然增加率：負的（死亡比出生多）用橘色分 4 級，正的用藍色
      var neg = Math.min(lo, -0.5), st = Math.ceil(-neg / 4 * 2) / 2;
      var O = RAMP.d.slice(0, 4);  // 淺到深：越負越深
      colorOf = function (v) { return v >= 0 ? "#3a7fd0" : O[Math.min(3, Math.floor(-v / st))]; };
    } else {
      var step = Math.max(0.5, Math.ceil((hi - lo) / 5 * 2) / 2);
      ramp = RAMP[key];
      edges = [0, 1, 2, 3, 4, 5].map(function (k) { return lo + k * step; });
      colorOf = function (v) { return ramp[Math.min(4, Math.floor((v - lo) / step))]; };
    }
    shapes.forEach(function (s) { var v = val(s.getAttribute("data-c")); s.style.fill = v === null ? "" : colorOf(v); });
    function sg(v) { return (v < 0 ? "−" : "") + r1(Math.abs(v)); }
    var html = "";
    if (key === "g") {
      for (var k = 3; k >= 0; k--) html += '<span><i style="background:' + colorOf(-(k + 0.5) * st) + '"></i>' + sg(-(k + 1) * st) + "～" + sg(-k * st) + "</span>";
      html += '<span><i style="background:#3a7fd0"></i>' + (EN ? "0 or more" : JA ? "0以上" : KO ? "0 이상" : "0 以上") + "</span>";
    } else {
      html = ramp.map(function (c, k) { return '<span><i style="background:' + c + '"></i>' + r1(edges[k]) + "～" + r1(edges[k + 1]) + "</span>"; }).join("");
    }
    leg.innerHTML = html + '<span class="u">' + (EN ? "per 1,000 people, last 12 months" : JA ? "人口千人あたり・直近12か月" : KO ? "인구 1,000명당·최근 12개월" : "每千人・近 12 個月") + "</span>";
    if (picked) show(picked);
  }
  function show(s) {
    var c = s.getAttribute("data-c"), nm = s.getAttribute("data-n") || c, a = D.c[c] && D.c[c][cur];
    if (!a) { tip.textContent = nm + (EN ? ": no data" : JA ? "：データなし" : KO ? ": 데이터 없음" : "：沒有資料"); return; }
    var r = rates(c), u = s.getAttribute("data-u");
    if (!r) { tip.textContent = nm + (EN ? ": no data" : JA ? "：データなし" : KO ? ": 데이터 없음" : "：沒有資料"); return; }
    var g = (r.g < 0 ? "−" : "+") + r1(Math.abs(r.g));
    tip.innerHTML = EN
      ? "<b>" + nm + "</b> per 1,000 people, last 12 months: " + r1(r.b) + " births, " + r1(r.d) + " deaths (" + g + ")  <a href='" + u + "'>Open " + nm + " ›</a>"
      : JA ? "<b>" + nm + "</b> 人口千人あたり（直近12か月）：出生 " + r1(r.b) + "、死亡 " + r1(r.d) + "（" + g + "）　<a href='" + u + "'>" + nm + "のページへ ›</a>"
      : KO ? "<b>" + nm + "</b> 인구 1,000명당(최근 12개월): 출생 " + r1(r.b) + ", 사망 " + r1(r.d) + " (" + g + ")  <a href='" + u + "'>" + nm + " 페이지 ›</a>"
      : "<b>" + nm + "</b> 每千人（近 12 個月）：出生 " + r1(r.b) + "、死亡 " + r1(r.d) + "（" + g + "）　<a href='" + u + "'>看" + nm + " ›</a>";
  }
  shapes.forEach(function (s) {
    s.addEventListener("mouseenter", function () { show(s); });
    s.addEventListener("mouseleave", function () { if (picked) show(picked); else tip.textContent = tipDef; });
    s.addEventListener("click", function () {
      if (picked === s) { location.href = s.getAttribute("data-u"); return; }
      if (picked) picked.classList.remove("on");
      picked = s; s.classList.add("on"); show(s);
    });
    s.addEventListener("keydown", function (ev) { if (ev.key === "Enter") location.href = s.getAttribute("data-u"); });
    s.addEventListener("focus", function () { show(s); });
  });
  document.querySelectorAll(".seg button").forEach(function (b) {
    b.addEventListener("click", function () {
      key = b.getAttribute("data-k");
      document.querySelectorAll(".seg button").forEach(function (x) { x.setAttribute("aria-pressed", x === b); });
      paint();
    });
  });
  paint();
})();
</script>"""


def load():
    """回傳 {縣市: {月份: [出生男, 出生女, 死亡男, 死亡女]}}，另加 "全台"。"""
    data = defaultdict(lambda: defaultdict(lambda: [0, 0, 0, 0]))
    with DATA.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            c = r["county"].replace("台", "臺")
            v = [int(r[k]) for k in ("births_m", "births_f", "deaths_m", "deaths_f")]
            for key in (c, "全台"):
                a = data[key][r["month"]]
                for i in range(4):
                    a[i] += v[i]
    return data


def load_pop():
    """回傳 {縣市: {月份: 人口}}，地圖算每千人比率用。"""
    pop = defaultdict(dict)
    with DATA.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r.get("population"):
                pop[r["county"].replace("台", "臺")][r["month"]] = int(r["population"])
    return pop


def n(x):
    return f"{x:,}"


def pct(now, before):
    if not before:
        return ""
    d = (now - before) / before * 100
    arrow = "▲" if d > 0 else "▼" if d < 0 else "▶"
    return f"{arrow} {abs(d):.1f}%"


def ym_label(ym):
    return f"{MON[int(ym[5:]) - 1]} {int(ym[:4])}" if EN else f"{int(ym[:4])}年{int(ym[5:])}月" if JA else f"{int(ym[:4])}년 {int(ym[5:])}월" if KO else f"{int(ym[:4])} 年 {int(ym[5:])} 月"


def births(a):
    return a[0] + a[1]


def deaths(a):
    return a[2] + a[3]


def nice_scale(lo, hi, ticks=4, zero=False):
    if zero:
        lo = 0
    span = (hi - lo) or hi or 1
    raw = span / ticks
    mag = 10 ** (len(str(int(raw))) - 1)
    step = next(s * mag for s in (1, 2, 2.5, 5, 10) if s * mag >= raw)
    if hi >= 10000:  # 軸寫成「x.x 萬」，格線要是 1,000 的倍數才不會四捨五入走樣
        step = next(s * 1000 for s in (1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000, 5000, 10000) if s * 1000 >= step)
    lo = (lo // step) * step
    hi = -(-hi // step) * step
    if hi == lo:
        hi = lo + step
    return lo, hi, step


def short(v, wan=False):
    """座標軸數字：圖上最大值到 1 萬以上時一律寫「x.x 萬」（不到 1 萬寫 0.x 萬）。"""
    v = int(v)
    if wan:
        if EN:  # 英文版寫 14k；百萬以上寫 2M（航班、旅遊頁）
            return "0" if v == 0 else f"{v / 1e6:g}M" if v >= 1e6 else f"{v / 1000:g}k"
        w = "万" if JA else "만" if KO else " 萬"
        return "0" if v == 0 else f"{v / 10000:g}{w}" if v >= 1e6 else f"{v / 10000:.1f}{w}"
    return n(v)


W, H, L, R, T, B = 420, 230, 50, 14, 12, 26


def frame(lo, hi, step, Y):
    out, g, wan = "", lo, hi >= 10000
    while g <= hi + 1e-9:
        out += (f'<line x1="{L}" x2="{W - R}" y1="{Y(g):.1f}" y2="{Y(g):.1f}" class="g"/>'
                f'<text x="{L - 5}" y="{Y(g) + 4:.1f}" text-anchor="end">{short(g, wan)}</text>')
        g += step
    return out


def xlabels(X, labels):
    """labels：[(索引, 文字)] 或 [(索引, 文字, 手機上的短文字)]；有短文字時置中，手機改顯示短文字。"""
    k = max(x[0] for x in labels) if labels else 0
    out = ""
    for i, t, *sm in labels:
        if sm:
            out += (f'<text class="xl" x="{X(i):.1f}" y="{H - 8}" text-anchor="middle">{t}</text>'
                    f'<text class="xs" x="{X(i):.1f}" y="{H - 8}" text-anchor="middle">{sm[0]}</text>')
            continue
        out += f'<text x="{X(i):.1f}" y="{H - 8}" text-anchor="{"start" if i == 0 and X(i) - L < 12 else "end" if i == k and W - R - X(i) < 12 else "middle"}">{t}</text>'
    return out


def box(title, legend, svg, aria, default_tip, extra=""):
    return (f'<section class="box"><h2>{title}</h2>{legend}<p class="tip">{e(default_tip)}</p>'
            f'<svg class="chart bd" viewBox="0 0 {W} {H}" role="img" aria-label="{e(aria)}">{svg}</svg>{extra}</section>')


def lines_chart(n_x, series, labels, tips, zero=False, end_labels=None):
    """series：[(class, [值或 None]*n_x)]；labels：[(索引, 文字)]；tips：每個 x 的說明文字。"""
    vals = [v for _, s in series for v in s if v is not None]
    lo, hi, step = nice_scale(min(vals), max(vals), zero=zero)
    k = max(1, n_x - 1)
    X = lambda i: L + (W - L - R - ((44 if EN else 34) if end_labels else 0)) * i / k
    Y = lambda v: T + (H - T - B) * (hi - v) / (hi - lo)
    svg = frame(lo, hi, step, Y)
    ends = []
    for cls, s in series:
        pts, pen = [], "M"
        for i, v in enumerate(s):
            if v is None:
                pen = "M"
                continue
            pts.append(f"{pen}{X(i):.1f},{Y(v):.1f}")
            pen = "L"
        svg += f'<path d="{" ".join(pts)}" class="line {cls}"/>'
        last = max((i for i, v in enumerate(s) if v is not None), default=None)
        if last is not None and cls in ("b", "d"):
            svg += f'<circle cx="{X(last):.1f}" cy="{Y(s[last]):.1f}" r="4" class="dot {cls}"/>'
        if end_labels and last is not None and cls in end_labels:
            ends.append([Y(s[last]), X(last), end_labels[cls]])
    ends.sort()
    for i in range(1, len(ends)):  # 線尾標籤太近就錯開
        ends[i][0] = max(ends[i][0], ends[i - 1][0] + 15)
    svg += "".join(f'<text x="{x + 8:.1f}" y="{y + 4:.1f}" class="lab">{t}</text>' for y, x, t in ends)
    svg += xlabels(X, labels)
    cw = (X(1) - X(0)) if n_x > 1 else W - L - R
    svg += "".join(
        f'<rect x="{X(i) - cw / 2:.1f}" y="{T}" width="{cw:.1f}" height="{H - T - B}" class="hit" tabindex="0" data-tip="{e(t)}"/>'
        for i, t in enumerate(tips))
    return svg


def stacked_bars(months, a_of, labels):
    """每月出生：男（下）＋女（上）堆疊長條。"""
    tot = [births(a_of(m)) for m in months]
    lo, hi, step = nice_scale(0, max(tot), zero=True)
    k = len(months)
    slot = (W - L - R) / k
    bw = max(2, slot - 2)
    X = lambda i: L + slot * (i + 0.5)
    Y = lambda v: T + (H - T - B) * (hi - v) / (hi - lo)
    svg = frame(lo, hi, step, Y)
    for i, mm in enumerate(months):
        a = a_of(mm)
        y0, ym, yf = Y(0), Y(a[0]), Y(a[0] + a[1])
        x = X(i) - bw / 2
        svg += (f'<rect x="{x:.1f}" y="{ym:.1f}" width="{bw:.1f}" height="{max(0, y0 - ym):.1f}" class="bar m"/>'
                f'<rect x="{x:.1f}" y="{yf:.1f}" width="{bw:.1f}" height="{max(0, ym - yf - 1):.1f}" rx="2" class="bar f"/>')
    svg += xlabels(X, labels)
    svg += "".join(
        f'<rect x="{X(i) - slot / 2:.1f}" y="{T}" width="{slot:.1f}" height="{H - T - B}" class="hit" tabindex="0" '
        f'data-tip="{ym_label(mm)}{tr("：出生 ", ": ", "：出生 ", ": 출생 ")}{n(births(a_of(mm)))}{tr(" 人（男 ", " births (", "人（男児 ", "명(남아 ")}{n(a_of(mm)[0])}'
        f'{tr("、女 ", " boys, ", "、女児 ", ", 여아 ")}{n(a_of(mm)[1])}{tr("）", " girls)", "）", ")")}"/>'
        for i, mm in enumerate(months))
    return svg


def month_ticks(months):
    k = len(months) - 1
    return [(i, f"{int(mm[:4])}/{int(mm[5:])}") for i, mm in enumerate(months)
            if i in (0, k) or (mm[5:] == "01" and 6 <= i <= k - 5)]


def page_body(name, d):
    """d：{月份: [出生男, 出生女, 死亡男, 死亡女]}。回傳 (HTML 區塊, 最新月, 出生, 死亡, 今年累計)。"""
    months = sorted(d)
    last = months[-1]
    y, m = int(last[:4]), int(last[5:])
    get = lambda mm: d.get(mm, [0, 0, 0, 0])
    a, la = get(last), d.get(f"{y - 1}-{m:02d}")

    def ytd(yy):
        rows = [d[f"{yy}-{i:02d}"] for i in range(1, m + 1) if f"{yy}-{i:02d}" in d]
        return [sum(r[j] for r in rows) for j in range(4)] if rows else None

    def duo(a, la, cmp):
        def one(key, cls, v, before, sex):
            yoy = f'<div class="yoy"{"" if before else " hidden"}>{tr("比", "", "", "")}{cmp} <b class="j-yoy">{pct(v, before)}</b></div>'
            return (f'<div class="j-{cls}"><div class="k"><i style="background:var(--{cls})"></i>{key}</div>'
                    f'<div class="v"><span class="j-v">{n(v)}</span><small>{tr("人", "", "人", "명")}</small></div>'
                    f'<div class="sex"><span><i style="background:var(--male)"></i>{tr("男", "Male", "男", "남")} <span class="j-m">{n(sex[0])}</span></span>'
                    f'<span><i style="background:var(--female)"></i>{tr("女", "Female", "女", "여")} <span class="j-f">{n(sex[1])}</span></span></div>{yoy}</div>')
        return (f'<div class="duo">{one(tr("出生", "Births", "出生", "출생"), "birth", births(a), la and births(la), a[0:2])}'
                f'{one(tr("死亡", "Deaths", "死亡", "사망"), "death", deaths(a), la and deaths(la), a[2:4])}</div>')

    where = "" if name == "全台" else cname(name) + ("の" if JA else " ")
    pick = [mm for mm in months[-36:]][::-1]
    opts = "".join(f'<option value="{mm}"{" selected" if mm == last else ""}>{ym_label(mm)}</option>' for mm in pick)
    hero = duo(a, la, tr("去年同月", "YoY", "前年同月比", "전년 동월 대비"))
    out = [f'<section class="box" id="mbox"><h2 class="mhead"><select id="mpick" aria-label="{tr("選月份", "Choose month", "月を選択", "월 선택")}">{opts}</select></h2>'
           f'{hero}</section>']
    cy, ly = ytd(y), ytd(y - 1)
    if m > 1 and cy:
        out.append(f'<section class="box"><h2>{tr("今年累計", f"{y} YTD (Jan–{MON[m - 1]})", f"{y}年1～{m}月の累計", f"{y}년 1~{m}월 누계")}</h2>'
                   f'{duo(cy, ly, tr("去年同期", "YoY", "前年同期比", "전년 동기 대비"))}</section>')

    # 1. 每月出生（男女）
    recent = months[-24:]
    out.append(box(
        tr("每月出生人數（男女）", "Monthly births by sex", "月別出生数（男女別）", "월별 출생아 수(남녀별)"),
        f'<p class="legend"><i class="sq" style="background:var(--male)"></i>{tr("男", "Boys", "男児", "남아")}'
        f'<i class="sq" style="background:var(--female)"></i>{tr("女", "Girls", "女児", "여아")}</p>',
        stacked_bars(recent, get, month_ticks(recent)),
        tr(f"{where}最近 {len(recent)} 個月每月出生人數，分男女", f"{where}monthly births by sex, last {len(recent)} months", f"{where}直近{len(recent)}か月の月別出生数（男女別）", f"{where}최근 {len(recent)}개월 월별 출생아 수(남녀별)"),
        tr("滑過或點長條看當月數字", "Hover or tap a bar to see that month", "棒にカーソルを合わせるかタップすると、その月の数値を表示", "막대에 마우스를 올리거나 탭하면 해당 월의 수치를 볼 수 있습니다")))

    # 2、3. 今年 vs 去年 vs 前年（1～12 月）
    def yoy_chart(title, fn, cls, word):
        yrs = [yy for yy in (y, y - 1, y - 2) if any(f"{yy}-{i:02d}" in d for i in range(1, 13))]
        series = []
        cs = (cls, cls + "1", cls + "2")
        for yy, c in zip(yrs, cs):
            series.append((c, [fn(d[f"{yy}-{i:02d}"]) if f"{yy}-{i:02d}" in d else None for i in range(1, 13)]))
        legend = '<p class="legend">' + "".join(
            f'<span class="k {c}"></span>{yy}{tr(" 年", "", "年", "년")}' for yy, c in zip(yrs, cs)) + "</p>"
        tips = []
        for i in range(1, 13):
            parts = [f"{yy}{tr(' 年 ', ': ', '年 ', '년: ')}{n(fn(d[f'{yy}-{i:02d}']))}" for yy in yrs if f"{yy}-{i:02d}" in d]
            tips.append(tr(f"{i} 月{word}：", f"{MON[i - 1]} {word}: ", f"{i}月の{word}：", f"{i}월 {word}: ") + tr("、", ", ", "、", ", ").join(parts))
        labels = [(i - 1, tr(f"{i}月", MON[i - 1], f"{i}月", f"{i}월"), tr(str(i), MON[i - 1][0], str(i), str(i))) for i in range(1, 13)]  # 每個月都標；手機只標數字
        return box(title, legend, lines_chart(12, series[::-1], labels, tips), tr(f"{where}{title}折線圖", f"{where}{title}", f"{where}{title}の折れ線グラフ", f"{where}{title} 꺾은선 그래프"),
                   tr("滑過或點圖看每月數字", "Hover or tap the chart to see each month", "グラフにカーソルを合わせるかタップすると、各月の数値を表示", "그래프에 마우스를 올리거나 탭하면 월별 수치를 볼 수 있습니다"))

    # 2. 最近 36 個月出生 vs 死亡（寬螢幕排在右上）
    recent = months[-36:]
    out.append(box(
        tr(f"出生與死亡：最近 {len(recent)} 個月", f"Births and deaths: last {len(recent)} months", f"出生と死亡：直近{len(recent)}か月", f"출생과 사망: 최근 {len(recent)}개월"),
        f'<p class="legend"><span class="k b"></span>{tr("出生", "Births", "出生", "출생")}<span class="k d"></span>{tr("死亡", "Deaths", "死亡", "사망")}</p>',
        lines_chart(len(recent), [("b", [births(get(mm)) for mm in recent]), ("d", [deaths(get(mm)) for mm in recent])],
                    month_ticks(recent),
                    [tr(f"{ym_label(mm)}：出生 {n(births(get(mm)))}、死亡 {n(deaths(get(mm)))}",
                       f"{ym_label(mm)}: {n(births(get(mm)))} births, {n(deaths(get(mm)))} deaths",
                       f"{ym_label(mm)}：出生 {n(births(get(mm)))}、死亡 {n(deaths(get(mm)))}", f"{ym_label(mm)}: 출생 {n(births(get(mm)))}, 사망 {n(deaths(get(mm)))}") for mm in recent],
                    end_labels={"b": tr("出生", "Births", "出生", "출생"), "d": tr("死亡", "Deaths", "死亡", "사망")}),
        tr(f"{where}最近 {len(recent)} 個月每月出生與死亡人數折線圖", f"{where}monthly births and deaths, last {len(recent)} months", f"{where}直近{len(recent)}か月の月別出生数・死亡数の折れ線グラフ", f"{where}최근 {len(recent)}개월 월별 출생·사망 꺾은선 그래프"),
        tr("滑過或點圖看每月數字", "Hover or tap the chart to see each month", "グラフにカーソルを合わせるかタップすると、各月の数値を表示", "그래프에 마우스를 올리거나 탭하면 월별 수치를 볼 수 있습니다")))
    out.append(yoy_chart(tr("每月出生：跟前兩年比", "Monthly births vs the past two years", "月別出生数：過去2年との比較", "월별 출생아 수: 최근 2년과 비교"), births, "b", tr("出生", "births", "出生数", "출생아 수")))
    out.append(yoy_chart(tr("每月死亡：跟前兩年比", "Monthly deaths vs the past two years", "月別死亡数：過去2年との比較", "월별 사망자 수: 최근 2년과 비교"), deaths, "d", tr("死亡", "deaths", "死亡数", "사망자 수")))

    return out, last, a, cy


def county_table(data, last, current="全台", prefix=""):
    y, m = int(last[:4]), int(last[5:])
    rows = []
    for c, slug in COUNTIES:
        dd = data.get(c, {})
        t = [sum(dd[f"{y}-{i:02d}"][j] for i in range(1, m + 1) if f"{y}-{i:02d}" in dd) for j in range(4)]
        rows.append((c, slug, births(t), deaths(t)))
    span = (tr(f"{y} 年 1～{m} 月", f"Jan–{MON[m - 1]} {y}", f"{y}年1～{m}月", f"{y}년 1~{m}월") if m > 1 else ym_label(last))
    body = "".join(
        f'<tr{" class=\"me\"" if c == current else ""}><td><a href="{prefix}{slug}/">{e(cname(c))}</a></td><td class="n">{n(b)}</td><td class="n">{n(dd)}</td>'
        f'<td class="n{" neg" if b < dd else ""}">{"+" if b >= dd else "−"}{n(abs(b - dd))}</td></tr>'
        for c, slug, b, dd in sorted(rows, key=lambda x: -x[2]))
    return (f'<p class="note">{tr(f"{span}累計，依出生人數排序。", f"{span} total, sorted by births.", f"{span}の累計、出生数の多い順。", f"{span} 누계, 출생아 수가 많은 순.")}</p><table class="tw">'
            f'<tr><th>{tr("縣市", "County", "県・市", "시·현")}</th><th class="n">{tr("出生", "Births", "出生", "출생")}</th><th class="n">{tr("死亡", "Deaths", "死亡", "사망")}</th>'
            f'<th class="n">{tr("出生減死亡", "Births − deaths", "出生－死亡", "출생−사망")}</th></tr>{body}</table>')


def map_box(data, last, current, prefix):
    shapes = json.loads(MAP.read_text(encoding="utf-8"))
    paths = "".join(
        f'<path d="{d}" data-c="{c}" data-n="{cname(c)}" data-u="{prefix}{SLUG[c]}/" tabindex="0"{" class=\"me\"" if c == current else ""}/>'
        for c, d in shapes["counties"].items() if c in SLUG)
    isl = "".join(
        f'<rect x="24" y="{yy}" width="170" height="90" rx="12" class="isl{" me" if c == current else ""}" data-c="{c}" '
        f'data-n="{cname(c)}" data-u="{prefix}{SLUG[c]}/" tabindex="0"/><text x="109" y="{yy + 53}" text-anchor="middle">{tr(c[:2], cname(c), c[:2], i18n_ko.ISLAND_SHORT[c])}</text>'
        for c, yy in ISLANDS)
    seg = (f'<div class="seg" role="group" aria-label="{tr("地圖顯示", "Map shows", "地図の表示", "지도 표시")}">'
           f'<button type="button" data-k="b" aria-pressed="true">{tr("出生率", "Birth rate", "出生率", "출생률")}</button>'
           f'<button type="button" data-k="d" aria-pressed="false">{tr("死亡率", "Death rate", "死亡率", "사망률")}</button>'
           f'<button type="button" data-k="g" aria-pressed="false">{tr("自然增加率", "Natural increase", "自然増加率", "자연증가율")}</button></div>')
    return (f'<section class="box mapbox"><h2>{tr("各縣市地圖（", "By county (", "県・市別の地図（", "시·현별 지도(")}<span class="j-mapmonth">{ym_label(last)}</span>{tr("）", ")", "）", ")")}</h2>{seg}'
            f'<p class="tip" id="maptip">{tr("滑過或點縣市看數字，再點一次進入該縣市", "Hover or tap a county for its numbers; tap again to open it", "県・市にカーソルを合わせるかタップすると数値を表示、もう一度タップでその県・市のページへ", "시·현에 마우스를 올리거나 탭하면 수치가 나오고, 한 번 더 탭하면 해당 시·현 페이지로 이동합니다")}</p>'
            f'<svg class="tmap" viewBox="0 0 {shapes["width"]} {shapes["height"]}" role="img" aria-label="{tr("各縣市出生、死亡人數地圖", "Map of births and deaths by county", "県・市別の出生数・死亡数の地図", "시·현별 출생·사망 지도")}">'
            f'{paths}{isl}</svg><div class="mleg" id="mapleg"></div>'
            f'<details><summary>{tr("看各縣市數字", "Numbers by county", "県・市別の数値を見る", "시·현별 수치 보기")}</summary>{county_table(data, last, current, prefix)}</details></section>')


REGIONS = [("北部", ["臺北市", "新北市", "基隆市", "桃園市", "新竹市", "新竹縣", "宜蘭縣"]),
           ("中部", ["苗栗縣", "臺中市", "彰化縣", "南投縣", "雲林縣"]),
           ("南部", ["嘉義市", "嘉義縣", "臺南市", "高雄市", "屏東縣"]),
           ("東部・離島", ["花蓮縣", "臺東縣", "澎湖縣", "金門縣", "連江縣"])]
REGIONS_EN = {"北部": "North", "中部": "Central", "南部": "South", "東部・離島": "East and islands"}
REGIONS_KO = {"北部": "북부", "中部": "중부", "南部": "남부", "東部・離島": "동부·섬 지역"}


def picker(current, prefix):
    """換縣市：平常只顯示「高雄市 ⌄」，點開是依地區分組的縣市格子。"""
    def a(c, url):
        on = ' class="on" aria-current="page"' if c == current else ""
        return f'<a href="{url}"{on}>{cname(c)}</a>'
    groups = f'<div class="g">{a("全台", prefix or "./")}</div>' + "".join(
        f'<h4>{tr(r, REGIONS_EN[r], r, REGIONS_KO[r])}</h4><div class="g">' + "".join(a(c, f"{prefix}{SLUG[c]}/") for c in cs) + "</div>"
        for r, cs in REGIONS)
    return (f'<div class="pick"><button type="button" id="pickbtn" aria-expanded="false" aria-controls="pickpanel">'
            f'{cname(current)}<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg><small>{tr("換縣市", "Change county", "県・市を変更", "시·현 변경")}</small></button>'
            f'<nav class="pickpanel" id="pickpanel" aria-label="{tr("選縣市", "Choose county", "県・市を選択", "시·현 선택")}" hidden>{groups}</nav></div>')


def page_data(data, name):
    """給網頁 JS 用：最近 48 個月（選月份要 36 個月＋去年同月），這一頁的數字和各縣市數字。"""
    months = sorted(data["全台"])[-48:]
    pack = lambda dd: [dd.get(mm) for mm in months]
    pop = load_pop()
    return json.dumps({"m": months, "t": pack(data[name]), "c": {c: pack(data.get(c, {})) for c, _ in COUNTIES},
                       "p": {c: [pop[c].get(mm) for mm in months] for c, _ in COUNTIES}},
                      ensure_ascii=False, separators=(",", ":"))


def build(out, head, nav):
    """nav(lang, path)：頂欄。中文頁放在 births/，英文頁放在 en/births/，日文頁放在 jp/births/。"""
    if not DATA.exists():
        return []
    data = load()
    urls = []
    for lang in ("zh", "en", "ja", "ko"):
        set_lang(lang)
        for name, slug in [("全台", "")] + COUNTIES:
            if name not in data:
                continue
            urls.append(page(out, head, nav, data, name, slug))
    set_lang("zh")
    return urls


def page(out, head, nav, data, name, slug):
    blocks, last, a, cy = page_body(name, data[name])
    y, m = int(last[:4]), int(last[5:])
    path = f"births/{slug + '/' if slug else ''}"
    url = f"{SITE}/{PREFIX[LANG]}{path}"
    if EN:
        where = "Taiwan" if name == "全台" else f"{cname(name)}, Taiwan"
        title = (f"{where} Births and Deaths, {ym_label(last)}: {n(births(a))} Births, {n(deaths(a))} Deaths"
                 f" | Taiwan Vital Statistics")
        desc = (f"Taiwan vital statistics from the Ministry of the Interior: {where} recorded {n(births(a))} births and {n(deaths(a))} deaths "
                f"in {ym_label(last)}." + (f" Jan–{MON[m - 1]} {y}: {n(births(cy))} births, {n(deaths(cy))} deaths." if cy else "")
                + " Monthly births by sex, comparison with the past two years, and a county map.")
        foot = ("<div>Source: Department of Household Registration, Ministry of the Interior, open data (monthly births and deaths "
                "by village, added up here by county and for all of Taiwan). Figures are by month of registration, not the month "
                "of birth or death. Checked daily; usually published early in the following month.</div>\n"
                "    <div>An independent site, not affiliated with the government. All figures come from government open data.</div>")
    elif JA:
        where = "台湾" if name == "全台" else f"台湾・{cname(name)}"
        title = f"{where}の出生数・死亡数：{ym_label(last)}は出生 {n(births(a))}人、死亡 {n(deaths(a))}人｜台湾の人口動態統計"
        desc = (f"内政部戸政司の最新統計：{ym_label(last)}の{where}の出生数は {n(births(a))}人、死亡数は {n(deaths(a))}人。"
                + (f"{y}年1～{m}月の累計は出生 {n(births(cy))}人、死亡 {n(deaths(cy))}人。" if cy else "")
                + "男女別の月別出生数、過去2年との比較、県・市別の地図。")
        foot = ("<div>出典：内政部戸政司オープンデータ「動態資料統計表」（村里別の毎月の出生数・死亡数を、本サイトで県・市別と台湾全体に集計）。"
                "数値は戸籍登録の月によるもので、実際に出生・死亡した月ではありません。毎日確認しており、通常は翌月上旬に前月分が発表されます。</div>\n"
                f"    <div>{i18n_ja.FOOT}</div>")
    elif KO:
        where = "대만" if name == "全台" else f"대만 {cname(name)}"
        title = f"{where} 출생·사망자 수: {ym_label(last)} 출생 {n(births(a))}명, 사망 {n(deaths(a))}명 | 대만 인구 동태 통계"
        desc = (f"내정부 호정사 최신 통계: {ym_label(last)} {where}의 출생아 수는 {n(births(a))}명, 사망자 수는 {n(deaths(a))}명."
                + (f" {y}년 1~{m}월 누계는 출생 {n(births(cy))}명, 사망 {n(deaths(cy))}명." if cy else "")
                + " 남녀별 월별 출생아 수, 최근 2년과의 비교, 시·현별 지도.")
        foot = ("<div>출처: 내정부 호정사 공공데이터 「동태자료통계표」(촌리별 월간 출생·사망자 수를 이 사이트에서 시·현별과 대만 전체로 합산). "
                "수치는 호적 등록 월 기준이며 실제 출생·사망 월이 아닙니다. 매일 확인하며, 보통 다음 달 초에 전월분이 발표됩니다.</div>\n"
                f"    <div>{i18n_ko.FOOT}</div>")
    else:
        where = "台灣" if name == "全台" else name
        title = f"{where}出生與死亡人數：{ym_label(last)}出生 {n(births(a))} 人、死亡 {n(deaths(a))} 人｜Taiwan Data 台灣數據"
        desc = (f"內政部戶政司最新統計：{ym_label(last)}{'全台' if name == '全台' else name}出生 {n(births(a))} 人、"
                f"死亡 {n(deaths(a))} 人。" + (f"{y} 年 1～{m} 月累計出生 {n(births(cy))} 人、死亡 {n(deaths(cy))} 人。" if cy else "")
                + "每月出生男女、跟前兩年比較、各縣市地圖。")
        foot = ("<div>資料來源：內政部戶政司開放資料「動態資料統計表」（各村里每月出生、死亡數，本站加總成縣市與全台）。"
                "數字依戶籍登記月份計算，不是實際出生或死亡的月份；每天檢查一次，通常每月上旬公布上個月。</div>\n"
                "    <div>本站為個人經營，非政府網站；所有數據皆來自政府開放資料。</div>")
    prefix = "" if not slug else "../"
    extra = map_box(data, last, name, prefix)
    html_ = f"""{head(title, desc, url, "og.png", LANG, "/" + path)}
<body>
<style>{CSS}</style>
{nav(LANG, "/" + path)}
<div class="wrap">
  {picker(name, prefix)}
  <div class="top">{"".join(blocks[:2])}</div>
  <div class="grid">{extra}{"".join(blocks[2:])}</div>
  <footer>
    {foot}
  </footer>
</div>
<script type="application/json" id="bd-data">{page_data(data, name)}</script>
{JS}
</body>
</html>
"""
    d = Path(out) / PREFIX[LANG] / path
    d.mkdir(parents=True, exist_ok=True)
    (d / "index.html").write_text(html_, encoding="utf-8")
    return url
