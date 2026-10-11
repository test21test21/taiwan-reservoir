"""出生與死亡頁：/births/（全台）和 /births/<縣市>/（22 縣市各一頁），數字和圖直接寫進 HTML。

資料：data/births/monthly.csv（scripts/fetch_births.py 從內政部戶政司抓的各縣市每月出生、死亡數）
build_pages.py 部署時呼叫 build(out, head, nav)。
"""
import csv
import html
from collections import defaultdict
from pathlib import Path

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

# 出生藍、死亡橘；男藍、女粉（色盲也分得出來；深色模式另一組）
CSS = """
:root { --birth:#1f7ad6; --death:#cf6526; --male:#2a7fd4; --female:#d4508f; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --birth:#3d8fdb; --death:#d0702c; --male:#4a90e2; --female:#d9609b; } }
:root[data-theme="dark"] { --birth:#3d8fdb; --death:#d0702c; --male:#4a90e2; --female:#d9609b; }
.wrap { max-width:1840px; padding-inline:max(16px, env(safe-area-inset-left)) max(16px, env(safe-area-inset-right)); }
.top, .grid { display:grid; gap:12px; align-items:start; }
.top > .box, .grid > .box { margin-top:12px; }
.top { margin-top:0; }
@media (min-width:860px) { .top { grid-template-columns:1fr 1fr; } .grid { grid-template-columns:1fr 1fr; } .top, .grid { column-gap:16px; row-gap:0; } }
@media (min-width:1360px) { .grid { grid-template-columns:1fr 1fr 1fr; } }
.chart.bd { max-height:none; }
.pick { display:flex; align-items:center; gap:8px; margin:4px 0 0; height:44px; font-size:15px; }
.pick select { font:inherit; font-size:16px; padding:6px 10px; border-radius:10px; border:1px solid var(--line); background:var(--surface); color:var(--fg); }
.duo { display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-top:8px; }
.duo .k { font-size:15px; font-weight:700; display:flex; align-items:center; gap:6px; }
.duo .k i, .sex i { width:10px; height:10px; border-radius:50%; display:inline-block; }
.duo .v { font-size:clamp(28px,8.4vw,52px); white-space:nowrap; font-weight:700; line-height:1.1; }
.duo .v small { font-size:16px; color:var(--muted); font-weight:500; margin-left:2px; }
.duo .yoy, .duo .sex { font-size:14px; color:var(--muted); }
.duo .yoy b { font-weight:500; color:var(--fg); }
.sex { display:flex; flex-wrap:wrap; gap:2px 10px; }
.sex span { display:inline-flex; align-items:center; gap:4px; }
.gap { margin:14px 0 0; padding-top:12px; border-top:1px solid var(--line); font-size:16px; }
.gap b { font-size:20px; }
.bd .line.b { stroke:var(--birth); }
.bd .line.d { stroke:var(--death); }
.bd .line.ly { stroke:var(--muted); stroke-width:2; stroke-dasharray:5 4; }
.bd .line.l2 { stroke:var(--muted); stroke-width:1.5; stroke-dasharray:1.5 4; opacity:.8; }
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
.legend .k.ly { border-top:2px dashed var(--muted); }
.legend .k.l2 { border-top:2px dotted var(--muted); }
.legend .sq { width:12px; height:12px; border-radius:3px; display:inline-block; margin-left:8px; }
.legend .sq:first-child { margin-left:0; }
.tw .neg { color:var(--muted); }
.tw a { font-weight:500; }
.tw tr.me td { background:var(--chip); font-weight:700; }
.note { font-size:13px; color:var(--muted); margin:8px 0 0; }
.tip { font-size:13px; color:var(--muted); margin:2px 0 0; min-height:1.6em; }
"""

