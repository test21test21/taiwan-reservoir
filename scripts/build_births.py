"""出生與死亡頁：/births/（全台）和 /births/<縣市>/（22 縣市各一頁），數字和圖直接寫進 HTML。

資料：data/births/monthly.csv（scripts/fetch_births.py 從內政部戶政司抓的各縣市每月出生、死亡數）
build_pages.py 部署時呼叫 build(out, head, nav)。
"""
import csv
import math
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

CSS = """
/* Tableau 10（scripts/theme.py）：出生紅、死亡青綠、男藍女粉、自然增減藍（橘色跟出生的紅線在深色模式太像，Shane 2026-11-03）；比年份的兩張圖同一年同一色：今年藍、去年橘、前年綠 */
:root { --birth:#e15759; --birth-ln:#e15759; --death:#76b7b2; --male:#4e79a7; --female:#ff9da7; --ni:#4e79a7; --ni-op:.42; --y0:#4e79a7; --y1:#f28e2b; --y2:#59a14f; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --birth:#ee7a7c; --birth-ln:#ee7a7c; --death:#8ccbc6; --male:#7aa6d6; --female:#ffb3bb; --ni:#7aa6d6; --ni-op:.55; --y0:#7aa6d6; --y1:#f5a05a; --y2:#7cc26f; } }
:root[data-theme="dark"] { --birth:#ee7a7c; --birth-ln:#ee7a7c; --death:#8ccbc6; --male:#7aa6d6; --female:#ffb3bb; --ni:#7aa6d6; --ni-op:.55; --y0:#7aa6d6; --y1:#f5a05a; --y2:#7cc26f; }
.wrap { max-width:1840px; padding-inline:max(16px, env(safe-area-inset-left)) max(16px, env(safe-area-inset-right)); }
.top, .grid { display:grid; gap:12px; align-items:start; }
.top > .box, .grid > .box { margin-top:12px; min-width:0; }
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
@media (min-width:860px) { .duo .v { font-size:clamp(28px,4.6vw,52px); } }
.duo .v small { font-size:16px; color:var(--muted); font-weight:500; margin-left:2px; }
.duo .yoy, .duo .sex { font-size:14px; color:var(--muted); }
.duo .yoy b { font-weight:500; color:var(--fg); }
.sex { display:flex; flex-wrap:wrap; gap:2px 10px; }
.sex span { display:inline-flex; align-items:center; gap:4px; }
.bd .line.b { stroke:var(--birth-ln); stroke-width:3; }
.bd .line.d { stroke:var(--death); stroke-width:3; }
/* 跟前兩年比：今年藍（粗）、去年橘、前年綠（細），出生、死亡兩張圖一樣 */
.bd .line.y0 { stroke:var(--y0); stroke-width:3; }
.bd .line.y1 { stroke:var(--y1); stroke-width:2; }
.bd .line.y2 { stroke:var(--y2); stroke-width:2; }
.bd .dot.y0 { fill:var(--y0); }
.bd .dot.b { fill:var(--birth-ln); }
.bd .dot.d { fill:var(--death); }
.bd .lab { font-size:12px; font-weight:700; fill:var(--fg); }
.bd .bar.ni { fill:var(--ni); fill-opacity:var(--ni-op); }
.bd .z { stroke:var(--muted); stroke-width:1; }
.chart.bd text.rax { fill:var(--ni); font-weight:700; }
.bd .ref { stroke:var(--muted); stroke-width:1.5; stroke-dasharray:4 4; }
.legend .li { display:inline-flex; align-items:center; gap:6px; white-space:nowrap; }
.legend .li { margin-right:8px; }
.lead { font-size:15px; line-height:1.5; margin:4px 0 6px; color:var(--fg); }
.lead b { font-weight:700; }
.bd .hit { fill:transparent; }
.bd .hit:hover, .bd .hit:focus { fill:var(--fg); fill-opacity:.06; outline:none; }
.legend { flex-wrap:wrap; }
.legend .k.b { border-color:var(--birth-ln); }
.legend .k.d { border-color:var(--death); }
.legend .k.y0 { border-color:var(--y0); }
.legend .k.y1 { border-color:var(--y1); }
.legend .k.y2 { border-color:var(--y2); }
.legend .k.ref { border-top:2px dashed var(--muted); }
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
@media (min-width:860px) { .grid { align-items:stretch; } .grid > .box:not(.mapbox) { display:flex; flex-direction:column; } .grid > .box:not(.mapbox) > svg.bd { margin-top:auto; } }
/* 寬螢幕：地圖卡跨兩列，地圖自己長到填滿卡片（高度由右邊兩張圖決定） */
@media (min-width:860px) { .grid > .mapbox { grid-row:span 2; display:flex; flex-direction:column; } .grid > .mapbox .tmap { flex:1 1 0; min-height:320px; max-height:none; } }

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
  // 顏色都從網站的 10 Tableau 調出來（Shane 2026-11-03 選 A）：出生 黃 f1ce63 → 橘 f28e2b → 紅 e15759 → 加深；
  // 死亡 青綠 76b7b2 → 藍 4e79a7，深淺拉開、彩度略提高，深色模式也分得出來。淺到深；p：自然增加率 0 以上
  var RAMP = { b: ["#f1ce63", "#f28e2b", "#e15759", "#b4343a", "#901221"], d: ["#bdede5", "#73c9c0", "#37a19e", "#3a73a6", "#2a4f86"], p: "#e15759" };
  function ink(h) {  // 離島方塊上的字：底色亮用深字，底色暗用白字
    var n = parseInt(h.slice(1), 16), y = 0.299 * (n >> 16) + 0.587 * (n >> 8 & 255) + 0.114 * (n & 255);
    return y > 150 ? "#1d2125" : "#ffffff";
  }
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
    if (key === "g") {  // 自然增加率：負的（死亡比出生多）用死亡的顏色分 4 級，正的用出生的顏色
      var neg = Math.min(lo, -0.5), st = Math.ceil(-neg / 4 * 2) / 2;
      var O = RAMP.d.slice(0, 4);  // 淺到深：越負越深
      colorOf = function (v) { return v >= 0 ? RAMP.p : O[Math.min(3, Math.floor(-v / st))]; };
    } else {
      var step = Math.max(0.5, Math.ceil((hi - lo) / 5 * 2) / 2);
      ramp = RAMP[key];
      edges = [0, 1, 2, 3, 4, 5].map(function (k) { return lo + k * step; });
      colorOf = function (v) { return ramp[Math.min(4, Math.floor((v - lo) / step))]; };
    }
    shapes.forEach(function (s) {
      var v = val(s.getAttribute("data-c")), c = v === null ? "" : colorOf(v);
      s.style.fill = c;
      if (s.tagName.toLowerCase() === "rect" && s.nextElementSibling) s.nextElementSibling.style.fill = c ? ink(c) : "";
    });
    function sg(v) { return (v < 0 ? "−" : "") + r1(Math.abs(v)); }
    var html = "";
    if (key === "g") {
      for (var k = 3; k >= 0; k--) html += '<span><i style="background:' + colorOf(-(k + 0.5) * st) + '"></i>' + sg(-(k + 1) * st) + "～" + sg(-k * st) + "</span>";
      html += '<span><i style="background:' + RAMP.p + '"></i>' + (EN ? "0 or more" : JA ? "0以上" : KO ? "0 이상" : "0 以上") + "</span>";
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


W, H, L, R, T, B = 420, 280, 50, 14, 12, 26


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
        if last is not None and cls in ("b", "d", "y0"):
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


def signed(v, wan=False):
    """右軸數字：負數用真正的減號，正數加 +。"""
    return "0" if v == 0 else ("−" if v < 0 else "+") + short(abs(v), wan).replace(" ", "")


def right_scale(neg, pos, nint):
    """右軸：跟左軸共用同一組格線（nint 格），0 落在其中一條格線上，而且盡量往下放，長條往下長到底；
    回傳 (每格多少, 0 以上有幾格)。全台：左軸 0～2.5 萬，右軸 0 對齊 1.5 萬那條線。"""
    for e in range(0, 8):
        for m in (1, 2, 2.5, 5):
            st = m * 10 ** e
            if nint * st >= 10000 and st % 1000:  # 寫成「x.x 萬」時每格要是 1,000 的倍數
                continue
            up, down = (math.ceil(pos / st) if pos else 0), (math.ceil(neg / st) if neg else 0)
            if up + down <= nint:
                return st, nint - down
    return max(neg, pos, 1), 0


def bd_chart(months, b, d, labels, tips):
    """出生、死亡兩條線（左軸）和自然增減長條（右軸，出生減死亡）疊在同一張圖；兩邊的刻度用同一組格線。"""
    ni = [x - y for x, y in zip(b, d)]
    lo, hi, step = nice_scale(0, max(b + d), ticks=5, zero=True)  # 左軸從 0 開始，全台 0～2.5 萬
    nint = max(1, round((hi - lo) / step))
    st2, j = right_scale(-min(ni + [0]), max(ni + [0]), nint)
    hi2 = j * st2
    lo2 = hi2 - nint * st2
    k = max(1, len(months) - 1)
    PR = W - 50  # 圖的右緣；右邊留給右軸的數字
    X = lambda i: L + 6 + (PR - L - 12) * i / k
    Y = lambda v: T + (H - T - B) * (hi - v) / (hi - lo)
    Y2 = lambda v: T + (H - T - B) * (hi2 - v) / (hi2 - lo2)
    wan, wan2 = hi >= 10000, max(abs(lo2), abs(hi2)) >= 10000
    svg = ""
    for i in range(nint + 1):
        g, g2 = lo + i * step, lo2 + i * st2
        y = Y(g)
        svg += (f'<line x1="{L}" x2="{PR}" y1="{y:.1f}" y2="{y:.1f}" class="{"z" if g2 == 0 else "g"}"/>'
                f'<text x="{L - 5}" y="{y + 4:.1f}" text-anchor="end">{short(g, wan)}</text>'
                f'<text x="{PR + 5}" y="{y + 4:.1f}" class="rax">{signed(g2, wan2)}</text>')
    slot = (X(1) - X(0)) if k else PR - L
    bw = max(2, slot * 0.66)
    svg += "".join(f'<rect x="{X(i) - bw / 2:.1f}" y="{min(Y2(0), Y2(v)):.1f}" width="{bw:.1f}" height="{abs(Y2(v) - Y2(0)):.1f}" class="bar ni"/>'
                   for i, v in enumerate(ni))
    for cls, ser in (("b", b), ("d", d)):
        svg += f'<path d="{" ".join(f"{"M" if i == 0 else "L"}{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(ser))}" class="line {cls}"/>'
        svg += f'<circle cx="{X(k):.1f}" cy="{Y(ser[-1]):.1f}" r="4" class="dot {cls}"/>'
    svg += xlabels(X, labels)
    svg += "".join(
        f'<rect x="{X(i) - slot / 2:.1f}" y="{T}" width="{slot:.1f}" height="{H - T - B}" class="hit" tabindex="0" data-tip="{e(t)}"/>'
        for i, t in enumerate(tips))
    return svg, ni


def sr_rows(d, last):
    """每年的男女比：出生（每 100 個女嬰的男嬰數）、死亡（每 100 位女性死亡的男性數）；今年算到最新月。"""
    months = sorted(d)
    rows = []
    for yy in sorted({int(mm[:4]) for mm in months}):
        ms = [mm for mm in months if mm.startswith(f"{yy}-")]
        t = [sum(d[mm][j] for mm in ms) for j in range(4)]
        if t[1] and t[3]:
            miss = [] if yy == int(last[:4]) else [i for i in range(1, 13) if f"{yy}-{i:02d}" not in d]
            rows.append((yy, t, round(t[0] / t[1] * 100, 1), round(t[2] / t[3] * 100, 1), miss))
    return rows


def sr_chart(rows):
    """男女比折線：出生、死亡各一條，每年一點；虛線是 100（男女一樣多）。"""
    vals = [r[2] for r in rows] + [r[3] for r in rows]
    lo, hi = min(100, min(vals)), max(100, max(vals))
    step = next(s for s in (1, 2, 5, 10, 20, 25, 50, 100) if (hi - lo) / s <= 5)
    lo, hi = (lo // step) * step, -(-hi // step) * step
    if hi - max(vals) < step * 0.2:
        hi += step
    k = max(1, len(rows) - 1)
    X = lambda i: L + 18 + (W - L - 18 - 46) * i / k
    Y = lambda v: T + (H - T - B) * (hi - v) / (hi - lo)
    svg, g = "", lo
    while g <= hi + 1e-9:
        svg += (f'<line x1="{L}" x2="{W - R}" y1="{Y(g):.1f}" y2="{Y(g):.1f}" class="g"/>'
                f'<text x="{L - 5}" y="{Y(g) + 4:.1f}" text-anchor="end">{g:g}</text>')
        g += step
    svg += f'<line x1="{L}" x2="{W - R}" y1="{Y(100):.1f}" y2="{Y(100):.1f}" class="ref"/>'
    ends = []
    for cls, j in (("b", 2), ("d", 3)):
        svg += f'<path d="{" ".join(f"{"M" if i == 0 else "L"}{X(i):.1f},{Y(r[j]):.1f}" for i, r in enumerate(rows))}" class="line {cls}"/>'
        svg += "".join(f'<circle cx="{X(i):.1f}" cy="{Y(r[j]):.1f}" r="{4.5 if i == k else 3}" class="dot {cls}"/>' for i, r in enumerate(rows))
        ends.append([Y(rows[-1][j]), f"{rows[-1][j]:.1f}"])
    ends.sort()
    for i in range(1, len(ends)):
        ends[i][0] = max(ends[i][0], ends[i - 1][0] + 15)
    svg += "".join(f'<text x="{X(k) + 9:.1f}" y="{y + 4:.1f}" class="lab">{t}</text>' for y, t in ends)
    svg += xlabels(X, [(i, str(r[0])) for i, r in enumerate(rows)])
    slot = (X(1) - X(0)) if len(rows) > 1 else W - L - R

    def tip(r):
        miss = (tr(f"（缺 {'、'.join(map(str, r[4]))} 月資料）", f" (no data for {', '.join(MON[i - 1] for i in r[4])})",
                   f"（{'・'.join(map(str, r[4]))}月のデータなし）", f" ({', '.join(map(str, r[4]))}월 자료 없음)") if r[4] else "")
        return tr(f"{r[0]} 年：出生 男 {n(r[1][0])}、女 {n(r[1][1])}（{r[2]:.1f}）；死亡 男 {n(r[1][2])}、女 {n(r[1][3])}（{r[3]:.1f}）",
                  f"{r[0]}: births {n(r[1][0])} boys, {n(r[1][1])} girls ({r[2]:.1f}); deaths {n(r[1][2])} men, {n(r[1][3])} women ({r[3]:.1f})",
                  f"{r[0]}年：出生 男 {n(r[1][0])}・女 {n(r[1][1])}（{r[2]:.1f}）、死亡 男 {n(r[1][2])}・女 {n(r[1][3])}（{r[3]:.1f}）",
                  f"{r[0]}년: 출생 남 {n(r[1][0])}, 여 {n(r[1][1])}({r[2]:.1f}), 사망 남 {n(r[1][2])}, 여 {n(r[1][3])}({r[3]:.1f})") + miss
    svg += "".join(
        f'<rect x="{X(i) - slot / 2:.1f}" y="{T}" width="{slot:.1f}" height="{H - T - B}" class="hit" tabindex="0" data-tip="{e(tip(r))}"/>'
        for i, r in enumerate(rows))
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

    # 1. 男女比（每年）：出生每 100 個女嬰的男嬰數、死亡每 100 位女性的男性數
    rows = sr_rows(d, last)
    if rows:
        ry, rb, rd = rows[-1][0], rows[-1][2], rows[-1][3]
        fy, d0 = rows[0][0], rows[0][3]
        span = (tr(f"{ry} 年 1～{m} 月", f"Jan–{MON[m - 1]} {ry}", f"{ry}年1～{m}月", f"{ry}년 1~{m}월") if ry == y and m < 12
                else tr(f"{ry} 年", str(ry), f"{ry}年", f"{ry}년"))
        place = "" if name == "全台" else cname(name)
        lead = tr(f"{place + ' ' if place else ''}{span}，每 100 個女嬰有 <b>{rb:.1f}</b> 個男嬰；每 100 位女性過世，男性有 <b>{rd:.1f}</b> 位。",
                  f"{span}{' in ' + place if place else ''}: <b>{rb:.1f}</b> boys were born for every 100 girls, and <b>{rd:.1f}</b> men died for every 100 women.",
                  f"{place + 'の' if place else ''}{span}は、女児100人に対して男児 <b>{rb:.1f}</b>人、女性の死亡100人に対して男性 <b>{rd:.1f}</b>人。",
                  f"{place + ' ' if place else ''}{span}에는 여아 100명당 남아 <b>{rb:.1f}</b>명이 태어났고, 여성 사망 100명당 남성 <b>{rd:.1f}</b>명이 사망했습니다.")
        if len(rows) > 1 and abs(rd - d0) >= 1:
            up = rd > d0
            lead += tr(f"死亡的男女比從 {fy} 年的 {d0:.1f} {'升' if up else '降'}到 {rd:.1f}。",
                       f" The death ratio has {'risen' if up else 'fallen'} from {d0:.1f} in {fy}.",
                       f"死亡の男女比は{fy}年の{d0:.1f}から{'上がって' if up else '下がって'}います。",
                       f" 사망 성비는 {fy}년 {d0:.1f}에서 {'높아졌습니다' if up else '낮아졌습니다'}.")
        out.append(box(
            tr("出生與死亡的男女比", "Sex ratio of births and deaths", "出生と死亡の男女比", "출생·사망 성비"),
            f'<p class="lead">{lead}</p>'
            f'<p class="legend"><span class="li"><span class="k b"></span>{tr("出生：每 100 個女嬰的男嬰數", "Births: boys per 100 girls", "出生：女児100人あたりの男児数", "출생: 여아 100명당 남아 수")}</span>'
            f'<span class="li"><span class="k d"></span>{tr("死亡：每 100 位女性的男性數", "Deaths: men per 100 women", "死亡：女性100人あたりの男性数", "사망: 여성 100명당 남성 수")}</span>'
            f'<span class="li"><span class="k ref"></span>{tr("100 = 男女一樣多", "100 = equal numbers", "100 = 男女同数", "100 = 남녀 동수")}</span></p>',
            sr_chart(rows),
            tr(f"{where}每年出生與死亡的男女比折線圖", f"{where}sex ratio of births and deaths by year", f"{where}年別の出生・死亡の男女比の折れ線グラフ", f"{where}연도별 출생·사망 성비 꺾은선 그래프"),
            tr("滑過或點圖看每年男女人數", "Hover or tap the chart to see each year", "グラフにカーソルを合わせるかタップすると、各年の男女別の数を表示", "그래프에 마우스를 올리거나 탭하면 연도별 남녀 수를 볼 수 있습니다")))

    # 2、3. 今年 vs 去年 vs 前年（1～12 月）
    def yoy_chart(title, fn, cls, word):
        yrs = [yy for yy in (y, y - 1, y - 2) if any(f"{yy}-{i:02d}" in d for i in range(1, 13))]
        series = []
        cs = ("y0", "y1", "y2")  # 同一年在出生、死亡兩張圖用同一個顏色
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

    # 2. 最近 36 個月出生 vs 死亡；下段是自然增減（出生減死亡，右軸）
    recent = months[-36:]
    bs, ds = [births(get(mm)) for mm in recent], [deaths(get(mm)) for mm in recent]
    nis = [x - z for x, z in zip(bs, ds)]
    tips = [tr(f"{ym_label(mm)}：出生 {n(x)}、死亡 {n(z)}、自然增減 {signed(x - z)}",
               f"{ym_label(mm)}: {n(x)} births, {n(z)} deaths, natural change {signed(x - z)}",
               f"{ym_label(mm)}：出生 {n(x)}、死亡 {n(z)}、自然増減 {signed(x - z)}",
               f"{ym_label(mm)}: 출생 {n(x)}, 사망 {n(z)}, 자연 증감 {signed(x - z)}") for mm, x, z in zip(recent, bs, ds)]
    svg, _ = bd_chart(recent, bs, ds, month_ticks(recent), tips)
    gap, negs, K = nis[-1], sum(1 for v in nis if v < 0), len(nis)
    first = (tr(f"{ym_label(last)}死亡比出生多 <b>{n(-gap)}</b> 人", f"In {ym_label(last)}, deaths exceeded births by <b>{n(-gap)}</b>", f"{ym_label(last)}は死亡が出生を <b>{n(-gap)}</b>人上回りました", f"{ym_label(last)}에는 사망이 출생보다 <b>{n(-gap)}</b>명 많았습니다") if gap < 0
             else tr(f"{ym_label(last)}出生比死亡多 <b>{n(gap)}</b> 人", f"In {ym_label(last)}, births exceeded deaths by <b>{n(gap)}</b>", f"{ym_label(last)}は出生が死亡を <b>{n(gap)}</b>人上回りました", f"{ym_label(last)}에는 출생이 사망보다 <b>{n(gap)}</b>명 많았습니다") if gap > 0
             else tr(f"{ym_label(last)}出生和死亡一樣多", f"In {ym_label(last)}, births and deaths were equal", f"{ym_label(last)}は出生と死亡が同数でした", f"{ym_label(last)}에는 출생과 사망이 같았습니다"))
    rest = (tr(f"，最近 {K} 個月每個月都是死亡比較多。", f"; deaths have outnumbered births in every one of the last {K} months.", f"。直近{K}か月はすべての月で死亡が出生を上回っています。", f". 최근 {K}개월 동안 매달 사망이 출생보다 많았습니다.") if negs == K
            else tr(f"，最近 {K} 個月有 {negs} 個月死亡比出生多。", f"; deaths outnumbered births in {negs} of the last {K} months.", f"。直近{K}か月のうち{negs}か月で死亡が出生を上回りました。", f". 최근 {K}개월 중 {negs}개월은 사망이 출생보다 많았습니다."))
    out.append(box(
        tr(f"出生與死亡：最近 {len(recent)} 個月", f"Births and deaths: last {len(recent)} months", f"出生と死亡：直近{len(recent)}か月", f"출생과 사망: 최근 {len(recent)}개월"),
        f'<p class="lead">{first}{rest}</p>'
        f'<p class="legend"><span class="li"><span class="k b"></span>{tr("出生", "Births", "出生", "출생")}</span><span class="li"><span class="k d"></span>{tr("死亡", "Deaths", "死亡", "사망")}</span>'
        f'<span class="li"><i class="sq" style="background:var(--ni)"></i>{tr("自然增減（出生減死亡，右軸）", "Natural change (births − deaths, right axis)", "自然増減（出生－死亡、右軸）", "자연 증감(출생−사망, 오른쪽 축)")}</span></p>',
        svg,
        tr(f"{where}最近 {len(recent)} 個月每月出生、死亡人數折線圖，以及自然增減長條圖", f"{where}monthly births and deaths, last {len(recent)} months, with natural change as bars", f"{where}直近{len(recent)}か月の月別出生数・死亡数の折れ線グラフと自然増減の棒グラフ", f"{where}최근 {len(recent)}개월 월별 출생·사망 꺾은선 그래프와 자연 증감 막대그래프"),
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
                + " Sex ratio of births and deaths, natural change, comparison with the past two years, and a county map.")
        foot = ("<div>Source: Department of Household Registration, Ministry of the Interior, open data (monthly births and deaths "
                "by village, added up here by county and for all of Taiwan). Figures are by month of registration, not the month "
                "of birth or death. Checked daily; usually published early in the following month.</div>\n"
                "    <div>An independent site, not affiliated with the government. All figures come from government open data.</div>")
    elif JA:
        where = "台湾" if name == "全台" else f"台湾・{cname(name)}"
        title = f"{where}の出生数・死亡数：{ym_label(last)}は出生 {n(births(a))}人、死亡 {n(deaths(a))}人｜台湾の人口動態統計"
        desc = (f"内政部戸政司の最新統計：{ym_label(last)}の{where}の出生数は {n(births(a))}人、死亡数は {n(deaths(a))}人。"
                + (f"{y}年1～{m}月の累計は出生 {n(births(cy))}人、死亡 {n(deaths(cy))}人。" if cy else "")
                + "出生・死亡の男女比、自然増減、過去2年との比較、県・市別の地図。")
        foot = ("<div>出典：内政部戸政司オープンデータ「動態資料統計表」（村里別の毎月の出生数・死亡数を、本サイトで県・市別と台湾全体に集計）。"
                "数値は戸籍登録の月によるもので、実際に出生・死亡した月ではありません。毎日確認しており、通常は翌月上旬に前月分が発表されます。</div>\n"
                f"    <div>{i18n_ja.FOOT}</div>")
    elif KO:
        where = "대만" if name == "全台" else f"대만 {cname(name)}"
        title = f"{where} 출생·사망자 수: {ym_label(last)} 출생 {n(births(a))}명, 사망 {n(deaths(a))}명 | 대만 인구 동태 통계"
        desc = (f"내정부 호정사 최신 통계: {ym_label(last)} {where}의 출생아 수는 {n(births(a))}명, 사망자 수는 {n(deaths(a))}명."
                + (f" {y}년 1~{m}월 누계는 출생 {n(births(cy))}명, 사망 {n(deaths(cy))}명." if cy else "")
                + " 출생·사망 성비, 자연 증감, 최근 2년과의 비교, 시·현별 지도.")
        foot = ("<div>출처: 내정부 호정사 공공데이터 「동태자료통계표」(촌리별 월간 출생·사망자 수를 이 사이트에서 시·현별과 대만 전체로 합산). "
                "수치는 호적 등록 월 기준이며 실제 출생·사망 월이 아닙니다. 매일 확인하며, 보통 다음 달 초에 전월분이 발표됩니다.</div>\n"
                f"    <div>{i18n_ko.FOOT}</div>")
    else:
        where = "台灣" if name == "全台" else name
        title = f"{where}出生與死亡人數：{ym_label(last)}出生 {n(births(a))} 人、死亡 {n(deaths(a))} 人｜Taiwan Data 台灣數據"
        desc = (f"內政部戶政司最新統計：{ym_label(last)}{'全台' if name == '全台' else name}出生 {n(births(a))} 人、"
                f"死亡 {n(deaths(a))} 人。" + (f"{y} 年 1～{m} 月累計出生 {n(births(cy))} 人、死亡 {n(deaths(cy))} 人。" if cy else "")
                + "出生與死亡的男女比、自然增減、跟前兩年比較、各縣市地圖。")
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
