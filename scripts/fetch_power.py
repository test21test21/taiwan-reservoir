#!/usr/bin/env python3
"""抓台電開放資料：即時各機組發電量、每日備轉容量率、每日尖峰負載、未來一週預估。

資料（service.taipower.com.tw，政府資料開放平台 8931、19995 等）：
- d006001/001.json：各機組即時發電量（每 10 分鐘）
- d006002/001.csv：今年每日尖峰備轉容量、備轉容量率
- d006004/001.csv：2023～去年每日尖峰備轉容量、備轉容量率
- d006005/001.csv：2025 年起每日淨尖峰供電能力、尖峰負載、備轉、工業／民生用電
- d006007/001.csv：未來一週電力供需預估
（www.taipower.com.tw 擋 GitHub 的主機，所以只用 service.taipower.com.tw）

輸出 data/power/：
- latest.json：最新一次各機組發電量
- hourly/YYYY-MM.csv：每次抓到的各類發電加總（每小時一筆，畫「今天的發電」）
- reserve.csv：date,reserve,rate（萬瓩、%），2023 年起
- daily.csv：date,supply,peak,reserve,rate,industry,home（萬瓩、%、百萬度），2025 年起
- forecast.csv：date,supply,peak,rate,reserve

    python3 scripts/fetch_power.py
"""
import csv
import io
import json
import re
import ssl
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data/power"
BASE = "https://service.taipower.com.tw/data/opendata/apply/file/"
UA = "Mozilla/5.0 (compatible; taiwandata.info)"

# 發電類別：台電的機組類型 → 本站的類別代號（民營電廠併入同燃料）
FUEL = {"核能": "nuclear", "燃煤": "coal", "民營電廠-燃煤": "coal", "燃氣": "lng", "民營電廠-燃氣": "lng",
        "汽電共生": "cogen", "燃料油": "oil", "燃油": "oil", "輕油": "oil", "太陽能": "solar", "風力": "wind",
        "水力": "hydro", "其它再生能源": "other", "其他再生能源": "other", "儲能": "storage", "儲能負載": "storage_load"}
FUELS = ["nuclear", "coal", "lng", "cogen", "oil", "solar", "wind", "hydro", "other", "storage", "storage_load"]


def ssl_context():
    ctx = ssl.create_default_context()
    ctx.verify_flags &= ~getattr(ssl, "VERIFY_X509_STRICT", 0)
    return ctx


def get(name, tries=4):
    for i in range(tries):
        try:
            req = urllib.request.Request(BASE + name, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60, context=ssl_context()) as r:
                return r.read().decode("utf-8-sig")
        except Exception as ex:
            if i == tries - 1:
                raise
            print(f"  重試 {name}：{ex}", file=sys.stderr)
            time.sleep(3 * (i + 1))


def num(x):
    try:
        return float(str(x).replace(",", "").strip())
    except ValueError:
        return None


def clean(s):
    return re.sub(r"<[^>]+>", "", s or "").strip()


def fuel_of(t):
    t = clean(t)
    zh = t.split("(")[0].strip()
    return FUEL.get(zh, "other")


def live():
    d = json.loads(get("d006001/001.json"))
    units = []
    for r in d.get("aaData", []):
        name = clean(r.get("機組名稱"))
        if not name or name.startswith("小計"):
            continue
        units.append({
            "type": clean(r.get("機組類型")).split("(")[0].strip(),
            "fuel": fuel_of(r.get("機組類型")),
            "name": name,
            "cap": num(r.get("裝置容量(MW)")),
            "mw": num(r.get("淨發電量(MW)")),
            "note": clean(r.get("備註")),
        })
    t = d.get("DateTime", "")[:16]
    return t, units


def table(name, keys):
    rows = list(csv.reader(io.StringIO(get(name))))
    out = {}
    for r in rows[1:]:
        if not r or not re.fullmatch(r"\d{8}", r[0].strip()):
            continue
        dt = f"{r[0][:4]}-{r[0][4:6]}-{r[0][6:8]}"
        out[dt] = [num(x) for x in r[1:1 + len(keys)]]
    return out


def write_csv(path, head, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(head)
        for r in rows:
            w.writerow(["" if v is None else (f"{v:g}" if isinstance(v, float) else v) for v in r])


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    ok = True

    try:
        t, units = live()
        (OUT / "latest.json").write_text(json.dumps({"time": t, "units": units}, ensure_ascii=False, indent=0), encoding="utf-8")
        tot = {k: 0.0 for k in FUELS}
        for u in units:
            tot[u["fuel"]] += u["mw"] or 0
        path = OUT / "hourly" / f"{t[:7]}.csv"
        old = list(csv.reader(path.open(encoding="utf-8"))) if path.exists() else [["time"] + FUELS]
        if not any(r[0] == t for r in old[1:]):
            old.append([t] + [f"{tot[k]:.1f}" for k in FUELS])
            write_csv(path, old[0], sorted(old[1:]))
        print(f"即時發電 {t}：{sum(v for k, v in tot.items() if k != 'storage_load'):,.0f} MW，{len(units)} 部機組")
    except Exception as ex:
        ok = False
        print(f"即時發電抓取失敗：{ex}", file=sys.stderr)

    try:
        res = table("d006004/001.csv", ["reserve", "rate"])
        res.update(table("d006002/001.csv", ["reserve", "rate"]))
        old = {r["date"]: [num(r["reserve"]), num(r["rate"])] for r in csv.DictReader((OUT / "reserve.csv").open(encoding="utf-8"))} \
            if (OUT / "reserve.csv").exists() else {}
        old.update(res)
        write_csv(OUT / "reserve.csv", ["date", "reserve", "rate"], [[k] + v for k, v in sorted(old.items())])
        print(f"備轉容量率：{len(old)} 天，到 {max(old)}")
    except Exception as ex:
        ok = False
        print(f"備轉容量率抓取失敗：{ex}", file=sys.stderr)

    try:
        keys = ["supply", "peak", "reserve", "rate", "industry", "home"]
        daily = table("d006005/001.csv", keys)
        old = {r["date"]: [num(r[k]) for k in keys] for r in csv.DictReader((OUT / "daily.csv").open(encoding="utf-8"))} \
            if (OUT / "daily.csv").exists() else {}
        old.update(daily)
        write_csv(OUT / "daily.csv", ["date"] + keys, [[k] + v for k, v in sorted(old.items())])
        print(f"每日尖峰負載：{len(old)} 天，到 {max(old)}")
    except Exception as ex:
        ok = False
        print(f"每日尖峰負載抓取失敗：{ex}", file=sys.stderr)

    try:
        keys = ["supply", "peak", "rate", "reserve"]
        fc = table("d006007/001.csv", keys)
        if fc:
            write_csv(OUT / "forecast.csv", ["date"] + keys, [[k] + v for k, v in sorted(fc.items())])
        print(f"未來一週預估：{len(fc)} 天")
    except Exception as ex:
        ok = False
        print(f"未來一週預估抓取失敗：{ex}", file=sys.stderr)

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
