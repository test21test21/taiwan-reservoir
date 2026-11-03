"""全站配色：2026-11-03 Shane 改用第 10 組 Tableau 10（原本的備案）。
原因：第 16 組「大地」顏色太接近，折線、長條分不清楚（尤其深色模式）。
現在的備案是第 16 組「大地」（Coolors 582f0e 936639 b6ad90 a4ac86 414833，見 EARTH）。

不在這裡、也不能改的顏色：
- 水情：水庫水杯、地圖蓄水率分級、藍色系（build_pages.py TANK、reservoir/index.html）
- 官方燈號：水利署水情燈號、台電備轉容量率燈號
- 增減：▲ 綠 / ▼ 紅

圖表上的年份全站一致：今年藍、去年橘、前年綠（出生頁、電力頁）。
"""

# 五個主題各一色（首頁那一列、各頁的主色）
SECTION = {
    "reservoir": "#4e79a7",  # 藍
    "power": "#edc948",      # 黃
    "births": "#e15759",     # 紅
    "flights": "#76b7b2",    # 青綠
    "tourism": "#f28e2b",    # 橘
}

# Tableau 10 全部十色，頁面裡需要更多顏色時從這裡拿
TABLEAU = ["#4e79a7", "#f28e2b", "#e15759", "#76b7b2", "#59a14f",
           "#edc948", "#b07aa1", "#ff9da7", "#9c755f", "#bab0ac"]

# 備案：第 16 組「大地」的 Coolors 漸層
EARTH = ["#582f0e", "#7f4f24", "#936639", "#a68a64", "#b6ad90",
         "#c2c5aa", "#a4ac86", "#656d4a", "#414833", "#333d29"]


def _rgb(h):
    return [int(h[i:i + 2], 16) for i in (1, 3, 5)]


def mix(a, b, t):
    """a 和 b 混色，t=0 是 a，t=1 是 b。"""
    return "#" + "".join(f"{round(x * (1 - t) + y * t):02x}" for x, y in zip(_rgb(a), _rgb(b)))


def tint(c, t):
    return mix(c, "#ffffff", t)


def shade(c, t):
    return mix(c, "#000000", t)


def luminance(c):
    def ch(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(v) for v in _rgb(c))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def is_light(c):
    return luminance(c) > 0.45


def on(c):
    """放在這個顏色上的圖示／字用黑還是白。"""
    return "#111111" if is_light(c) else "#ffffff"


def dark(c):
    """深色模式：太深的顏色在黑底上看不到，調亮一點。"""
    return tint(c, 0.45) if luminance(c) < 0.12 else tint(c, 0.25) if luminance(c) < 0.3 else c


def bar_tint(c):
    """首頁小長條圖：舊的長條用淡色，最新一根用原色。"""
    return tint(c, 0.3 if luminance(c) > 0.6 else 0.45 if is_light(c) else 0.62)
