#!/usr/bin/env python3
"""把 world-atlas 的國家 TopoJSON 轉成航班頁、旅客人次頁用的世界地圖 SVG 路徑（data/world-map.json）。

只在要更新底圖時手動執行一次：
    npm pack world-atlas@2.0.2 && tar xzf world-atlas-*.tgz
    python3 scripts/build_world.py package/countries-50m.json

資料來源：world-atlas（ISC 授權，Mike Bostock），源自 Natural Earth（公眾領域）。
投影：等距圓柱，以太平洋為中心（左邊界東經 -30°，美洲在右、歐洲在左），
經度乘上 K，讓亞洲的形狀不會被壓扁。JS 端用同一組參數算座標（見 build_flights.world_svg）。
"""
import json
import sys
from pathlib import Path

from build_map import decode_arcs, ring, simplify

LON0, LAT0 = -30.0, 75.0           # 左上角
LAT1 = -50.0                       # 下緣（不畫南極洲）
K = 0.9
WIDTH = 1000                       # 輸出寬度（SVG 單位）
S = WIDTH / (360 * K)
HEIGHT = round((LAT0 - LAT1) * S)
TOL = 0.2                          # 簡化容許誤差（SVG 單位）
SKIP = {"010"}                     # 南極洲


def project(lon, lat):
    return ((lon - LON0) * K * S, (LAT0 - lat) * S)


def unwrap(pts):
    """把經度接成連續（不會在 ±180 跳一圈），起點落在 [LON0, LON0+360)。"""
    out = []
    for lon, lat in pts:
        if not out:
            lon = (lon - LON0) % 360 + LON0
        else:
            prev = out[-1][0]
            while lon - prev > 180:
                lon -= 360
            while lon - prev < -180:
                lon += 360
        out.append((lon, lat))
    return out


def path(xy):
    """相對座標的 SVG 路徑，比較省字。"""
    pts = [(round(x * 10), round(y * 10)) for x, y in xy]
    d = ["M%s,%s" % (pts[0][0] / 10, pts[0][1] / 10)]
    rel = []
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if (x1, y1) != (x0, y0):
            rel.append("%s,%s" % (_n((x1 - x0) / 10), _n((y1 - y0) / 10)))
    return d[0] + "l" + " ".join(rel) + "z"


def _n(v):
    s = ("%.1f" % v).rstrip("0").rstrip(".")
    return s.replace("0.", ".", 1) if s.startswith(("0.", "-0.")) else s


def main(src):
    topo = json.loads(Path(src).read_text(encoding="utf-8"))
    arcs = decode_arcs(topo)
    countries = {}
    for g in topo["objects"]["countries"]["geometries"]:
        cid = str(g.get("id", ""))
        if cid in SKIP or g.get("type") not in ("Polygon", "MultiPolygon"):
            continue
        polys = g["arcs"] if g["type"] == "MultiPolygon" else [g["arcs"]]
        d = []
        for poly in polys:
            for r in poly:
                pts = unwrap(ring(arcs, r))
                lons = [p[0] for p in pts]
                shifts = [0]
                if min(lons) < LON0:
                    shifts.append(360)
                if max(lons) > LON0 + 360:
                    shifts.append(-360)
                for sh in shifts:
                    xy = simplify([project(lon + sh, lat) for lon, lat in pts], TOL)
                    if len(xy) < 4:
                        continue
                    xs = [p[0] for p in xy]
                    if max(xs) < 0 or min(xs) > WIDTH:
                        continue
                    d.append(path(xy))
        if d:
            countries[cid or g["properties"]["name"]] = "".join(d)
    out = {
        "source": "world-atlas 2.0.2 (ISC, Mike Bostock) / Natural Earth",
        "lon0": LON0, "lat0": LAT0, "k": K, "s": round(S, 6),
        "width": WIDTH, "height": HEIGHT, "countries": countries,
    }
    dest = Path(__file__).resolve().parent.parent / "data" / "world-map.json"
    dest.write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
    print(dest, len(countries), "countries", dest.stat().st_size, "bytes", "height", HEIGHT)


if __name__ == "__main__":
    main(sys.argv[1])
