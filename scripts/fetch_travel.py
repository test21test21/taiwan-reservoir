#!/usr/bin/env python3
"""抓交通部觀光署「觀光統計」開放資料（每年），整理成 data/travel/ 的 CSV。

資料：https://stat.taiwan.net.tw/data/opendata/<編號>（data.gov.tw 上的「歷年來台旅客…統計」等資料集）
- 7  歷年來台旅客居住地統計（2002 年起，每年一欄）
- 1  歷年國人出國首站抵達地統計（2002 年起，每年一欄）
- 12 歷年來台旅客統計（1956 年起，每年總數）
- 17 歷年國人出國按性別分析（1984 年起，每年總數）
- 6  歷年來台旅客來台目的統計（按居住地）
- 13 歷年來台旅客搭乘交通工具及入境港口統計（按居住地）

輸出（data/travel/）：
- inbound.csv   year,area,place,count     來台旅客，按居住地
- outbound.csv  year,area,place,count     國人出國，按首站抵達地
- totals.csv    year,inbound,outbound     歷年總數
- purpose.csv   year,place,purpose,count  來台目的（業務、觀光、探親…）
- ports.csv     year,place,port,count     入境機場／港口

    python3 scripts/fetch_travel.py
"""
import csv
import io
import re
import ssl
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data/travel"
URL = "https://stat.taiwan.net.tw/data/opendata/{}"
PURPOSES = ["業務", "觀光", "探親", "會議", "求學", "展覽", "醫療", "其他"]
PORTS = ["飛機松山", "飛機桃園", "飛機臺中", "飛機高雄", "飛機其他", "輪船小計"]


def ssl_context():
    # 政府網站憑證鏈缺 Subject Key Identifier，Python 3.13 的嚴格模式會拒絕；仍照常驗證憑證。
    ctx = ssl.create_default_context()
    ctx.verify_flags &= ~getattr(ssl, "VERIFY_X509_STRICT", 0)
    return ctx


def get(n, tries=4):
    for i in range(tries):
        try:
            req = urllib.request.Request(URL.format(n), headers={"User-Agent": "taiwandata.info"})
            with urllib.request.urlopen(req, timeout=120, context=ssl_context()) as r:
                return r.read().decode("utf-8-sig")
        except Exception as ex:
            if i == tries - 1:
                raise
            print(f"  重試 {n}：{ex}", file=sys.stderr)
            time.sleep(3 * (i + 1))


def rows(text):
    return list(csv.reader(io.StringIO(text)))


def it(x):
    x = str(x).replace(",", "").replace("%", "").strip()
    try:
        return int(float(x))
    except ValueError:
        return None


def place(s):
    """「日本 Japan」「日本Japan」→ 一律「日本 Japan」；「總計 Grand Total」等保留。"""
    s = re.sub(r"\s+", " ", s.strip())
    return re.sub(r"([^\x00-\x7f])([A-Za-z])", r"\1 \2", s)


def wide(text):
    """地區,細分,2002,2003,… → [(年, 地區, 細分, 人次)]"""
    r = rows(text)
    years = r[0][2:]
    out = []
    for row in r[1:]:
        if len(row) < 3:
            continue
        for y, v in zip(years, row[2:]):
            v = it(v)
            if v is not None and y.strip().isdigit():
                out.append({"year": int(y), "area": row[0].strip(), "place": place(row[1]), "count": v})
    return out


def yearly_total(text, col):
    r = rows(text)
    i = r[0].index(col) if col in r[0] else 1
    return {int(row[0]): it(row[i]) for row in r[1:] if row and row[0].strip().isdigit() and it(row[i]) is not None}


def long(text, cols, name):
    """年別,居住地,細分,合計,業務,觀光… → [(年, 細分, 欄名, 人次)]；只留各國和總計，不留洲小計。"""
    r = rows(text)
    head = [h.strip() for h in r[0]]
    out = []
    for row in r[1:]:
        if len(row) < len(head) or not row[0].strip().isdigit():
            continue
        p = place(row[2])
        for c in cols:
            if c in head and it(row[head.index(c)]) is not None:
                out.append({"year": int(row[0]), "place": p, name: c, "count": it(row[head.index(c)])})
    return out


def write(name, rows_, fields):
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / name).open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows_)


def build(src):
    """src：{編號: CSV 文字}"""
    write("inbound.csv", wide(src[7]), ["year", "area", "place", "count"])
    write("outbound.csv", wide(src[1]), ["year", "area", "place", "count"])
    inb, outb = yearly_total(src[12], "總計人數"), yearly_total(src[17], "合計")
    write("totals.csv", [{"year": y, "inbound": inb.get(y, ""), "outbound": outb.get(y, "")} for y in sorted(set(inb) | set(outb))],
          ["year", "inbound", "outbound"])
    write("purpose.csv", long(src[6], PURPOSES, "purpose"), ["year", "place", "purpose", "count"])
    write("ports.csv", long(src[13], PORTS, "port"), ["year", "place", "port", "count"])


def main():
    build({n: get(n) for n in (7, 1, 12, 17, 6, 13)})
    print("觀光署資料已更新")


if __name__ == "__main__":
    main()
