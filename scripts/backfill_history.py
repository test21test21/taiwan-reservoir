"""補抓過去的水庫蓄水量（水利署防災資訊網「水庫水情比對」），寫進 data/history.csv。

用法：python3 scripts/backfill_history.py 2025-09-01 2026-10-09
- 只補 history.csv 還沒有的日期，不會蓋掉每小時抓的資料。
- 每天是早上 7 點的官方數字；只補蓄水量、蓄水率、水位（進出水量的日期定義不同，留空）。
- 水利署這個頁面只有 21 座主要水庫。
"""
import csv
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(__file__))
from fetch_reservoirs import HISTORY_FIELDS, read_history, ssl_context  # noqa: E402

API = "https://fhy.wra.gov.tw/Disaster/api/ReservoirHistoryApi/GetComparision"
STATIONS = "https://fhy.wra.gov.tw/Disaster/api/ReservoirStationsApi/GetAll"
UA = {"User-Agent": "reservoir-site/0.1"}


def get(url, data=None):
    for i in range(3):
        try:
            body = urllib.parse.urlencode(data).encode() if data else None
            req = urllib.request.Request(url, data=body, headers=UA)
            with urllib.request.urlopen(req, timeout=60, context=ssl_context()) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception:
            if i == 2:
                raise
            time.sleep(5 * (i + 1))


def drop_spikes(rows, keys):
    """單獨一天跳很大、前後兩天又很接近的值多半是資料錯誤（例如明德 70%→4.7%→70%），拿掉。"""
    by_id = {}
    for d, rid in sorted(rows):
        p = rows[(d, rid)].get("percent")
        if p not in (None, ""):
            by_id.setdefault(rid, []).append((d, float(p)))
    bad = []
    for rid, v in by_id.items():
        for (_, a), (d, b), (_, c) in zip(v, v[1:], v[2:]):
            if (d, rid) in keys and abs(a - c) <= 5 and abs(b - a) > 15 and abs(b - c) > 15:
                bad.append((d, rid))
    for k in bad:
        del rows[k]
    return len(bad)


def main(start, end, data_dir="data"):
    path = os.path.join(data_dir, "history.csv")
    rows = read_history(path)
    stations = [s["ST_NO"] for s in get(STATIONS)]
    groups = [stations[i:i + 8] for i in range(0, len(stations), 8)]  # 一次最多 8 座
    d, end = date.fromisoformat(start), date.fromisoformat(end)
    added_keys, skipped = set(), 0
    while d <= end:
        d2 = min(d + timedelta(days=1), end)
        for g in groups:
            for x in get(API, {"ST_NO": ",".join(g), "StartDate": d.strftime("%Y/%m/%d"), "EndDate": d2.strftime("%Y/%m/%d")}) or []:
                day = (x.get("DATE") or "")[:10]
                key = (day, x["ST_NO"])
                if not day or key in rows:
                    continue
                storage, rate = x.get("Capacity"), x.get("CapacityRate")
                if not storage or not rate or not 0 < rate <= 1.05:  # 缺值、0 或明顯錯誤就跳過
                    skipped += 1
                    continue
                rows[key] = {"date": day, "id": x["ST_NO"], "name": x.get("NAME_C"),
                             "storage": round(storage, 2), "capacity": round(storage / rate, 1),
                             "percent": round(rate * 100, 2), "water_level": x.get("WaterLine")}
                added_keys.add(key)
            time.sleep(0.3)
        d = d2 + timedelta(days=1)
    spikes = drop_spikes(rows, added_keys)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=HISTORY_FIELDS)
        w.writeheader()
        for key in sorted(rows):
            w.writerow({k: ("" if rows[key].get(k) is None else rows[key].get(k)) for k in HISTORY_FIELDS})
    print(f"added {len(added_keys) - spikes} rows, skipped {skipped} bad values, dropped {spikes} one-day spikes")


if __name__ == "__main__":
    main(*sys.argv[1:3])
