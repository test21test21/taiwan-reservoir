"""首頁「台灣概覽」：左邊是位置與基本資料（東亞地圖、人口），右邊是各主題的最新數字表。

build_pages.py 每小時呼叫 build(out)，數字直接寫進 HTML（搜尋引擎看得到，也不必等 JavaScript）。
每一列的數字和該主題頁的標題一致：水庫用 21 座主要水庫的有效容量加權蓄水率，電力用台電即時發電合計，
出生用戶政司最新月份，航班用民航局國際及兩岸定期航班載客率，旅客用觀光署年度來台旅客。
"""
import calendar
import csv
import json
from collections import defaultdict
from datetime import datetime
from html import escape as e
from pathlib import Path

import theme
import worldmap

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "data"
# 水利署的主要水庫（總覽頁地圖標名字的那一群再加上各區主力），蓄水率依有效容量加權
MAJOR = {"10201", "10205", "10401", "10405", "10501", "10601", "20101", "20201", "20202", "20501", "20502",
         "20503", "20509", "30301", "30401", "30501", "30502", "30503", "30802", "30901", "31201"}
FUELS = ["nuclear", "coal", "lng", "cogen", "oil", "solar", "wind", "hydro", "other", "storage"]


def rows(p):
    with open(D / p, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def data():
    """首頁要的數字（只用官方資料）。"""
    out = {}
    lat = json.loads((D / "latest.json").read_text(encoding="utf-8"))
    maj = [r for r in lat["reservoirs"] if r["id"] in MAJOR and r.get("percent") is not None
           and r["percent"] >= 0 and not r.get("suspect") and r.get("capacity")]
    cap = sum(r["capacity"] for r in maj)
    ly = [r for r in maj if r.get("last_year_percent") is not None]
    daily = defaultdict(lambda: [0.0, 0.0])
    for r in rows("history.csv"):
        if r["id"] in MAJOR and r["percent"] and r["capacity"] and float(r["percent"]) >= 0:
            daily[r["date"]][0] += float(r["percent"]) * float(r["capacity"])
            daily[r["date"]][1] += float(r["capacity"])
    days = sorted(daily)[-30:]
    out["reservoir"] = dict(
        pct=sum(r["percent"] * r["capacity"] for r in maj) / cap,
        last_year=sum(r["last_year_percent"] * r["capacity"] for r in ly) / sum(r["capacity"] for r in ly) if ly else None,
        when=max(r["observed_at"] for r in maj), count=len(maj),
        spark=[daily[d][0] / daily[d][1] for d in days])

    pw = json.loads((D / "power/latest.json").read_text(encoding="utf-8"))
    rv = rows("power/reserve.csv")[-1]
    today = pw["time"][:10]
    hourly = D / f"power/hourly/{today[:7]}.csv"
    curve = [sum(float(r[f] or 0) for f in FUELS) / 10 for r in rows(hourly.relative_to(D)) if r["time"].startswith(today)] if hourly.exists() else []
    rate = float(rv["rate"])
    out["power"] = dict(now=sum((u["mw"] or 0) for u in pw["units"]) / 10, when=pw["time"], rate=rate, rate_date=rv["date"],
                        light="green" if rate >= 10 else "yellow" if rate >= 6 else "orange", spark=curve)

    B, Dd, P = defaultdict(int), defaultdict(int), defaultdict(int)
    for r in rows("births/monthly.csv"):
        m = r["month"]
        B[m] += int(r["births_m"]) + int(r["births_f"])
        Dd[m] += int(r["deaths_m"]) + int(r["deaths_f"])
        P[m] += int(r["population"])
    ms = sorted(B)
    last = ms[-1]
    ago = f"{int(last[:4]) - 1}{last[4:]}"
    out["births"] = dict(month=last, births=B[last], deaths=Dd[last], yoy=(B[last] / B[ago] - 1) * 100 if B.get(ago) else None,
                         spark=[B[m] for m in ms[-24:]])
    out["population"] = dict(month=last, pop=P[last], year_change=P[last] - P[ago] if P.get(ago) else None)

    lf = [r for r in rows("flights/loadfactor.csv") if r["scope"] == "ALL" and r["region"] == "all"]
    out["flights"] = dict(month=lf[-1]["month"], lf=float(lf[-1]["lf"]), pax=int(lf[-1]["pax"]),
                          prev=float(lf[-2]["lf"]) if len(lf) > 1 else None, spark=[float(r["lf"]) for r in lf])

    tot = [r for r in rows("travel/totals.csv") if r["inbound"]]
    cur, prev = tot[-1], tot[-2]
    out["travel"] = dict(year=cur["year"], inbound=int(cur["inbound"]), outbound=int(cur["outbound"] or 0),
                         yoy=(int(cur["inbound"]) / int(prev["inbound"]) - 1) * 100,
                         spark=[int(r["inbound"]) for r in tot if int(r["year"]) >= 2010])
    out["generated_at"] = lat.get("generated_at")
    return out


# ---------- 文字（四種語言）
T = {
    "zh": dict(
        title="Taiwan Data 台灣數據：用數據看台灣，水庫、電力、人口、航班的最新數字",
        desc="台灣最新的官方數字：主要水庫蓄水率、現在用電、每月出生人數、航班載客率、來台旅客人次。",
        eyebrow="TAIWAN DATA", h1="用數據看台灣", lead="水庫、電力、人口、航班、旅客的最新官方數字。",
        updated="資料更新", meta_src="資料來源：政府開放資料", meta_freq="每小時自動更新", ctx="地圖", tbl="探索台灣數據",
        f_loc=("位置", "東亞・西太平洋"), f_tz=("時區", "UTC+8"), f_pop="人口", f_div=("行政區", "22 個縣市"),
        pop_fmt=lambda p: f"{p / 1e4:,.1f}<small> 萬人</small>", pop_when=lambda m: f"{m[:4]} 年 {int(m[5:])} 月底・內政部戶政司",
        pop_chg=lambda c: f"比一年前{'少' if c < 0 else '多'} {abs(c) / 1e4:.1f} 萬人",
        map_label="台灣在東亞的位置", inset="台灣本島", names={"156": "中國", "392": "日本", "410": "韓國", "608": "菲律賓", "158": "台灣", "sea": "太平洋"},
        km="公里",
        rows={
            "reservoir": ("台灣水庫水情", "蓄水率與水情燈號地圖", "主要水庫蓄水率", "近 30 天"),
            "power": ("台灣今日電力", "用電、備轉容量率與發電來源", "現在用電", "今天"),
            "births": ("台灣出生與死亡", "各縣市比較與歷年趨勢", "出生人數", "近 24 個月"),
            "flights": ("台灣航班", "航線、航空公司與載客率", "國際及兩岸載客率", "今年各月"),
            "travel": ("台灣旅客人次", "來台旅客、出國人次與機場", "來台旅客", "2010 年起"),
        },
        fmt_power=lambda v: f"{v:,.0f}<small>萬瓩</small>", fmt_people=lambda n: f"{n:,}<small>人</small>",
        fmt_wan=lambda n: f"{n / 1e4:,.0f}<small>萬</small>", unit_pt=" 個百分點",
        lights=dict(green="綠燈", yellow="黃燈", orange="橘燈"), reserve="備轉容量率",
        vs_ly="比去年同期", vs_lm="比上月", vs_ly_m="比去年同月", vs_py="比前一年",
        when_dt=lambda t: f"{t.month}/{t.day} {t:%H:%M}", when_m=lambda m: f"{m[:4]} 年 {int(m[5:])} 月", when_y=lambda y: f"{y} 年",
        src_t="資料來源", src="經濟部水利署、台灣電力公司、內政部戶政司、交通部民用航空局、交通部觀光署的開放資料。",
        about_t="關於本站", about="整理台灣政府開放資料，數字都標明資料時間。", about_link="關於本站",
        ng_t="非政府網站", ng="本站為個人經營，和任何政府機關沒有關係。", contact="歡迎來信：contact@taiwandata.info"),
    "en": dict(
        title="Taiwan Data: Taiwan at a Glance, the Latest Reservoir, Power, Population and Flight Figures",
        desc="The latest official figures for Taiwan: major reservoir storage, current power demand, monthly births, flight load factors and visitor arrivals.",
        eyebrow="TAIWAN DATA", h1="Taiwan at a Glance", lead="The latest official figures for Taiwan's reservoirs, electricity, population, flights and tourism.",
        updated="Updated", meta_src="Source: Taiwan government open data", meta_freq="Updated hourly", ctx="Map", tbl="Explore Taiwan data",
        f_loc=("Location", "East Asia, Western Pacific"), f_tz=("Time zone", "UTC+8"), f_pop="Population", f_div=("Divisions", "22 counties and cities"),
        pop_fmt=lambda p: f"{p / 1e6:,.2f}<small> million</small>",
        pop_when=lambda m: f"End of {calendar.month_name[int(m[5:])]} {m[:4]} · Ministry of the Interior",
        pop_chg=lambda c: f"{'Down' if c < 0 else 'Up'} {abs(c):,} from a year earlier",
        map_label="Taiwan's location in East Asia", inset="Main island",
        names={"156": "China", "392": "Japan", "410": "South Korea", "608": "Philippines", "158": "Taiwan", "sea": "Pacific"},
        km="km",
        rows={
            "reservoir": ("Taiwan Reservoirs", "Storage levels and water alert map", "Major reservoirs, storage", "Last 30 days"),
            "power": ("Taiwan Power", "Demand, operating reserve and power sources", "Current demand", "Today"),
            "births": ("Taiwan Births & Deaths", "By county and over time", "Births", "Last 24 months"),
            "flights": ("Taiwan Flights", "Routes, airlines and load factors", "Load factor, international and Mainland China", "This year"),
            "travel": ("Taiwan Tourism", "Visitors, trips abroad and airports", "Visitor arrivals", "Since 2010"),
        },
        fmt_power=lambda v: f"{v / 100:,.1f}<small>GW</small>", fmt_people=lambda n: f"{n:,}",
        fmt_wan=lambda n: f"{n / 1e6:,.2f}<small> million</small>", unit_pt=" pts",
        lights=dict(green="Green", yellow="Yellow", orange="Orange"), reserve="Operating reserve",
        vs_ly="vs. a year ago", vs_lm="vs. last month", vs_ly_m="vs. same month last year", vs_py="vs. previous year",
        when_dt=lambda t: f"{t:%b} {t.day}, {t:%H:%M}", when_m=lambda m: f"{calendar.month_name[int(m[5:])]} {m[:4]}", when_y=lambda y: f"{y}",
        src_t="Sources", src="Open data from the Water Resources Agency, Taiwan Power Company, Ministry of the Interior, Civil Aeronautics Administration and Tourism Administration.",
        about_t="About", about="Taiwan government open data, compiled, with the date of every figure shown.", about_link="About",
        ng_t="Independent site", ng="An independent site, not affiliated with any government agency.", contact="Email us: contact@taiwandata.info"),
    "ja": dict(
        title="Taiwan Data 台湾データ：データで見る台湾、ダム・電力・人口・航空便の最新統計",
        desc="台湾の最新の公式統計：主要ダムの貯水率、現在の電力使用量、毎月の出生数、航空便の搭乗率、訪台客数。",
        eyebrow="TAIWAN DATA", h1="データで見る台湾", lead="台湾のダム、電力、人口、航空便、旅客の最新の公式統計。",
        updated="データ更新", meta_src="出典：台湾政府オープンデータ", meta_freq="毎時自動更新", ctx="地図", tbl="台湾のデータ",
        f_loc=("位置", "東アジア・西太平洋"), f_tz=("標準時", "UTC+8"), f_pop="人口", f_div=("行政区画", "22県市"),
        pop_fmt=lambda p: f"{p / 1e4:,.1f}<small> 万人</small>", pop_when=lambda m: f"{m[:4]}年{int(m[5:])}月末・内政部戸政司",
        pop_chg=lambda c: f"1年前より{abs(c) / 1e4:.1f}万人{'減少' if c < 0 else '増加'}",
        map_label="東アジアにおける台湾の位置", inset="台湾本島",
        names={"156": "中国", "392": "日本", "410": "韓国", "608": "フィリピン", "158": "台湾", "sea": "太平洋"},
        km="km",
        rows={
            "reservoir": ("台湾のダム貯水率", "貯水率と水情信号マップ", "主要ダムの貯水率", "直近30日"),
            "power": ("台湾の電力", "電力需要・予備率・電源構成", "現在の電力需要", "今日"),
            "births": ("台湾の出生と死亡", "県市別の比較と長期推移", "出生数", "直近24か月"),
            "flights": ("台湾の航空便", "路線・航空会社・搭乗率", "国際線・中国大陸線の搭乗率", "今年の各月"),
            "travel": ("台湾の旅客数", "訪台客・出国者・空港", "訪台客数", "2010年以降"),
        },
        fmt_power=lambda v: f"{v:,.0f}<small>万kW</small>", fmt_people=lambda n: f"{n:,}<small>人</small>",
        fmt_wan=lambda n: f"{n / 1e4:,.0f}<small>万人</small>", unit_pt="ポイント",
        lights=dict(green="緑", yellow="黄", orange="橙"), reserve="予備率",
        vs_ly="前年同期比", vs_lm="前月比", vs_ly_m="前年同月比", vs_py="前年比",
        when_dt=lambda t: f"{t.month}/{t.day} {t:%H:%M}", when_m=lambda m: f"{m[:4]}年{int(m[5:])}月", when_y=lambda y: f"{y}年",
        src_t="出典", src="経済部水利署、台湾電力公司、内政部戸政司、交通部民用航空局、交通部観光署のオープンデータ。",
        about_t="このサイトについて", about="台湾政府のオープンデータを整理し、すべての数字にデータの時点を記載しています。", about_link="このサイトについて",
        ng_t="非政府サイト", ng="個人が運営するサイトで、政府機関とは関係ありません。", contact="お問い合わせ：contact@taiwandata.info"),
    "ko": dict(
        title="Taiwan Data 대만 데이터: 데이터로 보는 대만, 저수지·전력·인구·항공편 최신 통계",
        desc="대만의 최신 공식 통계: 주요 저수지 저수율, 현재 전력 수요, 월별 출생아 수, 항공편 탑승률, 대만 방문객 수.",
        eyebrow="TAIWAN DATA", h1="데이터로 보는 대만", lead="대만 저수지, 전력, 인구, 항공편, 여객의 최신 공식 통계.",
        updated="데이터 업데이트", meta_src="출처: 대만 정부 공공데이터", meta_freq="매시간 자동 업데이트", ctx="지도", tbl="대만 데이터",
        f_loc=("위치", "동아시아·서태평양"), f_tz=("시간대", "UTC+8"), f_pop="인구", f_div=("행정구역", "22개 현·시"),
        pop_fmt=lambda p: f"{p / 1e4:,.1f}<small>만 명</small>", pop_when=lambda m: f"{m[:4]}년 {int(m[5:])}월 말·내정부 호정사",
        pop_chg=lambda c: f"1년 전보다 {abs(c) / 1e4:.1f}만 명 {'감소' if c < 0 else '증가'}",
        map_label="동아시아 속 대만의 위치", inset="대만 본섬",
        names={"156": "중국", "392": "일본", "410": "한국", "608": "필리핀", "158": "대만", "sea": "태평양"},
        km="km",
        rows={
            "reservoir": ("대만 저수지 저수율", "저수율과 물 수급 신호 지도", "주요 저수지 저수율", "최근 30일"),
            "power": ("대만 전력", "전력 수요, 운영예비율, 발전원", "현재 전력 수요", "오늘"),
            "births": ("대만 출생·사망", "현·시별 비교와 연도별 추이", "출생아 수", "최근 24개월"),
            "flights": ("대만 항공편", "노선, 항공사, 탑승률", "국제선·중국 본토 노선 탑승률", "올해 월별"),
            "travel": ("대만 여객 수", "대만 방문객, 출국자, 공항", "대만 방문객", "2010년부터"),
        },
        fmt_power=lambda v: f"{v:,.0f}<small>만 kW</small>", fmt_people=lambda n: f"{n:,}<small>명</small>",
        fmt_wan=lambda n: f"{n / 1e4:,.0f}<small>만 명</small>", unit_pt="%p",
        lights=dict(green="초록", yellow="노랑", orange="주황"), reserve="운영예비율",
        vs_ly="전년 동기 대비", vs_lm="전월 대비", vs_ly_m="전년 동월 대비", vs_py="전년 대비",
        when_dt=lambda t: f"{t.month}/{t.day} {t:%H:%M}", when_m=lambda m: f"{m[:4]}년 {int(m[5:])}월", when_y=lambda y: f"{y}년",
        src_t="출처", src="경제부 수리서, 대만전력공사, 내정부 호정사, 교통부 민용항공국, 교통부 관광서의 공공데이터.",
        about_t="사이트 소개", about="대만 정부 공공데이터를 정리하고, 모든 수치에 기준 시점을 표시합니다.", about_link="사이트 소개",
        ng_t="비정부 사이트", ng="개인이 운영하는 사이트로, 정부 기관과 관련이 없습니다.", contact="문의: contact@taiwandata.info"),
}

ICONS = {  # Material Icons（Apache 2.0）
    "reservoir": "M12 2c-5.33 4.55-8 8.48-8 11.8 0 4.98 3.8 8.2 8 8.2s8-3.22 8-8.2C20 10.48 17.33 6.55 12 2z",
    "power": "M11 21h-1l1-7H7.5c-.58 0-.57-.32-.38-.66.19-.34.05-.08.07-.12C8.48 10.94 10.42 7.54 13 3h1l-1 7h3.5c.49 0 .56.33.47.51l-.07.15C12.96 17.55 11 21 11 21z",
    "births": ("M16 11c1.66 0 2.99-1.34 2.99-3S17.66 5 16 5c-1.66 0-3 1.34-3 3s1.34 3 3 3zm-8 0c1.66 0 2.99-1.34 2.99-3S9.66 5 8 5C6.34 5 5 6.34 5 8s1.34 3 3 3zm0 2c-2.33 0-7 1.17-7 3.5V19h14v-2.5c0-2.33-4.67-3.5-7-3.5zm8 0c-.29 0-.62.02-.97.05 1.16.84 1.97 1.97 1.97 3.45V19h6v-2.5c0-2.33-4.67-3.5-7-3.5z"),
    "flights": "M21 16v-2l-8-5V3.5c0-.83-.67-1.5-1.5-1.5S10 2.67 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5l8 2.5z",
    "travel": "M20 7h-4V5c0-1.1-.9-2-2-2h-4c-1.1 0-2 .9-2 2v2H4c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V9c0-1.1-.9-2-2-2zm-6 0h-4V5h4v2z",
}
URL = {"reservoir": "reservoir/", "power": "power/", "births": "births/", "flights": "flights/", "travel": "tourism/"}


def line_chart(vals, w=140, h=44):
    """連續資料（近 30 天、今天）：細線＋極淡底色，最後一點加圓點。"""
    if len(vals) < 2:
        return ""
    lo, hi = min(vals), max(vals)
    span = (hi - lo) or 1
    pts = [(3 + i * (w - 9) / (len(vals) - 1), 5 + (h - 12) * (1 - (v - lo) / span)) for i, v in enumerate(vals)]
    d = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    x, y = pts[-1]
    return (f'<svg class="chart" viewBox="0 0 {w} {h}" preserveAspectRatio="none" aria-hidden="true"><path class="base" d="M0 {h - .5}H{w}"/>'
            f'<polygon class="area" points="3,{h - 1} {d} {x:.1f},{h - 1}"/><polyline class="ln" points="{d}"/>'
            f'<path class="pt" d="M{x:.1f} {y:.1f}h0"/></svg>')


def bar_chart(vals, w=140, h=44):
    """每月、每年的資料：細長條，最新一根用主色。"""
    if not vals:
        return ""
    hi = max(vals) or 1
    n = len(vals)
    gap = 2 if n > 16 else 3
    bw = (w - gap * (n - 1)) / n
    out = []
    for i, v in enumerate(vals):
        bh = max(1.5, (h - 4) * v / hi)
        out.append(f'<rect class="{"last" if i == n - 1 else "b"}" x="{i * (bw + gap):.1f}" y="{h - bh:.1f}" width="{bw:.1f}" height="{bh:.1f}" rx="1"/>')
    return f'<svg class="chart" viewBox="0 0 {w} {h}" preserveAspectRatio="none" aria-hidden="true">{"".join(out)}</svg>'


def region_map(t):
    """東亞地圖，填滿地圖卡片：卡片多高多寬都不留白。

    地圖畫得比看得到的範圍大（北緯 58 度到南緯 12 度），寬度跟卡片一樣，畫面中心固定在北緯 24 度；
    卡片比較高就多看到一點南北，比較矮就少一點。地名、比例尺、台灣本島放大圖用一般文字疊在上面，
    字的大小固定，不會跟著地圖縮放變得太小或太大。
    """
    import math
    w = worldmap.world()
    W0, E0, N0, S0 = 104, 144, 58, -12
    x0, y0 = worldmap.xy(N0, W0)
    x1, y1 = worldmap.xy(S0, E0)
    vw, vh = x1 - x0, y1 - y0
    keep = {"156", "392", "410", "408", "608", "704", "418", "116", "764", "104", "496", "360", "458", "096", "626",
            "344", "446", "643", "036", "598", "585"}
    land = "".join(f'<path class="c" d="{w["countries"][k]}"/>' for k in sorted(keep) if k in w["countries"])
    grat = []
    for lon in (110, 120, 130, 140):
        x, _ = worldmap.xy(0, lon)
        grat.append(f'<path class="g" d="M{x} {y0}V{y1}"/>')
    for lat in range(-10, 60, 10):
        _, y = worldmap.xy(lat, 0)
        grat.append(f'<path class="g" d="M{x0} {y}H{x1}"/>')
    n = t["names"]

    def at(lat, lon):
        x, y = worldmap.xy(lat, lon)
        return f"left:{(x - x0) / vw * 100:.2f}%;top:{(y - y0) / vh * 100:.2f}%"

    # 地名放在卡片最矮時（高是寬的 0.7 倍，看得到北緯約 11～37 度）也看得到的位置
    labels = (f'<span class="ml" style="{at(31, 111)}">{e(n["156"])}</span>'
              f'<span class="ml" style="{at(33.2, 135.2)}">{e(n["392"])}</span>'
              f'<span class="ml" style="{at(17.0, 121.2)}">{e(n["608"])}</span>'
              f'<span class="ml sea" style="{at(27.5, 131)}">{e(n["sea"])}</span>'
              f'<span class="ml tw" style="{at(25.0, 122.2)}">{e(n["158"])}</span>')
    _, yc = worldmap.xy(24, 0)
    m = json.loads((ROOT / "reservoir/taiwan-map.json").read_text(encoding="utf-8"))
    inset = (f'<div class="inset"><svg viewBox="0 0 {m["width"]} {m["height"]}" aria-hidden="true">'
             + "".join(f'<path d="{d}"/>' for d in m["counties"].values())
             + f'</svg><span>{e(t["inset"])}</span></div>')
    per_km = w["k"] * w["s"] / (111.32 * math.cos(math.radians(23.5)))
    scale = (f'<div class="scl" style="width:{1000 * per_km / vw * 100:.2f}%"><b></b>'
             f'<span style="left:0">0</span><span style="left:100%">1,000 {e(t["km"])}</span></div>')
    return (f'<div class="mapart" style="aspect-ratio:{vw:.1f}/{vh:.1f};transform:translateY(-{(yc - y0) / vh * 100:.2f}%)">'
            f'<svg viewBox="{x0} {y0} {vw:.1f} {vh:.1f}" role="img" aria-label="{e(t["map_label"])}">'
            f'<rect class="sea" x="{x0}" y="{y0}" width="{vw:.1f}" height="{vh:.1f}"/>'
            + "".join(grat) + f'<g>{land}</g><path class="tw" d="{w["countries"]["158"]}"/></svg>{labels}</div>'
            + inset + scale)


def page(lang="zh"):
    t = T[lang]
    d = data()
    r, p, b, f, v = d["reservoir"], d["power"], d["births"], d["flights"], d["travel"]
    dt = lambda iso: t["when_dt"](datetime.fromisoformat(iso))

    def chip(val, label, unit="%", digits=1):
        if val is None:
            return ""
        cls, arrow = ("up", "▲") if val > 0.05 else ("down", "▼") if val < -0.05 else ("flat", "▶")
        return f'<span class="chg"><b class="chip {cls}">{arrow} {abs(val):.{digits}f}{unit}</b>{e(label)}</span>'
    pt = t["unit_pt"]
    lights = t["lights"]
    items = [
        ("reservoir", f"{r['pct']:.1f}<small>%</small>",
         chip(r["pct"] - r["last_year"] if r["last_year"] is not None else None, t["vs_ly"], pt), line_chart(r["spark"]), dt(r["when"])),
        ("power", t["fmt_power"](p["now"]),
         f'<span class="chg"><b class="chip ok"><i class="lamp {p["light"]}"></i>{lights[p["light"]]}</b>{e(t["reserve"])} {p["rate"]:.1f}%</span>',
         line_chart(p["spark"]), dt(p["when"])),
        ("births", t["fmt_people"](b["births"]), chip(b["yoy"], t["vs_ly_m"]), bar_chart(b["spark"]), t["when_m"](b["month"])),
        ("flights", f"{f['lf']:.1f}<small>%</small>", chip(f["lf"] - f["prev"] if f["prev"] is not None else None, t["vs_lm"], pt),
         bar_chart(f["spark"]), t["when_m"](f["month"])),
        ("travel", t["fmt_wan"](v["inbound"]), chip(v["yoy"], t["vs_py"]), bar_chart(v["spark"]), t["when_y"](v["year"])),
    ]
    trs = []

    def row_colors(k):  # 每一列的主題色（scripts/theme.py，第 16 組「大地」）
        c = theme.SECTION["tourism" if k == "travel" else k]
        return f"--c:{c};--ig:{theme.on(c)};--cb:{theme.bar_tint(c)}"
    for k, num, change, chart, when in items:
        name, sub, label, cap = t["rows"][k]
        trs.append(
            f'<a class="row card" href="{URL[k]}" style="{row_colors(k)}"><span class="ic"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="{ICONS[k]}"/></svg></span>'
            f'<span class="nm"><b>{e(name)}</b><span>{e(sub)}</span></span>'
            f'<span class="fig"><span class="num">{num}</span><span class="lbl">{e(label)}</span>{change}</span>'
            f'<span class="viz">{chart}<span class="cap">{e(cap)}</span></span>'
            f'<span class="when">{e(when)}</span><span class="go" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M5 12h13M13 6l6 6-6 6"/></svg></span></a>')
    pop = d["population"]
    facts = (
        f'<dl class="facts"><div class="pop"><dt>{e(t["f_pop"])}</dt><dd><span class="big">{t["pop_fmt"](pop["pop"])}</span>'
        f'<span class="note">{e(t["pop_when"](pop["month"]))}</span>'
        + (f'<span class="note">{e(t["pop_chg"](pop["year_change"]))}</span>' if pop["year_change"] is not None else "")
        + f'</dd></div><div class="kv"><dt>{e(t["f_loc"][0])}</dt><dd>{e(t["f_loc"][1])}</dd>'
        f'<dt>{e(t["f_tz"][0])}</dt><dd>{e(t["f_tz"][1])}</dd>'
        f'<dt>{e(t["f_div"][0])}</dt><dd>{e(t["f_div"][1])}</dd></div></dl>')
    upd = dt(d["generated_at"]) if d.get("generated_at") else ""
    tw = json.loads((ROOT / "reservoir/taiwan-map.json").read_text(encoding="utf-8"))
    isle = (f'<svg class="isle" viewBox="0 0 {tw["width"]} {tw["height"]}" aria-hidden="true">'
            + "".join(f'<path d="{p}"/>' for p in tw["counties"].values()) + "</svg>")  # 手機才顯示
    return f"""<body>
<!--SITE_NAV-->
<main class="w home">
  <div class="side">
    <header class="hero">
      {isle}
      <p class="eyebrow">{e(t["eyebrow"])}</p>
      <h1>{e(t["h1"])}</h1>
      <p class="lead">{e(t["lead"])}</p>
      <p class="meta"><span><i class="dot"></i>{e(t["meta_freq"])}</span><span>{e(t["updated"])} {e(upd)}</span><span>{e(t["meta_src"])}</span></p>
      {facts}
    </header>
    <section class="ctx">
      <h2 class="sh"><button type="button" aria-expanded="true" aria-controls="ctx-in">{e(t["ctx"])}<span class="plus" aria-hidden="true"></span></button></h2>
      <div class="ctx-in" id="ctx-in"><div class="mapbox">{region_map(t)}</div></div>
    </section>
  </div>
  <section class="topics">
    <h2 class="sh">{e(t["tbl"])}</h2>
    <div class="rows">{"".join(trs)}</div>
  </section>
</main>
<footer class="foot"><div class="w cols">
  <div><b>{e(t["src_t"])}</b><p>{e(t["src"])}</p></div>
  <div><b>{e(t["about_t"])}</b><p>{e(t["about"])} <a href="about/">{e(t["about_link"])} →</a></p></div>
  <div><b>{e(t["ng_t"])}</b><p>{e(t["ng"])}<br>{e(t["contact"])}</p></div>
</div></footer>
<script>(function(){{var c=document.querySelector(".ctx"),b=c&&c.querySelector("button");if(!b)return;
function set(o){{c.classList.toggle("shut",!o);b.setAttribute("aria-expanded",o?"true":"false");}}
if(window.matchMedia("(max-width: 760px)").matches)set(false);b.addEventListener("click",function(){{set(c.classList.contains("shut"));}});}})();</script>
</body>"""


CSS = """
:root { --f-body:"Noto Sans TC","PingFang TC","Microsoft JhengHei",system-ui,sans-serif; --f-head:"LXGW WenKai TC",var(--f-body); --f-num:"DM Sans",var(--f-body);
  --ink:#111111; --text:#333333; --muted:#6b6b6b; --line:#e3e3e3; --line-strong:#c8c8c8; --fill:#f2f2f2;
  --surface:#ffffff; --fg:#111111; --chip:#f2f2f2; /* 頂端列（site_nav）用這三個 */
  --icon:#2b6a66; --up:#1e7a45; --down:#c0392b;
  --sea:#e9f0f5; --land:#ffffff; --land-line:#c5cfd7; --grat:#d3dde5; --maplab:#5f6b73; --tw:#4e79a7; /* 台灣 = 水庫那一列的藍（theme.SECTION） */
  --gap:16px; --side:clamp(360px, 23vw, 440px); --map-w:38%; }
/* 黑白灰：底全白、字黑灰。只有地圖、台灣小圖、主題圖示、增減百分比（和官方燈號）有顏色 */
* { box-sizing:border-box; }
.hero h1, h2, .nm b, .foot b { font-family:var(--f-head); }
.num, .facts .big { font-family:var(--f-num); }
body { margin:0; background:#ffffff; color:var(--text); font-family:var(--f-body);
  font-size:15px; line-height:1.6; font-variant-numeric:tabular-nums; -webkit-font-smoothing:antialiased; }
a { color:inherit; }
/* 寬度和左右邊界跟頂端列、其他頁面一樣：最寬 1840px，左右各 16px */
.w { max-width:1840px; margin:0 auto; padding-inline:max(16px, env(safe-area-inset-left)) max(16px, env(safe-area-inset-right)); }
.card { background:#ffffff; border:1px solid var(--line); border-radius:16px; }

/* 版面。手機：一欄。平板（761～1279）：上面標題卡＋地圖並排，下面五張卡片。
   桌機（1280 以上）：左欄標題卡＋地圖，右欄五張卡片；左右兩欄上緣切齊、下緣切齊（地圖填滿剩下的高度） */
.home { display:grid; gap:28px; padding-top:20px; padding-bottom:48px; }
.side { display:flex; flex-direction:column; gap:var(--gap); min-width:0; }
.topics { min-width:0; }
.sh { margin:0 0 12px; font-size:18px; line-height:26px; color:var(--ink); font-weight:700; letter-spacing:.04em; }
@media (min-width:761px) {
  .home { gap:var(--gap); padding-top:24px; }
  .side { flex-direction:row; align-items:stretch; }
  .hero { flex:1 1 0; min-width:0; }
  .ctx { flex:0 0 var(--map-w); min-height:300px; }
  .sh { position:absolute; width:1px; height:1px; margin:0; overflow:hidden; clip:rect(0 0 0 0); white-space:nowrap; } }
@media (min-width:1024px) { .rows { column-gap:24px; } }
@media (min-width:1280px) {
  .home { grid-template-columns:var(--side) minmax(0, 1fr); align-items:stretch; }
  .side { flex-direction:column; }
  .hero { flex:none; }
  .ctx { flex:1 1 auto; min-height:calc(var(--side) * .7); }
  .topics { display:flex; flex-direction:column; }
  .rows { flex:1; } }

/* 標題卡 */
.eyebrow { margin:0 0 8px; font-size:12px; line-height:20px; font-weight:700; letter-spacing:.22em; color:var(--muted); }
.hero h1 { margin:0; font-size:min(34px, calc((100vw - 32px) / 10)); line-height:1.2; font-weight:700; letter-spacing:.06em; color:var(--ink); }
.hero .lead { margin:10px 0 0; font-size:15px; line-height:1.7; color:var(--muted); text-wrap:balance; word-break:keep-all; }
.meta { display:flex; flex-wrap:wrap; gap:2px 18px; margin:10px 0 0; font-size:13px; line-height:20px; color:var(--muted); }
.meta .dot { display:inline-block; width:7px; height:7px; border-radius:50%; background:var(--ink); margin-right:7px; vertical-align:1px; }
.facts { margin:18px 0 0; padding-top:14px; border-top:1px solid var(--line); }
.facts .pop { padding-bottom:12px; border-bottom:1px solid var(--line); }
.facts dt { font-size:13px; line-height:20px; color:var(--muted); }
.facts dd { margin:2px 0 0; font-size:15px; line-height:22px; color:var(--ink); }
.facts .kv { display:grid; grid-template-columns:max-content minmax(0, 1fr); gap:6px 20px; align-items:baseline; padding-top:12px; }
.facts .kv dd { margin:0; }
.facts .big { display:block; font-size:28px; line-height:34px; font-weight:700; color:var(--ink); }
.facts .big small { font-size:14px; font-weight:500; color:var(--muted); margin-left:3px; }
.facts .note { display:block; font-size:12.5px; line-height:20px; color:var(--muted); }
.isle { display:none; }
/* 手機：標題右邊放台灣本島，不留一大片空白；人口和位置、時區、行政區左右兩欄 */
@media (max-width:760px) {
  .hero { display:grid; grid-template-columns:minmax(0, 1fr) auto; grid-template-rows:auto auto auto 1fr auto; column-gap:12px; }
  .hero > :not(.isle) { grid-column:1; }
  .hero h1 { font-size:min(34px, calc((100vw - 44px - var(--isle-w)) / var(--h1-n))); text-wrap:balance; }
  .isle { display:block; grid-column:2; grid-row:1 / span 4; align-self:center; width:var(--isle-w); height:auto; }
  .isle path { fill:var(--tw); stroke:#ffffff; stroke-width:.8; vector-effect:non-scaling-stroke; }
  .hero .meta { align-self:start; }
  .hero .facts { grid-column:1 / -1; } }
/* 兩欄要排得下才用：中文、韓文都可以；日文 360 以上、英文 440 以上（字比較長） */
@media (max-width:760px) { html[lang^="zh"] .hero .facts { display:grid; grid-template-columns:minmax(0, 1fr) minmax(0, 1fr); column-gap:16px; } html[lang^="zh"] .facts .pop { padding-bottom:0; border-bottom:0; } html[lang^="zh"] .facts .big { font-size:clamp(22px, 7vw, 28px); } html[lang^="zh"] .facts .kv { display:block; padding:0 0 0 16px; border-left:1px solid var(--line); } html[lang^="zh"] .facts .kv dd { margin:0 0 6px; } html[lang^="zh"] .facts .kv dd:last-child { margin-bottom:0; } html[lang="ko"] .hero .facts { display:grid; grid-template-columns:minmax(0, 1fr) minmax(0, 1fr); column-gap:16px; } html[lang="ko"] .facts .pop { padding-bottom:0; border-bottom:0; } html[lang="ko"] .facts .big { font-size:clamp(22px, 7vw, 28px); } html[lang="ko"] .facts .kv { display:block; padding:0 0 0 16px; border-left:1px solid var(--line); } html[lang="ko"] .facts .kv dd { margin:0 0 6px; } html[lang="ko"] .facts .kv dd:last-child { margin-bottom:0; } }
@media (min-width:360px) and (max-width:760px) { html[lang="ja"] .hero .facts { display:grid; grid-template-columns:minmax(0, 1fr) minmax(0, 1fr); column-gap:16px; } html[lang="ja"] .facts .pop { padding-bottom:0; border-bottom:0; } html[lang="ja"] .facts .big { font-size:clamp(22px, 7vw, 28px); } html[lang="ja"] .facts .kv { display:block; padding:0 0 0 16px; border-left:1px solid var(--line); } html[lang="ja"] .facts .kv dd { margin:0 0 6px; } html[lang="ja"] .facts .kv dd:last-child { margin-bottom:0; } }
@media (min-width:440px) and (max-width:760px) { html[lang="en"] .hero .facts { display:grid; grid-template-columns:minmax(0, 1fr) minmax(0, 1fr); column-gap:16px; } html[lang="en"] .facts .pop { padding-bottom:0; border-bottom:0; } html[lang="en"] .facts .big { font-size:clamp(22px, 7vw, 28px); } html[lang="en"] .facts .kv { display:block; padding:0 0 0 16px; border-left:1px solid var(--line); } html[lang="en"] .facts .kv dd { margin:0 0 6px; } html[lang="en"] .facts .kv dd:last-child { margin-bottom:0; } }
:root { --isle-w:clamp(64px, 24vw, 110px); --h1-n:6.5; }  /* --h1-n：標題有幾個字寬（量過），手機上標題縮到一行排得下 */
html[lang="en"] { --h1-n:9.2; } html[lang="ja"] { --h1-n:8.4; } html[lang="ko"] { --h1-n:8.8; }
@media (min-width:761px) {
  .hero { background:#ffffff; border:1px solid var(--line); border-radius:16px; padding:24px; display:flex; flex-direction:column; }
  .hero h1 { font-size:clamp(32px, 2.3vw, 42px); }
  .hero .lead { font-size:16px; }
  .facts { margin-top:auto; }
  .meta + .facts { margin-top:20px; } }
@media (min-width:1280px) { .hero h1 { font-size:min(42px, calc((var(--side) - 48px) / 10)); } } /* 日文、英文標題也排得下一行 */

/* 地圖卡片：手機收合；平板、桌機填滿卡片 */
.ctx { border:1px solid var(--line); border-radius:16px; padding:0 16px; background:#ffffff; }
.ctx .sh { margin:0; font-size:16px; line-height:24px; }
.sh button { all:unset; display:flex; align-items:center; justify-content:space-between; gap:12px; width:100%; font:inherit; color:inherit; letter-spacing:inherit; padding:14px 0; cursor:pointer; }
.plus { width:20px; height:20px; position:relative; flex:none; color:var(--muted); }
.plus::before, .plus::after { content:""; position:absolute; left:3px; right:3px; top:9px; height:1.5px; background:currentColor; }
.plus::after { transform:rotate(0); transition:transform .2s; }
.ctx.shut .plus::after { transform:rotate(90deg); }
.ctx.shut .ctx-in { display:none; }
.ctx-in { padding:0 0 16px; }
.mapbox { position:relative; overflow:hidden; background:var(--sea); border-radius:10px; aspect-ratio:10 / 9; container-type:size; }
@media (min-width:761px) {
  .ctx { padding:0; display:flex; flex-direction:column; overflow:hidden; }
  .ctx-in { flex:1; display:flex; padding:0; }
  .ctx.shut .ctx-in { display:flex; }
  .mapbox { flex:1; aspect-ratio:auto; border-radius:0; } }
.mapart { position:absolute; left:0; top:50%; width:100%; }
.mapart svg { position:absolute; inset:0; width:100%; height:100%; display:block; }
.mapart .sea { fill:var(--sea); }
.mapart .g { stroke:var(--grat); stroke-width:.25; stroke-dasharray:.8 .8; }
.mapart .c { fill:var(--land); stroke:var(--land-line); stroke-width:.3; stroke-linejoin:round; }
.mapart .tw { fill:var(--tw); }
.ml { position:absolute; transform:translate(-50%, -50%); font-size:12px; line-height:16px; color:var(--maplab); letter-spacing:.12em; white-space:nowrap; pointer-events:none; }
.ml.sea { font-style:italic; letter-spacing:.3em; }
.ml.tw { transform:translate(0, -50%); font-size:13px; font-weight:700; color:var(--tw); }
.inset { position:absolute; right:12px; bottom:12px; display:flex; flex-direction:column; align-items:center; gap:2px; padding:8px 10px 6px; background:#ffffff; border:1px solid var(--line-strong); border-radius:6px; }
.inset svg { display:block; height:min(28cqh, 150px); aspect-ratio:720 / 1342; }
@media (min-width:761px) { .inset svg { height:min(32cqh, 150px); } }
.inset path { fill:var(--tw); stroke:#ffffff; stroke-width:.8; vector-effect:non-scaling-stroke; }
.inset span { font-size:11px; line-height:16px; color:var(--maplab); white-space:nowrap; }
.scl { position:absolute; left:14px; bottom:16px; height:20px; }
.scl b { position:absolute; left:0; right:0; bottom:0; height:5px; border:1px solid var(--maplab); border-top:0; }
.scl b::after { content:""; position:absolute; left:50%; bottom:0; height:5px; border-left:1px solid var(--maplab); }
.scl span { position:absolute; top:0; transform:translateX(-50%); font-size:11px; line-height:12px; color:var(--maplab); white-space:nowrap; }
.scl span:first-of-type { transform:none; }

/* 主題卡片。手機：圖示＋名稱在上，數字在左、趨勢圖在右，資料時間在最下面 */
.rows { display:grid; gap:12px; }
.row { display:grid; text-decoration:none; padding:18px 16px; column-gap:12px; align-items:start;
  grid-template-columns:40px minmax(0, 1fr) 70px 30px; grid-template-rows:auto auto auto auto auto auto;
  grid-template-areas:"ic t t go" "ic s s s" "n n viz viz" "l l viz viz" "c c viz viz" "w w w w"; transition:border-color .15s; }
.row:hover { border-color:var(--ink); }
.row.card:hover { border-left-color:var(--c, var(--ink)); }
.row:focus-visible { outline:2px solid var(--ink); outline-offset:2px; }
.nm, .fig { display:contents; }
.ic { grid-area:ic; align-self:center; width:40px; height:40px; border-radius:50%; display:grid; place-items:center; background:var(--c, var(--fill)); }
.ic svg { width:20px; height:20px; fill:var(--ig, var(--icon)); }
.row.card { border-left:8px solid var(--c, var(--line)); } /* 每列左邊一條主題色 */
.nm b { grid-area:t; align-self:end; font-size:17px; font-weight:700; line-height:1.35; color:var(--ink); letter-spacing:.04em; white-space:nowrap; }
.nm span { grid-area:s; font-size:13px; color:var(--muted); line-height:1.5; }
.num { grid-area:n; margin-top:16px; font-size:32px; font-weight:700; line-height:1.05; color:var(--ink); white-space:nowrap; letter-spacing:-.01em; }
.num small { font-size:14px; font-weight:500; margin-left:4px; color:var(--muted); letter-spacing:0; }
.lbl { grid-area:l; margin-top:6px; font-size:13.5px; color:var(--text); line-height:1.5; text-wrap:balance; }
.chg { grid-area:c; margin-top:4px; display:flex; flex-wrap:wrap; align-items:baseline; gap:2px 8px; font-size:12.5px; line-height:1.6; color:var(--muted); }
.chip { font-size:12.5px; font-weight:700; white-space:nowrap; color:var(--ink); }
.chip.up { color:var(--up); } .chip.down { color:var(--down); }
.lamp { display:inline-block; width:7px; height:7px; border-radius:50%; margin-right:6px; vertical-align:1px; }
.lamp.green { background:#2f8a4f; } .lamp.yellow { background:#d9a300; } .lamp.orange { background:#e07b1f; }
.viz { grid-area:viz; margin-top:16px; align-self:stretch; display:flex; flex-direction:column; min-width:0; }
.viz .chart { display:block; width:100%; height:0; flex:1 1 auto; min-height:44px; overflow:visible; } /* 高度由卡片的文字決定，圖只填滿 */
.viz .cap { display:block; font-size:11.5px; line-height:16px; color:var(--muted); margin-top:6px; letter-spacing:.04em; white-space:nowrap; text-align:right; }
.chart .base { stroke:var(--line-strong); stroke-width:1; vector-effect:non-scaling-stroke; }
.chart .area { fill:none; }
.chart .ln { fill:none; stroke:var(--c, var(--ink)); stroke-width:3; stroke-linejoin:round; stroke-linecap:round; vector-effect:non-scaling-stroke; }
.chart .pt { fill:none; stroke:var(--c, var(--ink)); stroke-width:9; stroke-linecap:round; vector-effect:non-scaling-stroke; }
.chart .b { fill:var(--cb, #d0d0d0); } .chart .last { fill:var(--c, var(--ink)); }
.when { grid-area:w; margin-top:10px; padding-top:10px; border-top:1px solid var(--line); font-size:12.5px; color:var(--muted); white-space:nowrap; }
.go { grid-area:go; align-self:center; justify-self:end; width:30px; height:30px; border-radius:50%; border:1px solid var(--line-strong); display:grid; place-items:center; transition:background .15s, border-color .15s; }
.go svg { width:16px; height:16px; fill:none; stroke:var(--ink); stroke-width:2; stroke-linecap:round; stroke-linejoin:round; }
.row:hover .go { background:var(--ink); border-color:var(--ink); }
.row:hover .go svg { stroke:#ffffff; }
/* 平板、桌機：五張卡片共用同一組欄寬（subgrid），名稱、數字、趨勢圖在每張卡片都同一條直線上。
   名稱和數字的欄寬照最長的那一張，剩下的寬度全給趨勢圖。資料時間放在說明下面，和增減同一行 */
@media (min-width:761px) {
  .rows { gap:var(--gap) 20px; grid-template-columns:max-content fit-content(320px) fit-content(260px) minmax(120px, 1fr) max-content; grid-auto-rows:1fr; }
  .row { grid-column:1 / -1; grid-template-columns:subgrid; padding:22px 24px; row-gap:6px; align-items:baseline;
    grid-template-rows:auto auto 1fr; grid-template-areas:"ic t n viz go" ". s l viz ." ". w c viz ."; }
  .ic { width:44px; height:44px; } .ic svg { width:22px; height:22px; }
  .nm b { font-size:19px; align-self:baseline; } .nm span { font-size:13.5px; }
  .num { margin-top:0; font-size:34px; } .lbl, .chg { margin-top:0; }
  .viz { margin-top:0; }
  .viz .cap { text-align:left; }
  .when { margin:0; padding:0; border:0; font-size:12.5px; }
  .go { width:32px; height:32px; } }
@supports not (grid-template-columns:subgrid) {
  @media (min-width:761px) { .row { grid-template-columns:44px minmax(0, 1.1fr) minmax(0, 1fr) minmax(150px, 1.4fr) 32px; column-gap:24px; } } }

/* 頁尾：欄線和上面的卡片對齊 */
.foot { background:#ffffff; border-top:1px solid var(--line); padding:30px 0 44px; }
.foot .cols { display:grid; gap:20px; }
@media (min-width:761px) { .foot .cols { grid-template-columns:minmax(0, 1fr) minmax(0, 1fr) var(--map-w); gap:24px var(--gap); } }
@media (min-width:1280px) { .foot .cols { grid-template-columns:var(--side) minmax(0, 1fr) minmax(0, 1fr); } }
.foot b { font-size:13px; color:var(--ink); letter-spacing:.04em; }
.foot p { margin:6px 0 0; font-size:13px; color:var(--muted); line-height:1.75; }
.foot a { color:var(--ink); text-decoration:none; font-weight:500; }
"""

# Shane 2026-11-01 選了「人文」（霞鶩文楷標題＋DM Sans 數字），配色只用黑白灰。
# 英文標題用 DM Sans（霞鶩文楷的英文字母是手寫體，不適合英文標題）。日文標題用 Klee One（霞鶩文楷就是從它改的，日文字形）；韓文沒有同風格的字，標題用內文字型。
# 內文的 Noto Sans TC，日韓文頁由 build_pages 的 use_ja_font／use_ko_font 換成 JP／KR。
FONTS = "LXGW+WenKai+TC:wght@400;700&family=DM+Sans:wght@400;500;700&family=Noto+Sans+TC:wght@400;500;700"
FONT_LINK = {
    "zh": FONTS, "en": "DM+Sans:wght@400;500;700&family=Noto+Sans+TC:wght@400;500;700",
    "ja": "Klee+One:wght@400;600&family=DM+Sans:wght@400;500;700&family=Noto+Sans+TC:wght@400;500;700",
    "ko": "DM+Sans:wght@400;500;700&family=Noto+Sans+TC:wght@400;500;700",
}
HEAD_FONT = {"en": ':root { --f-head:"DM Sans",var(--f-body); } .hero h1, .sh, .nm b, .foot b { letter-spacing:0; } .hero h1 { letter-spacing:-.01em; } .nm b { font-size:17px; }',
             "ja": ':root { --f-head:"Klee One",var(--f-body); } .hero h1, .sh, .nm b { font-weight:600; } .hero h1 { letter-spacing:.02em; }',
             "ko": ":root { --f-head:var(--f-body); }"}
SITE = "https://taiwandata.info"
HTML_LANG = {"zh": "zh-Hant-TW", "en": "en", "ja": "ja", "ko": "ko"}
SITE_NAME = {"zh": "Taiwan Data 台灣數據", "en": "Taiwan Data", "ja": "Taiwan Data 台湾データ", "ko": "Taiwan Data 대만 데이터"}
LOCALE = {"zh": "zh_TW", "en": "en_US", "ja": "ja_JP", "ko": "ko_KR"}
DIR = {"zh": "", "en": "en/", "ja": "jp/", "ko": "kr/"}


def html(lang):
    """整頁 HTML。<!--SITE_ICONS-->、<!--HREFLANG-->、<!--SITE_NAV--> 由 build_pages 換掉。"""
    t = T[lang]
    url = f"{SITE}/{DIR[lang]}"
    return f"""<!doctype html>
<html lang="{HTML_LANG[lang]}">
<head>
<meta charset="utf-8">
<!-- Google Analytics -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-0FDV48XD37"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag("js",new Date());gtag("config","G-0FDV48XD37");</script>
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{e(t["title"])}</title>
<meta name="description" content="{e(t["desc"])}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{SITE_NAME[lang]}">
<meta property="og:locale" content="{LOCALE[lang]}">
<meta property="og:title" content="{e(t["title"])}">
<meta property="og:description" content="{e(t["desc"])}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{SITE}/og.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<!--HREFLANG-->
<!--SITE_ICONS-->
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family={FONT_LINK[lang]}&display=swap">
<style>{CSS}{HEAD_FONT.get(lang, "")}</style>
</head>
{page(lang)}
</html>
"""


def build(out):
    """寫出四種語言的首頁：index.html、en/、jp/、kr/。"""
    out = Path(out)
    pages = {lang: html(lang) for lang in ("zh", "en", "ja", "ko")}  # 四種都做好才寫，避免只換掉一半
    for lang, text in pages.items():
        d = out / DIR[lang]
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(text, encoding="utf-8")
