#!/usr/bin/env python3
"""抓財政部稅收與綜合所得資料。

資料：
- 全國賦稅收入實徵淨額日曆年別－按稅目別分（財政部統計處，每月；data.gov.tw 6671）
- 全國賦稅收入實徵淨額與預算數之比較（每年；data.gov.tw 16910）
- 綜稅綜合所得總額全國各縣市鄉鎮村里統計分析表（財政部財政資訊中心，每年；data.gov.tw 103066）

輸出：
- data/tax/monthly.csv：ym,total,<各稅目>（千元），1974 年起每月
- data/tax/budget.csv：year,item,actual,budget,rate（千元、%），2001 年起每年
- data/income/towns.csv：year,town,households,total,mean,median,q1,q3（戶、千元），2012 年起（所得年度，西元）
- data/income/villages.csv：最新一年各村里同樣欄位（town,village,...）

web02.mof.gov.tw 只有 GitHub Actions 連得到；www.fia.gov.tw 偶爾斷線，會重試。

    python3 scripts/fetch_tax.py
"""
import csv
import io
import re
import ssl
import sys
import time
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TAX = ROOT / "data/tax"
INC = ROOT / "data/income"
UA = "Mozilla/5.0 (compatible; taiwandata.info)"
MOF = "https://web02.mof.gov.tw/njswww/webMain.aspx?sys=220&utf=1&outmode=12&compmode=00&kind=21"
MONTHLY = MOF + "&ym=6300&type=5&funid=i0421&cycle=41&outkind=11&fldspc=0,44,45,9,"
BUDGET = MOF + "&ym=9000&type=3&funid=i3451&cycle=4&outkind=3&fldlst=1111&codspc0=0,34,"
FIA = "https://www.fia.gov.tw/WEB/fia/ias/ias{y}/{y}_165-9.csv"

# 每月稅收要留的欄位（財政部欄名 → 代號）；房地合一稅已含在所得稅裡
COLS = {"總計": "total", "所得稅小計": "income", "營利事業所得稅": "corp", "綜合所得稅": "personal", "營業稅": "vat",
        "證券交易稅": "stock", "貨物稅": "commodity", "關稅": "customs", "土地稅小計": "land", "房屋稅": "house",
        "菸酒稅": "tobacco", "遺產及贈與稅": "estate", "使用牌照稅": "vehicle", "期貨交易稅": "futures",
        "特種貨物及勞務稅": "luxury", "契稅": "deed", "印花稅": "stamp", "娛樂稅": "amusement",
        "特別及臨時稅課": "special", "健康福利捐": "health", "房地合一稅合計": "realestate"}


def ssl_context():
    ctx = ssl.create_default_context()
    ctx.verify_flags &= ~getattr(ssl, "VERIFY_X509_STRICT", 0)
    return ctx


def get(url, tries=5):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=120, context=ssl_context()) as r:
                return r.status, r.read().decode("utf-8-sig", "replace")
        except urllib.error.HTTPError as ex:
            if ex.code == 404:
                return 404, ""
            err = ex
        except Exception as ex:
            err = ex
        if i == tries - 1:
            raise err
        print(f"  重試 {url[:80]}：{err}", file=sys.stderr)
        time.sleep(4 * (i + 1))


def num(x):
    x = (x or "").replace(",", "").strip()
    if x in ("", "－", "-", "…"):
        return 0.0
    try:
        return float(x)
    except ValueError:
        return 0.0


def write(path, head, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(head)
        w.writerows(rows)


def g(v):
    return f"{v:.0f}" if float(v).is_integer() else f"{v:g}"


def monthly(text=None):
    text = text or get(MONTHLY)[1]
    rows = list(csv.reader(io.StringIO(text)))
    head = [h.strip().lstrip("﻿") for h in rows[0]]
    out = []
    for r in rows[1:]:
        m = re.fullmatch(r"(\d+)年\s*(\d+)月", (r[0] if r else "").strip())
        if not m:
            continue
        d = dict(zip(head, r))
        out.append([f"{int(m[1]) + 1911}-{int(m[2]):02d}"] + [g(num(d.get(k))) for k in COLS])
    if len(out) < 100:
        raise RuntimeError(f"每月稅收只有 {len(out)} 筆，格式可能變了")
    write(TAX / "monthly.csv", ["ym"] + list(COLS.values()), sorted(out))
    print(f"每月稅收：{len(out)} 個月，到 {max(out)[0]}")


def budget(text=None):
    text = text or get(BUDGET)[1]
    out = []
    for r in list(csv.reader(io.StringIO(text)))[1:]:
        m = re.fullmatch(r"(\d+)年/\s*(.+)", (r[0] if r else "").strip())
        if not m or len(r) < 5:
            continue
        item = m[2].replace("　", "").strip()
        out.append([int(m[1]) + 1911, item, g(num(r[1])), g(num(r[2])), r[4].strip() if r[4].strip() not in ("－", "-") else ""])
    if not out:
        raise RuntimeError("稅收與預算比較沒有資料")
    write(TAX / "budget.csv", ["year", "item", "actual", "budget", "rate"], out)
    print(f"稅收與預算：到 {max(r[0] for r in out)} 年")


def income():
    """各年度鄉鎮市區（合計列）；最新一年另存各村里。"""
    towns = {}
    if (INC / "towns.csv").exists():
        for r in csv.DictReader((INC / "towns.csv").open(encoding="utf-8")):
            towns[(int(r["year"]), r["town"])] = r
    have = {y for y, _ in towns}
    # 第一次抓全部年度；之後只試還沒有的下一、兩年（財政部每年公布一次）
    years = [y + 1911 for y in range(101, date.today().year - 1911)] if not have else [max(have) + 1, max(have) + 2]
    latest_villages = None
    for y in years:
        code, text = get(FIA.format(y=y - 1911))
        if code == 404 or not text.strip():
            continue
        vil = []
        for r in list(csv.reader(io.StringIO(text)))[1:]:
            if len(r) < 8 or not r[0].strip():
                continue
            town, name = r[0].strip(), r[1].strip()
            vals = [g(num(x)) for x in r[2:8]]
            if name == "合計":
                towns[(y, town)] = dict(zip(["year", "town", "households", "total", "mean", "median", "q1", "q3"], [y, town] + vals))
            elif name != "其他":
                vil.append([y, town, name] + vals)
        if vil:
            latest_villages = vil
        print(f"所得：{y} 年 {sum(1 for k in towns if k[0] == y)} 個鄉鎮市區、{len(vil)} 個村里")
    keys = ["year", "town", "households", "total", "mean", "median", "q1", "q3"]
    write(INC / "towns.csv", keys, [[towns[k][c] for c in keys] for k in sorted(towns)])
    if latest_villages:
        write(INC / "villages.csv", ["year", "town", "village", "households", "total", "mean", "median", "q1", "q3"], latest_villages)


def main():
    ok = True
    for name, fn in (("每月稅收", monthly), ("稅收與預算", budget), ("所得", income)):
        try:
            fn()
        except Exception as ex:
            ok = False
            print(f"{name}抓取失敗：{ex}", file=sys.stderr)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
