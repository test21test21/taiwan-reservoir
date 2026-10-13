"""航班頁、旅客人次頁共用的世界地圖：底圖 SVG、投影、「亞洲／全球」切換。

底圖由 scripts/build_world.py 產生（data/world-map.json）。地圖固定深灰底，和水庫地圖一樣，淺色深色主題都不變。
"""
import json
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TAIWAN = "158"
ASIA = (88, 47, 152, -11)  # 亞洲視角：西經界、北緯界、東經界、南緯界


@lru_cache(maxsize=1)
def world():
    return json.loads((ROOT / "data/world-map.json").read_text(encoding="utf-8"))


def xy(lat, lon):
    w = world()
    lon = (lon - w["lon0"]) % 360 + w["lon0"]
    return [round((lon - w["lon0"]) * w["k"] * w["s"], 1), round((w["lat0"] - lat) * w["s"], 1)]


def views():
    w = world()
    x0, y0 = xy(ASIA[1], ASIA[0])
    x1, y1 = xy(ASIA[3], ASIA[2])
    return {"asia": f"{x0} {y0} {round(x1 - x0, 1)} {round(y1 - y0, 1)}", "world": f"0 0 {w['width']} {w['height']}"}


def svg(id_, label, classes="", extra=""):
    """底圖；國家路徑帶 data-id（ISO 數字代碼），疊圖畫在 <g class="ov">。"""
    w = world()
    paths = "".join(f'<path data-id="{k}" class="c{" tw" if k == TAIWAN else ""}" d="{d}"/>' for k, d in w["countries"].items())
    v = views()
    return (f'<div class="wmwrap"><svg class="wm {classes}" id="{id_}" viewBox="{v["asia"]}" data-asia="{v["asia"]}" '
            f'data-world="{v["world"]}" preserveAspectRatio="xMidYMid meet" role="img" aria-label="{label}">'
            f'<rect class="sea" x="-500" y="-500" width="{w["width"] + 1000}" height="{w["height"] + 1000}"/>'
            f'<g class="land">{paths}</g><g class="ov"></g></svg>{extra}</div>')


CSS = """
.wmwrap { background:#1b1d20; border-radius:12px; overflow:hidden; margin-top:6px; position:relative; }
.wm { display:block; width:100%; height:min(112vw, 70vh, 620px); touch-action:manipulation; }
.wm.world { height:auto; aspect-ratio:1000/386; }
.wm .sea { fill:#1b1d20; }
.wm .c { fill:#2b2f33; stroke:rgba(255,255,255,.28); stroke-width:.5; vector-effect:non-scaling-stroke; stroke-linejoin:round; }
.wm .c.tw { fill:#5d656e; }
.wm text { font-family:inherit; fill:#e8eaed; paint-order:stroke; stroke:#1b1d20; stroke-width:3px; stroke-linejoin:round; pointer-events:none; }
.wmleg { display:flex; flex-wrap:wrap; gap:4px 12px; font-size:13px; color:var(--muted); margin-top:6px; align-items:center; }
.wmleg i { display:inline-block; width:14px; height:10px; border-radius:3px; margin-right:4px; vertical-align:-1px; }
.wmleg .ln { height:4px; border-radius:2px; }
.wminfo { margin-top:8px; font-size:14px; min-height:3.2em; }
.wminfo h3 { font-size:16px; margin:0 0 2px; }
.wminfo .muted { color:var(--muted); }
.seg { display:inline-flex; flex-wrap:wrap; border:1px solid var(--line); border-radius:999px; padding:2px; gap:2px; margin:2px 6px 6px 0; }
.seg button { font:inherit; font-size:14px; border:0; background:none; color:var(--muted); padding:4px 11px; white-space:nowrap; border-radius:999px; cursor:pointer; }
.seg button[aria-pressed="true"] { background:var(--fg); color:var(--bg); }
"""

JS = """<script>
// 世界地圖共用：亞洲／全球切換，以及「一個螢幕像素等於幾個 SVG 單位」（畫線、字用）
window.WM = {
  view: function (svg, v) {
    svg.setAttribute("viewBox", svg.getAttribute("data-" + v));
    svg.classList.toggle("world", v === "world");
    svg.dispatchEvent(new Event("wmview"));
  },
  unit: function (svg) {
    var vb = svg.viewBox.baseVal, r = svg.getBoundingClientRect();
    return Math.max(vb.width / (r.width || 1), vb.height / (r.height || 1));
  },
  el: function (tag, attrs) {
    var e = document.createElementNS("http://www.w3.org/2000/svg", tag);
    for (var k in attrs) e.setAttribute(k, attrs[k]);
    return e;
  },
  init: function (svg) {
    var box = svg.closest(".box");
    var start = box.getBoundingClientRect().width >= 700 ? "world" : "asia";
    box.querySelectorAll("[data-wmview] button").forEach(function (b) {
      b.setAttribute("aria-pressed", b.getAttribute("data-k") === start);
      b.addEventListener("click", function () {
        b.parentNode.querySelectorAll("button").forEach(function (x) { x.setAttribute("aria-pressed", x === b); });
        WM.view(svg, b.getAttribute("data-k"));
      });
    });
    WM.view(svg, start);
    var t; window.addEventListener("resize", function () { clearTimeout(t); t = setTimeout(function () { svg.dispatchEvent(new Event("wmview")); }, 150); });
  }
};
</script>"""
