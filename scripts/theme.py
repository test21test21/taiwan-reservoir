"""全站配色：2026-11-02 Shane 選定第 16 組「大地」（Coolors 熱門漸層 582f0e … 333d29 取五色）。
備案是第 10 組 Tableau（4e79a7 edc948 e15759 76b7b2 f28e2b）。

不在這裡、也不能改的顏色：
- 水情：水庫水杯、地圖蓄水率分級、藍色系（build_pages.py TANK、reservoir/index.html）
- 官方燈號：水利署水情燈號、台電備轉容量率燈號
- 增減：▲ 綠 / ▼ 紅
"""

# 五個主題各一色（首頁那一列、各頁的主色）
SECTION = {
    "reservoir": "#582f0e",  # 深咖啡
    "power": "#936639",      # 銅褐
    "births": "#b6ad90",     # 卡其
    "flights": "#a4ac86",    # 鼠尾草綠
    "tourism": "#414833",    # 深橄欖
}

# 同一條 Coolors 漸層的十個顏色（深咖啡 → 卡其 → 橄欖），頁面裡需要更多顏色時從這裡拿
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