# 滑過／點圖上的長條或點，在圖上方顯示那一期的數字（每個 .hit 帶 data-tip）
JS = """<script>
document.querySelectorAll("svg.bd").forEach(function (svg) {
  var tip = svg.previousElementSibling, def = tip.textContent;
  svg.querySelectorAll(".hit").forEach(function (h) {
    function on() { tip.textContent = h.getAttribute("data-tip"); }
    h.addEventListener("mouseenter", on); h.addEventListener("focus", on); h.addEventListener("click", on);
    h.addEventListener("mouseleave", function () { tip.textContent = def; });
  });
});
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


def n(x):
    return f"{x:,}"


def pct(now, before):
    if not before:
        return ""
    d = (now - before) / before * 100
    arrow = "▲" if d > 0 else "▼" if d < 0 else "▶"
    return f"{arrow} {abs(d):.1f}%"


def ym_label(ym):
    return f"{int(ym[:4])} 年 {int(ym[5:])} 月"


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
    lo = (lo // step) * step
    hi = -(-hi // step) * step
    if hi == lo:
        hi = lo + step
    return lo, hi, step


def short(v):
    v = int(v)
    if v >= 10000:
        return f"{v / 10000:g} 萬"
    return n(v)


W, H, L, R, T, B = 420, 230, 50, 14, 12, 26


def frame(lo, hi, step, Y):
    out, g = "", lo
    while g <= hi + 1e-9:
        out += (f'<line x1="{L}" x2="{W - R}" y1="{Y(g):.1f}" y2="{Y(g):.1f}" class="g"/>'
                f'<text x="{L - 5}" y="{Y(g) + 4:.1f}" text-anchor="end">{short(g)}</text>')
        g += step
    return out


def xlabels(X, labels):
    k = max(i for i, _ in labels) if labels else 0
    return "".join(
        f'<text x="{X(i):.1f}" y="{H - 8}" text-anchor="{"start" if i == 0 and X(i) - L < 12 else "end" if i == k and W - R - X(i) < 12 else "middle"}">{t}</text>'
        for i, t in labels)


def box(title, legend, svg, aria, default_tip, extra=""):
    return (f'<section class="box"><h2>{title}</h2>{legend}<p class="tip">{e(default_tip)}</p>'
            f'<svg class="chart bd" viewBox="0 0 {W} {H}" role="img" aria-label="{e(aria)}">{svg}</svg>{extra}</section>')


def lines_chart(n_x, series, labels, tips, zero=False, end_labels=None):
    """series：[(class, [值或 None]*n_x)]；labels：[(索引, 文字)]；tips：每個 x 的說明文字。"""
    vals = [v for _, s in series for v in s if v is not None]
    lo, hi, step = nice_scale(min(vals), max(vals), zero=zero)
    k = max(1, n_x - 1)
    X = lambda i: L + (W - L - R - (34 if end_labels else 0)) * i / k
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
        f'data-tip="{ym_label(mm)}：出生 {n(births(a_of(mm)))} 人（男 {n(a_of(mm)[0])}、女 {n(a_of(mm)[1])}）"/>'
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

    def gap_line(b, dd, lead):
        g = b - dd
        if g < 0:
            return f'<p class="gap">{lead}死亡比出生多 <b>{n(-g)}</b> 人，人口自然減少</p>'
        return f'<p class="gap">{lead}出生比死亡多 <b>{n(g)}</b> 人，人口自然增加</p>'

    def duo(a, la, cmp):
        def one(key, cls, v, before, sex):
            yoy = f'<div class="yoy">比{cmp} <b>{pct(v, before)}</b></div>' if before else ""
            return (f'<div><div class="k"><i style="background:var(--{cls})"></i>{key}</div>'
                    f'<div class="v">{n(v)}<small>人</small></div>'
                    f'<div class="sex"><span><i style="background:var(--male)"></i>男 {n(sex[0])}</span>'
                    f'<span><i style="background:var(--female)"></i>女 {n(sex[1])}</span></div>{yoy}</div>')
        return (f'<div class="duo">{one("出生", "birth", births(a), la and births(la), a[0:2])}'
                f'{one("死亡", "death", deaths(a), la and deaths(la), a[2:4])}</div>')

    where = "" if name == "全台" else name + " "
    out = [f'<section class="box"><h2>{where}{ym_label(last)}</h2>{duo(a, la, "去年同月")}'
           f'{gap_line(births(a), deaths(a), "這個月")}</section>']
    cy, ly = ytd(y), ytd(y - 1)
    if m > 1 and cy:
        out.append(f'<section class="box"><h2>{where}{y} 年 1～{m} 月累計</h2>{duo(cy, ly, "去年同期")}'
                   f'{gap_line(births(cy), deaths(cy), "今年到目前，")}</section>')

    # 1. 每月出生（男女）
    recent = months[-24:]
    out.append(box(
        f"每月出生人數（男女）", '<p class="legend"><i class="sq" style="background:var(--male)"></i>男'
        '<i class="sq" style="background:var(--female)"></i>女</p>',
        stacked_bars(recent, get, month_ticks(recent)), f"{where}最近 {len(recent)} 個月每月出生人數，分男女",
        "滑過或點長條看當月數字"))

    # 2、3. 今年 vs 去年 vs 前年（1～12 月）
    def yoy_chart(title, fn, cls, word):
        yrs = [yy for yy in (y, y - 1, y - 2) if any(f"{yy}-{i:02d}" in d for i in range(1, 13))]
        series = []
        for yy, c in zip(yrs, (cls, "ly", "l2")):
            series.append((c, [fn(d[f"{yy}-{i:02d}"]) if f"{yy}-{i:02d}" in d else None for i in range(1, 13)]))
        legend = '<p class="legend">' + "".join(
            f'<span class="k {c}"></span>{yy} 年' for yy, c in zip(yrs, (cls, "ly", "l2"))) + "</p>"
        tips = []
        for i in range(1, 13):
            parts = [f"{yy} 年 {n(fn(d[f'{yy}-{i:02d}']))}" for yy in yrs if f"{yy}-{i:02d}" in d]
            tips.append(f"{i} 月{word}：" + "、".join(parts))
        labels = [(i - 1, f"{i}月") for i in (1, 3, 5, 7, 9, 11)]
        return box(title, legend, lines_chart(12, series, labels, tips), f"{where}{title}折線圖",
                   "滑過或點圖看每月數字")
    out.append(yoy_chart("每月出生：跟前兩年比", births, "b", "出生"))
    out.append(yoy_chart("每月死亡：跟前兩年比", deaths, "d", "死亡"))

    # 4. 最近 36 個月出生 vs 死亡
    recent = months[-36:]
    out.append(box(
        f"出生與死亡：最近 {len(recent)} 個月", '<p class="legend"><span class="k b"></span>出生<span class="k d"></span>死亡</p>',
        lines_chart(len(recent), [("b", [births(get(mm)) for mm in recent]), ("d", [deaths(get(mm)) for mm in recent])],
                    month_ticks(recent), [f"{ym_label(mm)}：出生 {n(births(get(mm)))}、死亡 {n(deaths(get(mm)))}" for mm in recent],
                    end_labels={"b": "出生", "d": "死亡"}),
        f"{where}最近 {len(recent)} 個月每月出生與死亡人數折線圖", "滑過或點圖看每月數字"))

    # 5. 每年合計：只算 12 個月都有資料的年份（官方開放資料缺 2022 年 3 月，那年留空）
    years = sorted({mm[:4] for mm in months})
    full = {yy for yy in years if all(f"{yy}-{i:02d}" in d for i in range(1, 13))}
    span = [yy for yy in years if min(full, default="9") <= yy <= max(full, default="0")]
    if len(full) >= 3:
        tot = {yy: [sum(d[f"{yy}-{i:02d}"][j] for i in range(1, 13)) for j in range(4)] for yy in sorted(full)}
        missing = [yy for yy in span if yy not in full]
        table = "".join(
            f'<tr><td>{yy}</td><td class="n">{n(births(t))}</td><td class="n">{n(deaths(t))}</td>'
            f'<td class="n{" neg" if births(t) < deaths(t) else ""}">{"+" if births(t) >= deaths(t) else "−"}{n(abs(births(t) - deaths(t)))}</td></tr>'
            for yy, t in reversed(tot.items()))
        table = (f'<details><summary>看每年數字</summary><table class="tw"><tr><th>年份</th><th class="n">出生</th>'
                 f'<th class="n">死亡</th><th class="n">出生減死亡</th></tr>{table}</table></details>')
        if missing:
            table = (f'<p class="note">{"、".join(missing)} 年官方開放資料缺少部分月份（例如 2022 年 3 月），'
                     f'算不出全年合計，所以留空。</p>' + table)
        out.append(box(
            "每年出生與死亡", '<p class="legend"><span class="k b"></span>出生<span class="k d"></span>死亡</p>',
            lines_chart(len(span), [("b", [births(tot[yy]) if yy in tot else None for yy in span]),
                                    ("d", [deaths(tot[yy]) if yy in tot else None for yy in span])],
                        [(i, yy if i in (0, len(span) - 1) else f"'{yy[2:]}") for i, yy in enumerate(span) if i != 1],
                        [f"{yy} 年：出生 {n(births(tot[yy]))}、死亡 {n(deaths(tot[yy]))}" if yy in tot
                         else f"{yy} 年：缺少部分月份" for yy in span],
                        end_labels={"b": "出生", "d": "死亡"}),
            f"{where}{span[0]}～{span[-1]} 年每年出生與死亡人數折線圖", "滑過或點圖看每年數字", table))
    return out, last, a, cy


def county_table(data, last, current="全台", prefix=""):
    y, m = int(last[:4]), int(last[5:])
    rows = []
    for c, slug in COUNTIES:
        dd = data.get(c, {})
        t = [sum(dd[f"{y}-{i:02d}"][j] for i in range(1, m + 1) if f"{y}-{i:02d}" in dd) for j in range(4)]
        rows.append((c, slug, births(t), deaths(t)))
    span = f"{y} 年 1～{m} 月" if m > 1 else ym_label(last)
    body = "".join(
        f'<tr{" class=\"me\"" if c == current else ""}><td><a href="{prefix}{slug}/">{e(c)}</a></td><td class="n">{n(b)}</td><td class="n">{n(dd)}</td>'
        f'<td class="n{" neg" if b < dd else ""}">{"+" if b >= dd else "−"}{n(abs(b - dd))}</td></tr>'
        for c, slug, b, dd in sorted(rows, key=lambda x: -x[2]))
    return (f'<section class="box"><h2>各縣市（{span}累計）</h2><table class="tw">'
            f'<tr><th>縣市</th><th class="n">出生</th><th class="n">死亡</th><th class="n">出生減死亡</th></tr>{body}</table>'
            f'<p class="note">依出生人數排序，點縣市名稱看該縣市的圖。</p></section>')


def picker(current, prefix):
    opts = f'<option value="{prefix}"{" selected" if current == "全台" else ""}>全台</option>' + "".join(
        f'<option value="{prefix}{slug}/"{" selected" if c == current else ""}>{c}</option>' for c, slug in COUNTIES)
    return (f'<label class="pick">看哪裡：<select onchange="location.href=this.value" aria-label="選縣市">{opts}</select></label>')


def build(out, head, nav):
    if not DATA.exists():
        return []
    data = load()
    urls = []
    for name, slug in [("全台", "")] + COUNTIES:
        if name not in data:
            continue
        blocks, last, a, cy = page_body(name, data[name])
        y, m = int(last[:4]), int(last[5:])
        where = "台灣" if name == "全台" else name
        title = f"{where}出生與死亡人數：{ym_label(last)}出生 {n(births(a))} 人、死亡 {n(deaths(a))} 人｜Taiwan Data 台灣數據"
        desc = (f"內政部戶政司最新統計：{ym_label(last)}{'全台' if name == '全台' else name}出生 {n(births(a))} 人、"
                f"死亡 {n(deaths(a))} 人。" + (f"{y} 年 1～{m} 月累計出生 {n(births(cy))} 人、死亡 {n(deaths(cy))} 人。" if cy else "")
                + "每月出生男女、跟前兩年比較、歷年趨勢。")
        url = f"{SITE}/births/{slug + '/' if slug else ''}"
        prefix = "" if not slug else "../"
        extra = county_table(data, last, name, prefix)
        page = f"""{head(title, desc, url, "og.png")}
<body>
<style>{CSS}</style>
{nav(prefix)}
<div class="wrap">
  {picker(name, prefix)}
  <div class="top">{"".join(blocks[:2])}</div>
  <div class="grid">{"".join(blocks[2:])}{extra}</div>
  <footer>
    <div>資料來源：內政部戶政司開放資料「動態資料統計表」（各村里每月出生、死亡數，本站加總成縣市與全台）。數字依戶籍登記月份計算，不是實際出生或死亡的月份；每天檢查一次，通常每月上旬公布上個月。</div>
    <div>本站為個人經營，非政府網站；所有數據皆來自政府開放資料。</div>
  </footer>
</div>
{JS}
</body>
</html>
"""
        d = Path(out) / "births" / slug
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(page, encoding="utf-8")
        urls.append(url)
    return urls
