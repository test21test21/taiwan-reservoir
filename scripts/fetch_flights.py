#!/usr/bin/env python3
"""抓交通部民用航空局「民航運輸統計」（每月），整理成 data/flights/ 的 CSV。

民航局在 data.gov.tw 登記的網址（www.caa.gov.tw/FileAtt.ashx?id=…）是一個小 CSV，裡面寫最新版本和真正檔案（ODS）的網址：
- 30683 表3  各機場營運量（架次、旅客、貨運；歷年＋最近 13 個月）
- 30682 表5  各機場營運量－按國際、兩岸、國內航線分
- 30678 表32 國際及兩岸定期航線載客率－按月別分（今年每月；全部＋各機場）
- 30680 表36／42 國際及兩岸定期航線載客率－按航點及航空公司分（當月／今年累計；全部＋各機場）
- 34966 表53 同上的年資料（去年全年）

輸出（data/flights/）：
- airports.csv     period,airport,flights,pax,cargo        period 是 2025（全年）或 2026-08（單月）
- segments.csv     period,flights,flights_intl,flights_cross,flights_dom,pax,pax_intl,pax_cross,pax_dom,pax_transit
- loadfactor.csv   month,scope,region,flights,seats,pax,lf,in_pax,in_seats,out_pax,out_seats  region：all、intl、cross
- routes/<期間>.csv scope,region,dest,airline,flights,seats,pax,in_pax,in_seats,out_pax,out_seats
                    期間：2026-08（單月）、2026-ytd（今年 1 月到最新月）、2025（全年）
- source.json      每個檔案抓到的版本（例如 115年8月），沒變就不重抓

    python3 scripts/fetch_flights.py
"""
import csv
import io
import json
import re
import ssl
import sys
import time
import urllib.request
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data/flights"
CAA = "https://www.caa.gov.tw/FileAtt.ashx?lang=1&id={}"
SOURCES = {"airports": 30683, "segments": 30682, "loadfactor": 30678, "routes": 30680, "routes_year": 34966}

# 表裡的機場名稱 → 代號（網址和英文版用）
AIRPORTS = {
    "臺灣桃園國際機場": "TPE", "高雄國際機場": "KHH", "臺北松山國際機場": "TSA", "臺中國際機場": "RMQ",
    "花蓮機場": "HUN", "臺東機場": "TTT", "澎湖機場": "MZG", "臺南機場": "TNN", "嘉義機場": "CYI",
    "七美機場": "CMJ", "望安機場": "WOT", "蘭嶼機場": "KYD", "綠島機場": "GNI", "金門機場": "KNH",
    "馬祖北竿機場": "MFK", "屏東機場": "PIF", "新竹機場": "HSZ", "馬祖南竿機場": "LZN", "恆春機場": "HCN",
}
# 載客率表的分頁 → 範圍（ALL＝全部機場）
LF_SHEETS = {"32": "ALL", "32-1": "TPE", "32-2": "KHH", "32-3": "TSA", "32-4": "RMQ", "32-5": "HUN", "32-6": "TNN"}
ROUTE_SCOPES = {"": "ALL", "-1": "TPE", "-2": "KHH", "-3": "TSA", "-4": "RMQ"}  # 花蓮、臺南只有零星包機，不收

O = "{urn:oasis:names:tc:opendocument:xmlns:office:1.0}"
T = "{urn:oasis:names:tc:opendocument:xmlns:table:1.0}"


def ssl_context():
    # 政府網站憑證鏈缺 Subject Key Identifier，Python 3.13 的嚴格模式會拒絕；仍照常驗證憑證。
    ctx = ssl.create_default_context()
    ctx.verify_flags &= ~getattr(ssl, "VERIFY_X509_STRICT", 0)
    return ctx


def get(url, tries=4):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "taiwandata.info"})
            with urllib.request.urlopen(req, timeout=120, context=ssl_context()) as r:
                return r.read()
        except Exception as ex:
            if i == tries - 1:
                raise
            print(f"  重試 {url}：{ex}", file=sys.stderr)
            time.sleep(3 * (i + 1))


def read_ods(data):
    """ODS 試算表 → {分頁名稱: [[儲存格文字…]…]}（只用標準函式庫）。"""
    root = ET.fromstring(zipfile.ZipFile(io.BytesIO(data)).read("content.xml"))
    out = {}
    for t in root.iter(T + "table"):
        rows = []
        for r in t.iter(T + "table-row"):
            row = []
            for c in r:
                if c.tag not in (T + "table-cell", T + "covered-table-cell"):
                    continue
                n = int(c.get(T + "number-columns-repeated", "1"))
                v = c.get(O + "value") or "".join(c.itertext())
                row += [v.strip()] * min(n, 80)
            while row and row[-1] == "":
                row.pop()
            rows.append(row)
        out[t.get(T + "name")] = rows
    return out


