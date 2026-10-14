#!/usr/bin/env python3
"""抓水利署水庫開放資料，整理成乾淨格式，並存每日快照。

資料來源（政府資料開放平臺）：
  41568 水庫每日營運狀況  -> 每日：有效容量、進水量、取用水量、集水區雨量…
  45501 水庫水情資料      -> 每小時：有效蓄水量、水位、進出流量…

輸出（data/ 底下）：
  latest.json                  每座水庫最新一筆（網站直接讀這個）
  snapshots/YYYY-MM-DD.json    當天的快照，累積成歷史
  history.csv                  一列一座水庫一天，方便畫趨勢

用法：
  python3 fetch_reservoirs.py                 # 線上抓
  python3 fetch_reservoirs.py --raw-dir DIR   # 改讀 DIR/daily.json、DIR/hourly.json
只用 Python 標準函式庫，GitHub Actions 上可直接跑。
"""
import argparse
import csv
import json
import os
import re
import ssl
import sys
import struct
import time
import urllib.request
import zlib
from datetime import datetime, timedelta, timezone

TW = timezone(timedelta(hours=8))
DAILY_URL = "https://opendata.wra.gov.tw/api/v2/51023e88-4c76-4dbc-bbb9-470da690d539?format=JSON"
HOURLY_URL = "https://opendata.wra.gov.tw/api/v2/2be9044c-6e44-4856-aad5-dd108c2e6679?format=JSON"

ALERT_PAGE = "https://www.wra.gov.tw/EarlyWarning.aspx?n=18804&sms=9114"

HISTORY_FIELDS = [
    "date", "id", "name", "storage", "capacity", "percent",
    "water_level", "inflow_daily", "outflow_daily", "rainfall_daily", "use_daily",
]


def ssl_context():
    # 政府網站憑證鏈缺 Subject Key Identifier，Python 3.13 的嚴格模式會拒絕；
    # 仍照常驗證憑證，只關掉嚴格檢查。
    ctx = ssl.create_default_context()
    ctx.verify_flags &= ~getattr(ssl, "VERIFY_X509_STRICT", 0)
    return ctx


def fetch_json(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "reservoir-site/0.1"})
            with urllib.request.urlopen(req, timeout=60, context=ssl_context()) as r:
                return json.loads(r.read().decode("utf-8-sig"))
        except Exception as ex:  # 水利署偶爾逾時，等一下再試
            if i == tries - 1:
                raise
            print(f"  重試 {url}：{ex}", file=sys.stderr)
            time.sleep(10 * (i + 1))


def as_rows(payload):
    """API 可能直接回 list，也可能包在某個 key 裡。"""
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for v in payload.values():
            if isinstance(v, list) and v and isinstance(v[0], dict):
                return v
    raise ValueError("看不懂的資料格式")


def lower_keys(row):
    return {str(k).strip().lower(): v for k, v in row.items()}


