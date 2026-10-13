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

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data/travel"
SITE = "https://taiwandata.info"
e = html.escape
EN = False
MON = bb.MON
PURPOSE_EN = {"業務": "Business", "觀光": "Leisure", "探親": "Visiting relatives", "會議": "Conferences", "求學": "Study",
              "展覽": "Exhibitions", "醫療": "Medical", "其他": "Other"}
PORT = {"飛機桃園": ("桃園機場", "Taoyuan Airport"), "飛機高雄": ("高雄機場", "Kaohsiung Airport"),
        "飛機松山": ("松山機場", "Songshan Airport"), "飛機臺中": ("台中機場", "Taichung Airport"),
        "輪船小計": ("搭船", "By sea"), "飛機其他": ("其他機場", "Other airports")}
EN_FIX = {"HongKong. Macao": "Hong Kong & Macau", "U.K.": "UK", "USA": "USA", "UAE": "UAE", "S. Africa": "South Africa",
          "Russian Federation": "Russia", "Macao": "Macau"}
ZH_FIX = {"阿拉伯聯合大公國": "阿聯", "香港.澳門": "港澳"}
TOP5 = ["#1f7ad6", "#e07b28", "#2e9e5b", "#8a55dd", "#d4508f"]


def tr(zh, en):
    return en if EN else zh