def num(x):
    try:
        return float(str(x).replace(",", "").strip())
    except ValueError:
        return None


def it(x):
    v = num(x)
    return int(round(v)) if v is not None else 0


def clean(s):
    return re.sub(r"[\s　]+", "", s or "")


def period_rows(rows):
    """表3、表5 的「年(月)別」欄：100年…114年 是全年，接著「8月 9月 … 115年 1月 …」是最近 13 個月。
    回傳 [(期間, 該列)]，期間是 2025 或 2026-08。"""
    out, year = [], None
    for r in rows:
        if not r or not r[0]:
            continue
        lab = clean(r[0])
        m = re.fullmatch(r"(\d{2,3})年", lab)
        if m:
            year = int(m.group(1)) + 1911
            if len(r) > 2 and num(r[1]) is not None:
                out.append((str(year), r))
            continue
        m = re.fullmatch(r"(\d{1,2})月", lab)
        if m and year:
            # 「114年」那列之後的 8～12 月是 114 年；「115年」之後的 1～8 月是 115 年
            out.append((f"{year}-{int(m.group(1)):02d}", r))
    # 今年那列（後面接著 1 月起的月份）只是今年累計，不是全年，不收
    partial = {p for i, (p, _) in enumerate(out) if len(p) == 4 and i + 1 < len(out) and out[i + 1][0] == f"{p}-01"}
    return [(p, r) for p, r in out if p not in partial]


def parse_airports(data):
    sheets = read_ods(data)
    rows = next(iter(sheets.values()))
    head = next(r for r in rows if r and any("臺灣桃園國際機場" in c for c in r))
    cols = []  # (機場代號, 起始欄)
    for i, c in enumerate(head):
        name = re.sub(r"^\d+\.", "", clean(c))
        if name == "總計":
            cols.append(("ALL", i))
        elif name in AIRPORTS:
            cols.append((AIRPORTS[name], i))
    sub = next(r for r in rows if r and "合計" in r)  # 旅客人數下面分「合計 過境 出入境」或只有合計
    out = []
    for period, r in period_rows(rows):
        for code, i in cols:
            # 每個機場的欄位：起降架次、旅客人數合計、（過境、出入境）、貨運噸數
            j = i
            flights = it(r[j]) if j < len(r) else 0
            pax = it(r[j + 1]) if j + 1 < len(r) else 0
            nxt = min([k for _, k in cols if k > i] + [len(head)])
            cargo = num(r[nxt - 1]) if nxt - 1 < len(r) else None
            out.append({"period": period, "airport": code, "flights": flights, "pax": pax,
                        "cargo": round(cargo or 0, 1)})
    return fix_years(out)


def fix_years(rows):
    """表上最近 13 個月的前幾個月（例如 8～12 月）寫在「114年」全年那列下面，期間已經是對的；
    這裡只把重複的期間去掉（同一期間留最後一筆）。"""
    seen = {}
    for r in rows:
        seen[(r["period"], r.get("airport", ""))] = r
    return list(seen.values())


def parse_segments(data):
    sheets = read_ods(data)
    rows = sheets.get("5") or next(iter(sheets.values()))
    out = []
    for period, r in period_rows(rows):
        v = [it(x) for x in r[1:10]]
        if len(v) < 9:
            continue
        out.append(dict(zip(["period", "flights", "flights_intl", "flights_cross", "flights_dom",
                             "pax", "pax_intl", "pax_cross", "pax_dom", "pax_transit"], [period] + v)))
    return fix_years(out)


def roc_year(rows):
    for r in rows[:8]:
        for c in r:
            m = re.search(r"中華民國(\d{2,3})年", clean(c))
            if m:
                return int(m.group(1)) + 1911


def parse_loadfactor(data):
    sheets = read_ods(data)
    out = []
    for name, scope in LF_SHEETS.items():
        rows = sheets.get(name)
        if not rows:
            continue
        y = roc_year(rows)
        block = -1  # 每個分頁上下三段：國際及兩岸合計、國際、兩岸
        for r in rows:
            if r and clean(r[0]) == "月別":
                block += 1
                continue
            m = re.fullmatch(r"(\d{1,2})月", clean(r[0]) if r else "")
            if not m or len(r) < 13 or num(r[1]) is None or not 0 <= block <= 2:
                continue
            out.append({"month": f"{y}-{int(m.group(1)):02d}", "scope": scope, "region": ["all", "intl", "cross"][block],
                        "flights": it(r[1]), "seats": it(r[2]),
                        "pax": it(r[3]), "lf": num(r[4]), "in_pax": it(r[7]), "in_seats": it(r[6]),
                        "out_pax": it(r[11]), "out_seats": it(r[10])})
    return out