def num(v):
    if v is None:
        return None
    s = str(v).strip().replace(",", "")
    if s in ("", "-", "--", "null", "None"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def parse_time(v):
    """支援 2023-05-03T13:20:10、2023-05-03t13:20:10、20230503t132010、2023/05/03 13:20 等。"""
    if not v:
        return None
    s = str(v).strip().upper().replace("/", "-")
    m = re.match(r"^(\d{4})(\d{2})(\d{2})T?(\d{2})(\d{2})(\d{2})?$", s)
    if m:
        y, mo, d, h, mi, se = m.groups()
        return datetime(int(y), int(mo), int(d), int(h), int(mi), int(se or 0), tzinfo=TW)
    s = s.replace(" ", "T")
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(s[:19], fmt).replace(tzinfo=TW)
        except ValueError:
            pass
    try:
        t = datetime.fromisoformat(s)
        return t if t.tzinfo else t.replace(tzinfo=TW)
    except ValueError:
        return None


def latest_by_id(rows, time_key):
    best = {}
    for r in rows:
        rid = str(r.get("reservoiridentifier") or "").strip()
        t = parse_time(r.get(time_key))
        if not rid or not t:
            continue
        if rid not in best or t > best[rid][0]:
            best[rid] = (t, r)
    return best


def load_info(data_dir):
    """水庫基本資料（資料集 32726）：補名稱和地區。"""
    path = os.path.join(data_dir, "reservoir_info.json")
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8-sig") as f:
        rows = json.load(f)
    return {str(r.get("水庫代碼")).strip(): r for r in rows}


def region_of(rid, info):
    area = (info.get(rid) or {}).get("地區別", "")
    for key, name in (("北", "北部"), ("中", "中部"), ("南", "南部"), ("東", "東部"), ("澎湖", "澎湖")):
        if key in area:
            return name
    if rid.startswith("501"):
        return "澎湖"
    if rid.startswith("502"):
        return "金門"
    if rid.startswith("503"):
        return "馬祖"
    return {"1": "北部", "2": "中部", "3": "南部", "4": "東部"}.get(rid[:1], "其他")


def build(daily_rows, hourly_rows, info=None):
    info = info or {}
    daily = latest_by_id([lower_keys(r) for r in daily_rows], "datetime")
    hourly = latest_by_id([lower_keys(r) for r in hourly_rows], "observationtime")

    out = []
    for rid in sorted(set(daily) | set(hourly)):
        d_t, d = daily.get(rid, (None, {}))
        h_t, h = hourly.get(rid, (None, {}))
        capacity = num(d.get("capacity"))
        storage = num(h.get("effectivewaterstoragecapacity"))
        percent = round(storage / capacity * 100, 2) if storage is not None and capacity else None
        name = (d.get("reservoirname") or (info.get(rid) or {}).get("水庫名稱") or "").strip()
        out.append({
            "id": rid,
            "name": name or None,
            "region": region_of(rid, info),
            "purpose": ((info.get(rid) or {}).get("功能") or None),
            # 即時（每小時）
            "observed_at": h_t.isoformat() if h_t else None,
            "storage": storage,                       # 有效蓄水量（萬立方公尺）
            "capacity": capacity,                     # 有效容量（萬立方公尺）
            "percent": percent,                       # 蓄水百分比（自己算）
            "water_level": num(h.get("waterlevel")),  # 水位（公尺）
            "inflow_cms": num(h.get("inflowdischarge")),
            "outflow_cms": num(h.get("totaloutflow")),
            "rainfall_today": num(h.get("accumulaterainfallincatchment")),
            "status": (h.get("statustype") or None),
            # 蓄水率超過 105% 多半是來源資料填錯（例如容量單位不一致），網站上要另外標示
            "suspect": percent is not None and percent > 105,
            # 每日營運（前一日統計）
            "daily_date": d_t.date().isoformat() if d_t else None,
            "inflow_daily": num(d.get("inflow")),     # 進水量（萬立方公尺）
            "outflow_daily": num(d.get("outflow")),   # 取用水量（萬立方公尺）
            "outflow_total_daily": num(d.get("outflowtotal")),
            "rainfall_daily": num(d.get("basinrainfall")),
            "dead_level": num(d.get("dwl")),
            "full_level": num(d.get("nwlmax")),
        })
    # 有些水庫只出現在每小時資料，沒有名稱和容量，就沒辦法算蓄水率；先保留但排在後面
    out.sort(key=lambda r: (r["name"] is None, r["id"]))
    return out


def daily_use(r):
    """每天用掉的水（萬立方公尺）：優先用「取用水量」，沒有就用「出水量合計」。"""
    for k in ("outflow_daily", "outflow_total_daily"):
        v = r.get(k)
        if v is not None and v > 0:
            return v
    return None


def read_history(path):
    rows = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                rows[(r["date"], r["id"])] = r
    return rows


def add_estimates(reservoirs, history, today):
    """去年同期：history 裡一年前（前後 3 天內）同一座水庫的蓄水率。
    可用天數不自己估算，以政府公告為準。"""
    by_id = {}
    for (d, rid), row in history.items():
        by_id.setdefault(rid, []).append((d, row))
    t = datetime.fromisoformat(today).date()
    for r in reservoirs:
        r["use_daily"] = daily_use(r)
        past = sorted(by_id.get(r["id"], []))
        r["last_year_percent"] = None
        r["last_year_date"] = None
        for off in (0, 1, -1, 2, -2, 3, -3):
            try:
                ly = (t.replace(year=t.year - 1) + timedelta(days=off)).isoformat()
            except ValueError:  # 2/29
                ly = (t - timedelta(days=365 - off)).isoformat()
            row = next((row for d, row in past if d == ly), None)
            p = num(row.get("percent")) if row else None
            if p is not None and p <= 105:
                r["last_year_percent"], r["last_year_date"] = p, ly
                break


def write_outputs(reservoirs, data_dir, now):
    os.makedirs(os.path.join(data_dir, "snapshots"), exist_ok=True)
    today = now.date().isoformat()
    path = os.path.join(data_dir, "history.csv")
    rows = read_history(path)
    add_estimates(reservoirs, rows, today)
    doc = {"generated_at": now.isoformat(timespec="seconds"), "count": len(reservoirs), "reservoirs": reservoirs}

    with open(os.path.join(data_dir, "latest.json"), "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)

    with open(os.path.join(data_dir, "snapshots", f"{today}.json"), "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)

    # history.csv：同一天同一座水庫只留最新一筆
    for r in reservoirs:
        rows[(today, r["id"])] = {"date": today, **{k: r.get(k) for k in HISTORY_FIELDS if k != "date"}}
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=HISTORY_FIELDS)
        w.writeheader()
        for key in sorted(rows):
            w.writerow({k: ("" if rows[key].get(k) is None else rows[key].get(k)) for k in HISTORY_FIELDS})


def fetch_text(url):
    req = urllib.request.Request(url, headers={"User-Agent": "reservoir-site/0.1"})
    with urllib.request.urlopen(req, timeout=60, context=ssl_context()) as r:
        return r.read().decode("utf-8", "replace")


def png_pixels(data):
    """解 8-bit RGB/RGBA/調色盤、非交錯的 PNG，回傳 (寬, 高, 每列 RGBA bytes 的 list)。看不懂就回傳 None。"""
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    pos, idat, w, h, bpp, ctype, plte, trns = 8, b"", 0, 0, 4, 6, b"", b""
    while pos < len(data):
        n, typ = struct.unpack(">I4s", data[pos:pos + 8])
        chunk = data[pos + 8:pos + 8 + n]
        if typ == b"IHDR":
            w, h, depth, ctype, _, _, interlace = struct.unpack(">IIBBBBB", chunk)
            if depth != 8 or ctype not in (2, 3, 6) or interlace:
                return None
            bpp = {6: 4, 2: 3, 3: 1}[ctype]
        elif typ == b"PLTE":
            plte = chunk
        elif typ == b"tRNS":
            trns = chunk
        elif typ == b"IDAT":
            idat += chunk
        pos += 12 + n
    raw, stride, prev, rows, i = zlib.decompress(idat), w * bpp, None, [], 0
    for _ in range(h):
        f, line = raw[i], bytearray(raw[i + 1:i + 1 + stride])
        i += 1 + stride
        for x in range(stride):
            a = line[x - bpp] if x >= bpp else 0
            b = prev[x] if prev else 0
            c = prev[x - bpp] if prev and x >= bpp else 0
            if f == 1: line[x] = (line[x] + a) & 255
            elif f == 2: line[x] = (line[x] + b) & 255
            elif f == 3: line[x] = (line[x] + (a + b) // 2) & 255
            elif f == 4:
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                line[x] = (line[x] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        prev = line
        if ctype == 6:
            rows.append(line)
        elif ctype == 2:
            rows.append(bytearray(b"".join(bytes(line[x:x + 3]) + b"\xff" for x in range(0, stride, 3))))
        else:
            rows.append(bytearray(b"".join(plte[k * 3:k * 3 + 3] + bytes([trns[k] if k < len(trns) else 255]) for k in line)))
    return w, h, rows


def light_of(r, g, b, a):
    """把燈號圖上的一個像素分類成燈號：N 正常（沒上色）、G 綠、Y 黃、O 橙、R 紅。"""
    if a < 128 or max(r, g, b) - min(r, g, b) < 60:
        return "N"
    import colorsys
    hue = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)[0] * 360
    if hue < 15 or hue >= 330:
        return "R"
    if hue < 40:
        return "O"
    if hue < 70:
        return "Y"
    if hue < 170:
        return "G"
    return "N"  # 藍色系＝水情正常


# 官方燈號圖（480×568）上各縣市內部的一個點。官方換了圖的尺寸就不用這些點，只顯示原圖。
MAP_SIZE = (480, 568)
COUNTY_SEEDS = {
    "基隆市": (386, 42), "臺北市": (362, 45), "新北市": (345, 80), "桃園市": (300, 60), "新竹市": (272, 97),
    "新竹縣": (300, 120), "苗栗縣": (250, 140), "臺中市": (240, 185), "彰化縣": (200, 230), "南投縣": (280, 250),
    "雲林縣": (190, 270), "嘉義市": (206, 306), "嘉義縣": (240, 320), "臺南市": (180, 360), "高雄市": (250, 380),
    "屏東縣": (230, 460), "宜蘭縣": (400, 110), "花蓮縣": (350, 250), "臺東縣": (290, 420),
    # 離島在圖上是透明的輪廓，沒亮燈時取到的是透明像素（算正常），亮燈時會是有顏色的像素
    "澎湖縣": (65, 333), "金門縣": (85, 178), "連江縣": (32, 82),
}


def county_lights(img):
    """每個縣市取種子點周圍 5×5 裡最常見的燈號。"""
    px = png_pixels(img)
    if not px or (px[0], px[1]) != MAP_SIZE:
        return None
    _, _, rows = px
    out = {}
    for name, (x, y) in COUNTY_SEEDS.items():
        votes = {}
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                row = rows[y + dy]
                r, g, b, a = row[(x + dx) * 4:(x + dx) * 4 + 4]
                if a >= 128 and min(r, g, b) < 100 and max(r, g, b) - min(r, g, b) < 40:
                    continue  # 縣市界線
                k = light_of(r, g, b, a)
                votes[k] = votes.get(k, 0) + 1
        out[name] = max(votes, key=votes.get) if votes else None
    return out


def update_alert(data_dir):
    """水利署官網的水情燈號：官方只公布一張全台燈號圖和發布日期，沒有結構化資料。
    抓圖片網址和日期存到 alert.json，並試著把圖片存到本機（失敗就讓網頁直接連官方圖）。"""
    page = fetch_text(ALERT_PAGE)
    m = re.search(r'src="([^"]*EarlyWarningMap_[^"]+)"', page)
    d = re.search(r"現行水情燈號發布日期.*?(\d{2,3})年(\d{1,2})月(\d{1,2})日", page, re.S)
    if not m:
        raise ValueError("官網找不到燈號圖")
    image_url = m.group(1).replace("&amp;", "&")
    published = None
    if d:
        y, mo, da = (int(x) for x in d.groups())
        published = f"{y + 1911:04d}-{mo:02d}-{da:02d}"
    local, counties = None, None
    try:
        req = urllib.request.Request(image_url, headers={"User-Agent": "reservoir-site/0.1"})
        with urllib.request.urlopen(req, timeout=60, context=ssl_context()) as r:
            img = r.read()
        try:
            counties = county_lights(img)
        except Exception:  # noqa: BLE001
            counties = None
        with open(os.path.join(data_dir, "alert-map.png"), "wb") as f:
            f.write(img)
        local = "data/alert-map.png"
    except Exception as e:  # noqa: BLE001
        print(f"燈號圖下載失敗，改用官方網址：{e}", file=sys.stderr)
    # counties：本島各縣市燈號 N/G/Y/O/R；any_alert：本島有沒有任何縣市亮燈（None＝無法判讀）
    any_alert = None if counties is None else any(v not in ("N", None) for v in counties.values())
    doc = {"published": published, "image_url": image_url, "local_image": local,
           "any_alert": any_alert, "counties": counties, "source_url": ALERT_PAGE}
    with open(os.path.join(data_dir, "alert.json"), "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    return doc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-dir", help="讀本機的 daily.json / hourly.json，不上網")
    ap.add_argument("--save-raw", help="把抓到的原始資料另存到這個資料夾")
    ap.add_argument("--data-dir", default=os.path.join(os.path.dirname(__file__), "..", "data"))
    a = ap.parse_args()

    if a.raw_dir:
        with open(os.path.join(a.raw_dir, "daily.json"), encoding="utf-8-sig") as f:
            daily = json.load(f)
        with open(os.path.join(a.raw_dir, "hourly.json"), encoding="utf-8-sig") as f:
            hourly = json.load(f)
    else:
        daily, hourly = fetch_json(DAILY_URL), fetch_json(HOURLY_URL)
        if a.save_raw:
            os.makedirs(a.save_raw, exist_ok=True)
            for n, p in (("daily", daily), ("hourly", hourly)):
                with open(os.path.join(a.save_raw, f"{n}.json"), "w", encoding="utf-8") as f:
                    json.dump(p, f, ensure_ascii=False)

    data_dir = os.path.abspath(a.data_dir)
    res = build(as_rows(daily), as_rows(hourly), load_info(data_dir))
    if not res:
        sys.exit("沒有抓到任何水庫資料")
    write_outputs(res, data_dir, datetime.now(TW))
    if not a.raw_dir:
        try:
            alert = update_alert(data_dir)
            print(f"水情燈號發布日期 {alert['published']}")
        except Exception as e:  # noqa: BLE001
            print(f"水情燈號更新失敗：{e}", file=sys.stderr)
    ok = sum(1 for r in res if r["percent"] is not None)
    print(f"{len(res)} 座水庫，{ok} 座有蓄水率")


if __name__ == "__main__":
    main()
