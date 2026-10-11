#!/usr/bin/env python3
"""抓內政部戶政司「動態資料統計表」（每月、各村里的出生數、死亡數），加總成各縣市每月數字。

資料：https://www.ris.gov.tw/rs-opendata/api/v1/datastore/<表號>/<民國年月>
- ODRP012：民國 107/01 ～ 109/08（動態資料統計表，新增區域代碼）
- ODRP061：民國 109/09 起（動態資料統計表，含同婚）

輸出 data/births/monthly.csv：month,county,births_m,births_f,deaths_m,deaths_f,population
已經抓過的月份不重抓；最新月份往後試，抓到「查無資料」就停。

    python3 scripts/fetch_births.py            # 補齊缺的月份
    python3 scripts/fetch_births.py --since 2024-01
"""
import csv
import json
import sys
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data/births/monthly.csv"
API = "https://www.ris.gov.tw/rs-opendata/api/v1/datastore"
FIELDS = ["month", "county", "births_m", "births_f", "deaths_m", "deaths_f", "population"]
FIRST = (2018, 1)


def table_for(y, m):
    return "ODRP061" if (y, m) >= (2020, 9) else "ODRP012"


def get(url, tries=4):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "taiwandata.info"})
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as ex:  # 偶爾逾時，等一下再試
            if i == tries - 1:
                raise
            print(f"  重試 {url}：{ex}", file=sys.stderr)
            time.sleep(3 * (i + 1))


def n(x):
    try:
        return int(str(x).replace(",", "").strip() or 0)
    except ValueError:
        return 0


def fetch_month(y, m):
    """回傳 {縣市: [出生男, 出生女, 死亡男, 死亡女, 人口]}；沒有這個月的資料回傳 None。"""
    ym = f"{y - 1911}{m:02d}"
    url = f"{API}/{table_for(y, m)}/{ym}"
    agg = defaultdict(lambda: [0, 0, 0, 0, 0])
    page, pages = 1, 1
    while page <= pages:
        d = get(url + "?" + urllib.parse.urlencode({"PAGE": page}))
        rows = d.get("responseData") or []
        if not rows:
            return None if page == 1 else agg
        pages = n(d.get("totalPage")) or 1
        for r in rows:
            county = (r.get("site_id") or "").strip()[:3]
            if not county:
                continue
            a = agg[county]
            a[0] += n(r.get("birth_total_m"))
            a[1] += n(r.get("birth_total_f"))
            a[2] += n(r.get("death_m"))
            a[3] += n(r.get("death_f"))
            a[4] += n(r.get("people_total"))
        page += 1
        time.sleep(0.3)
    return agg


def months_from(start, end):
    y, m = start
    while (y, m) <= end:
        yield y, m
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def main():
    since = FIRST
    if "--since" in sys.argv:
        s = sys.argv[sys.argv.index("--since") + 1]
        since = (int(s[:4]), int(s[5:7]))
    rows = []
    if OUT.exists():
        with OUT.open(encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
    have = {r["month"] for r in rows}
    today = date.today()
    added, misses = 0, 0
    for y, m in months_from(since, (today.year, today.month)):
        key = f"{y}-{m:02d}"
        if key in have:
            continue
        agg = fetch_month(y, m)
        if agg is None:
            print(f"{key}：查無資料")
            misses += 1
            continue
        tb = sum(a[0] + a[1] for a in agg.values())
        td = sum(a[2] + a[3] for a in agg.values())
        print(f"{key}：出生 {tb:,}、死亡 {td:,}（{len(agg)} 縣市）")
        for c, a in sorted(agg.items()):
            rows.append(dict(zip(FIELDS, [key, c, *a])))
        added += 1
    rows.sort(key=lambda r: (r["month"], r["county"]))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f"新增 {added} 個月，共 {len({r['month'] for r in rows})} 個月")


if __name__ == "__main__":
    main()