def parse_route_sheet(rows):
    """表36／42／53：區域列（國際航線、兩岸航線）→ 航點小計列 → 各航空公司列。只留航空公司列，航點小計可以加總回來。"""
    out, region, dest = [], None, None
    for r in rows:
        if len(r) < 14:
            continue
        a, b, c = clean(r[0]), clean(r[1]), clean(r[2])
        if a.startswith("國際"):
            region, dest = "intl", None
            continue
        if a.startswith("兩岸"):
            region, dest = "cross", None
            continue
        if b == "總計" or a == "總計" or not region:
            continue
        if b and not c:
            dest = b
            continue
        if c and dest and c != "合計":
            v = [it(x) for x in r[3:15]]
            out.append({"region": region, "dest": dest, "airline": c, "flights": v[0], "seats": v[1], "pax": v[2],
                        "in_seats": v[5], "in_pax": v[6], "out_seats": v[9], "out_pax": v[10]})
    return out


def period_of(rows):
    for r in rows[:10]:
        for c in r:
            s = clean(c)
            m = re.search(r"中華民國(\d{2,3})年(\d{1,2})月至\d{2,3}年(\d{1,2})月", s)
            if m:
                return f"{int(m.group(1)) + 1911}-ytd", int(m.group(3))
            m = re.search(r"中華民國(\d{2,3})年(\d{1,2})月份", s)
            if m:
                return f"{int(m.group(1)) + 1911}-{int(m.group(2)):02d}", None
            m = re.fullmatch(r"中華民國(\d{2,3})年", s)
            if m:
                return str(int(m.group(1)) + 1911), None
    return None, None


def parse_routes(data):
    """回傳 {期間: [列…]}，每列多一個 scope（ALL、TPE…）。"""
    sheets = read_ods(data)
    out, through = {}, {}
    for name, rows in sheets.items():
        m = re.fullmatch(r"(\d+)(-\d)?(_\d)?", name)
        if not m or m.group(3):
            continue
        scope = ROUTE_SCOPES.get(m.group(2) or "")
        if not scope:
            continue
        period, upto = period_of(rows)
        if not period:
            continue
        if upto:
            through[period] = upto
        for r in parse_route_sheet(rows):
            out.setdefault(period, []).append({"scope": scope, **r})
    return out, through


def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def merge_csv(path, rows, fields, key):
    """把新抓的列併進舊檔（同一個 key 用新的），舊月份保留，所以歷史會越存越多。"""
    old = {}
    if path.exists():
        with path.open(encoding="utf-8") as f:
            for r in csv.DictReader(f):
                old[tuple(r[k] for k in key)] = r
    for r in rows:
        old[tuple(str(r[k]) for k in key)] = r
    write_csv(path, sorted(old.values(), key=lambda r: tuple(str(r[k]) for k in key)), fields)


ROUTE_FIELDS = ["scope", "region", "dest", "airline", "flights", "seats", "pax", "in_pax", "in_seats", "out_pax", "out_seats"]


def save(kind, data):
    if kind == "airports":
        merge_csv(OUT / "airports.csv", parse_airports(data), ["period", "airport", "flights", "pax", "cargo"], ["period", "airport"])
    elif kind == "segments":
        merge_csv(OUT / "segments.csv", parse_segments(data),
                  ["period", "flights", "flights_intl", "flights_cross", "flights_dom", "pax", "pax_intl", "pax_cross", "pax_dom", "pax_transit"],
                  ["period"])
    elif kind == "loadfactor":
        merge_csv(OUT / "loadfactor.csv", parse_loadfactor(data),
                  ["month", "scope", "region", "flights", "seats", "pax", "lf", "in_pax", "in_seats", "out_pax", "out_seats"],
                  ["month", "scope", "region"])
    else:
        periods, through = parse_routes(data)
        for p, rows in periods.items():
            write_csv(OUT / "routes" / f"{p}.csv", rows, ROUTE_FIELDS)
        if through:
            meta = OUT / "routes/ytd.json"
            old = json.loads(meta.read_text()) if meta.exists() else {}
            old.update(through)
            meta.write_text(json.dumps(old, ensure_ascii=False, indent=1) + "\n")
    print(f"  {kind} 已更新")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    src_file = OUT / "source.json"
    seen = json.loads(src_file.read_text()) if src_file.exists() else {}
    force = "--force" in sys.argv
    for kind, fid in SOURCES.items():
        meta = get(CAA.format(fid)).decode("utf-8-sig")
        row = list(csv.reader(io.StringIO(meta)))[1]  # 名稱,版本,時間,路徑
        version, url = row[1], row[3]
        if seen.get(kind) == version and not force:
            print(f"{kind}：{version} 已經有了")
            continue
        print(f"{kind}：抓 {version}")
        save(kind, get(url))
        seen[kind] = version
    src_file.write_text(json.dumps(seen, ensure_ascii=False, indent=1) + "\n")


if __name__ == "__main__":
    main()