def n(x):
    return f"{x:,}"


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
"""

JS = """<script>
(function () {
  var EN = document.documentElement.lang === "en";
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
  sel.addEventListener("change", show);
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
    global EN
    if not (DATA / "totals.csv").exists():
        return []
    data = load()
    seg, airports = bf.load()[:2]
    urls = []
    for EN in (False, True):
        bb.EN = bf.EN = EN
        urls.append(page(out, head, nav, *data, seg, airports))
    EN = bb.EN = bf.EN = False
    return urls


def page(out, head, nav, inbound, outbound, totals, purpose, port, seg, airports):
    y = max(yy for yy, (i, o) in totals.items() if i and o)
    ti, to = totals[y]
    pi, po = totals.get(y - 1, (0, 0))
    pre = totals.get(2019)

    def one(label, cls, v, before, pre_v):
        rec = (f'<div class="yoy">{tr("疫情前 2019 年的", "")} <b>{v / pre_v * 100:.0f}%</b>{tr("", " of 2019, before Covid")}</div>'
               if pre_v and y > 2019 else "")
        return (f'<div><div class="k"><i style="background:var(--{cls})"></i>{label}</div>'
                f'<div class="v">{n(v)}<small>{tr("人次", "")}</small></div>'
                f'<div class="yoy">{tr("比前一年", "vs previous year")} <b>{pct(v, before)}</b></div>{rec}</div>')

    hero = (f'<section class="box"><h2>{tr(f"{y} 年全年", f"All of {y}")}</h2><div class="duo">'
            f'{one(tr("來台旅客", "Visitors to Taiwan"), "in", ti, pi, pre and pre[0])}'
            f'{one(tr("國人出國", "Taiwanese going abroad"), "out", to, po, pre and pre[1])}</div>'
            f'<p class="note">{tr("觀光署每年公布一次全年統計。", "Published once a year by the Tourism Administration.")}</p></section>')

    # 機場旅客（民航局，每月）
    latest = air_box = bars_box = ""
    months = sorted(p for p in seg if len(p) == 7)
    if months:
        last = months[-1]
        ly, lm = int(last[:4]), int(last[5:])
        x, prev = seg[last], seg.get(f"{ly - 1}-{lm:02d}")
        ytd = [seg[k] for k in months if k.startswith(f"{ly}-")]
        items = [(tr("國際", "International"), "intl", "pax_intl"), (tr("兩岸", "China"), "cross", "pax_cross"),
                 (tr("國內", "Domestic"), "dom", "pax_dom")]
        split = '<dl class="split">' + "".join(
            f'<div><dt><i style="background:var(--{c})"></i>{k}</dt><dd>{bf.wan(x[f])}</dd></div>' for k, c, f in items) + "</dl>"
        yoy = pct(x["pax"], prev and prev["pax"])
        latest = (f'<section class="box"><h2>{tr(f"{ly} 年 {lm} 月・全台機場旅客", f"{MON[lm - 1]} {ly}: passengers at Taiwan airports")}</h2>'
                  f'<div class="big">{n(x["pax"])}<small>{tr("人次", "")}</small></div>'
                  + (f'<div class="yoy">{tr("比去年同月", "vs a year earlier")} <b>{yoy}</b>・{tr(f"今年 1～{lm} 月", f"Jan–{MON[lm - 1]}")} <b>{n(sum(r["pax"] for r in ytd))}</b></div>' if yoy else "")
                  + split + f'<p class="note">{tr("含入境、出境及過境旅客；民航局每月公布。", "Arrivals, departures and transit; published monthly by the Civil Aeronautics Administration.")}</p></section>')
        air_box = (f'<section class="box"><h2>{tr(f"各機場旅客（{ly} 年 {lm} 月）", f"Passengers by airport ({MON[lm - 1]} {ly})")}</h2>'
                   f'<p class="note" style="margin:0 0 6px">{tr("右邊是比去年同月", "Right: change from a year earlier")}</p>'
                   f'<ul class="hbars in">{bf.airport_list(airports, last)}</ul></section>')
        recent = months[-24:]
        bars_box = (f'<section class="box"><h2>{tr("每月機場旅客", "Airport passengers per month")}</h2>'
                    f'<p class="legend"><i class="sq" style="background:var(--intl)"></i>{tr("國際", "International")}'
                    f'<i class="sq" style="background:var(--cross)"></i>{tr("兩岸", "China")}<i class="sq" style="background:var(--dom)"></i>{tr("國內", "Domestic")}</p>'
                    f'<p class="tip">{tr("滑過或點長條看當月數字", "Hover or tap a bar to see that month")}</p>'
                    f'<svg class="chart bd" viewBox="0 0 {bb.W} {bb.H}" role="img" aria-label="{tr("每月機場旅客人次", "Airport passengers per month")}">{bf.pax_bars(seg, recent)}</svg></section>')

    # 歷年趨勢
    yrs = [yy for yy in sorted(totals) if yy >= 1990 and yy <= y]
    tips = [tr(f"{yy} 年：來台 {n(totals[yy][0])}、出國 {n(totals[yy][1])}", f"{yy}: {n(totals[yy][0])} visitors, {n(totals[yy][1])} trips abroad") for yy in yrs]
    labels = [(i, str(yy)) for i, yy in enumerate(yrs) if (yy % 10 == 0 and yy < yrs[-1] - 4) or i == len(yrs) - 1]
    trend = bb.box(
        tr(f"歷年來台與出國人次（{yrs[0]}～{y}）", f"Visitors and trips abroad, {yrs[0]}–{y}"),
        f'<p class="legend"><span class="k b"></span>{tr("來台旅客", "Visitors to Taiwan")}<span class="k d"></span>{tr("國人出國", "Taiwanese abroad")}</p>',
        bb.lines_chart(len(yrs), [("b", [totals[yy][0] for yy in yrs]), ("d", [totals[yy][1] for yy in yrs])], labels, tips, zero=True),
        tr("歷年來台旅客與國人出國人次折線圖", "Visitors to Taiwan and trips abroad by year"),
        tr("滑過或點圖看每年數字", "Hover or tap the chart to see each year")).replace(" 萬<", "萬<")

    # 名稱對照（中文頁顯示中文，英文頁顯示英文）
    names = {}
    for d in (inbound, outbound):
        for yy in d:
            for p in d[yy]:
                names[p] = split_name(p)[1 if EN else 0]
    for k in PURPOSE_EN:
        names[k] = PURPOSE_EN[k] if EN else k
    for k, (zh, en) in PORT.items():
        names[k] = en if EN else zh

    def only(d):
        return {yy: {p: v for p, v in d[yy].items() if countable(p)} for yy in d}
    ib, ob = only(inbound), only(outbound)
    years = sorted(set(ib) & set(ob), reverse=True)
    pick = (f'<div class="yearpick"><label for="ypick">{tr("看哪一年：", "Year:")}</label><select id="ypick">'
            + "".join(f'<option value="{yy}"{" selected" if yy == y else ""}>{yy}</option>' for yy in years)
            + f'</select><span>{tr("下面四張圖跟著換；右邊是比前一年", "The four charts below follow; right column is change from the year before")}</span></div>')

    def hbox(title, key, d, cls, limit, note=""):
        return (f'<section class="box"><h2>{title}（<span class="j-year">{y}</span>）</h2>'
                f'<ul class="hbars {cls}" data-set="{key}" data-n="{limit}">{bars_html(d.get(y, {}), d.get(y - 1), names, limit)}</ul>'
                + (f'<p class="note">{note}</p>' if note else "") + "</section>")

    blocks = [
        hbox(tr("來台旅客從哪裡來", "Where visitors come from"), "in", ib, "in", 15, tr("依旅客居住地。", "By country of residence.")),
        hbox(tr("國人出國去哪裡", "Where Taiwanese travel"), "out", ob, "out", 15, tr("依出國後第一站抵達的地方。", "By first destination after leaving Taiwan.")),
        hbox(tr("來台目的", "Why visitors come"), "purpose", purpose, "in", 8),
        hbox(tr("從哪裡入境", "Where visitors arrive"), "port", port, "in", 6),
    ]

    # 主要來源地近 10 年
    top = sorted(ib.get(y, {}).items(), key=lambda x: -x[1])[:5]
    ys = [yy for yy in range(y - 10, y + 1) if yy in ib]
    series = [(f"c{i}", [ib[yy].get(p) for yy in ys]) for i, (p, _) in enumerate(top)]
    tips = [tr(f"{yy} 年：", f"{yy}: ") + tr("、", ", ").join(f"{names[p]} {n(ib[yy].get(p, 0))}" for p, _ in top) for yy in ys]
    style = "".join(f".bd .line.c{i} {{ stroke:{c}; }}" for i, c in enumerate(TOP5))
    legend = '<p class="legend">' + "".join(f'<span class="sw" style="border-color:{TOP5[i]}"></span>{names[p]}' for i, (p, _) in enumerate(top)) + "</p>"
    blocks.append(bb.box(tr(f"前五大來源地：近 {len(ys)} 年", f"Top five source markets, last {len(ys)} years"), legend,
                         bb.lines_chart(len(ys), series, [(i, str(yy)) for i, yy in enumerate(ys) if i % 2 == 0 or i == len(ys) - 1], tips, zero=True),
                         tr("前五大來台旅客來源地歷年人次", "Visitors from the top five markets by year"),
                         tr("滑過或點圖看每年數字", "Hover or tap the chart to see each year")))

    pj = {"names": names, "in": ib, "out": ob, "purpose": purpose, "port": port}
    path = "tourism/"
    zh_url, en_url = f"{SITE}/{path}", f"{SITE}/en/{path}"
    top3 = "、".join(names[p] for p, _ in top[:3]) if not EN else ", ".join(names[p] for p, _ in top[:3])
    if EN:
        title = f"Taiwan Tourism and Travellers {y}: {ti / 1e6:.2f}M Visitors, {to / 1e6:.2f}M Trips Abroad | Taiwan Data"
        desc = (f"Taiwan welcomed {n(ti)} visitors in {y} ({pct(ti, pi)}) and Taiwanese made {n(to)} trips abroad ({pct(to, po)}). "
                f"Top markets: {top3}. Visitors by country, purpose and port of entry, destinations of Taiwanese travellers, and trends since {yrs[0]}.")
        foot = ("<div>Sources: Tourism Administration, Ministry of Transportation and Communications, tourism statistics open data (yearly); "
                "monthly airport passengers from the Civil Aeronautics Administration. Checked daily.</div>\n"
                "    <div>An independent site, not affiliated with the government. All figures come from government open data.</div>")
    else:
        title = f"台灣旅客人次：{y} 年來台 {ti / 1e4:,.0f} 萬人次、出國 {to / 1e4:,.0f} 萬人次｜Taiwan Data 台灣數據"
        desc = (f"觀光署最新統計：{y} 年來台旅客 {n(ti)} 人次（{pct(ti, pi)}），國人出國 {n(to)} 人次（{pct(to, po)}）。"
                f"各機場旅客、主要來源地{top3}；來台目的、入境港口、國人出國目的地與 {yrs[0]} 年以來趨勢。")
        foot = ("<div>資料來源：交通部觀光署觀光統計開放資料（每年）；每月機場旅客來自交通部民用航空局。每天檢查一次。</div>\n"
                "    <div>本站為個人經營，非政府網站；所有數據皆來自政府開放資料。</div>")
    html_ = f"""{head(title, desc, en_url if EN else zh_url, "og.png", "en" if EN else "zh", (zh_url, en_url))}
<body>
<style>{CSS}{style}</style>
{nav("en" if EN else "zh", "/" + path if EN else "/en/" + path)}
<div class="wrap">
  <div class="top">{latest}{hero}</div>
  <div class="grid">{air_box}{bars_box}{trend}{blocks[-1]}</div>
  {pick}
  <div class="grid">{"".join(blocks[:-1])}</div>
  <footer>
    {foot}
  </footer>
</div>
<script type="application/json" id="tv-data">{json.dumps(pj, ensure_ascii=False, separators=(",", ":"))}</script>
{JS}
</body>
</html>
"""
    d = Path(out) / ("en" if EN else "") / path
    d.mkdir(parents=True, exist_ok=True)
    (d / "index.html").write_text(html_, encoding="utf-8")
    return en_url if EN else zh_url
