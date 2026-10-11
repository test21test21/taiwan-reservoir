#!/usr/bin/env python3
"""把 taiwan-atlas 的縣市 TopoJSON 轉成網站用的本島縣市 SVG 路徑（reservoir/taiwan-map.json）。

只在要更新底圖時手動執行一次：
    npm pack taiwan-atlas && tar xzf taiwan-atlas-*.tgz
    python3 scripts/build_map.py package/counties-10t.json

資料來源：taiwan-atlas（MIT），源自內政部「村里界圖(TWD97經緯度)」。
投影：等距圓柱，經度乘上 cos(23.7°)，和 reservoir/index.html 的 project() 一致。
"""
import json
import math
import sys
from pathlib import Path

LON0, LAT0 = 120.0, 25.35          # 左上角
LON1, LAT1 = 122.05, 21.85         # 右下角（本島＋綠島、蘭嶼、龜山島）
WIDTH = 720                        # 輸出寬度（SVG 單位）
K = math.cos(math.radians(23.7))
S = WIDTH / ((LON1 - LON0) * K)
HEIGHT = round((LAT0 - LAT1) * S)
TOL = 0.7                          # 簡化容許誤差（SVG 單位）


def project(lon, lat):
    return ((lon - LON0) * K * S, (LAT0 - lat) * S)


def decode_arcs(topo):
    sx, sy = topo["transform"]["scale"]
    tx, ty = topo["transform"]["translate"]
    out = []
    for arc in topo["arcs"]:
        x = y = 0
        pts = []
        for dx, dy in arc:
            x += dx
            y += dy
            pts.append((x * sx + tx, y * sy + ty))
        out.append(pts)
    return out


def ring(arcs, idxs):
    pts = []
    for i in idxs:
        a = arcs[i] if i >= 0 else arcs[~i][::-1]
        pts.extend(a if not pts else a[1:])
    return pts


def simplify(pts, tol):
    """Douglas–Peucker。封閉環先從離起點最遠的點切成兩段再各自簡化。"""
    if len(pts) > 4 and pts[0] == pts[-1]:
        x0, y0 = pts[0]
        m = max(range(len(pts)), key=lambda i: (pts[i][0] - x0) ** 2 + (pts[i][1] - y0) ** 2)
        return _dp(pts[:m + 1], tol) + _dp(pts[m:], tol)[1:]
    return _dp(pts, tol)


def _dp(pts, tol):
    if len(pts) < 4:
        return pts
    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        a, b = stack.pop()
        (x1, y1), (x2, y2) = pts[a], pts[b]
        dx, dy = x2 - x1, y2 - y1
        L = math.hypot(dx, dy) or 1e-9
        best, bi = 0, -1
        for i in range(a + 1, b):
            x0, y0 = pts[i]
            d = abs(dy * x0 - dx * y0 + x2 * y1 - y2 * x1) / L
            if d > best:
                best, bi = d, i
        if best > tol:
            keep[bi] = True
            stack += [(a, bi), (bi, b)]
    return [p for p, k in zip(pts, keep) if k]


def main(src):
    topo = json.loads(Path(src).read_text(encoding="utf-8"))
    arcs = decode_arcs(topo)
    counties = {}
    for g in topo["objects"]["counties"]["geometries"]:
        name = g["properties"]["COUNTYNAME"].replace("台", "臺")
        polys = g["arcs"] if g["type"] == "MultiPolygon" else [g["arcs"]]
        d = []
        for poly in polys:
            for k, r in enumerate(poly):
                pts = ring(arcs, r)
                lons = [p[0] for p in pts]
                lats = [p[1] for p in pts]
                if max(lons) < LON0 or min(lons) > LON1 or max(lats) < LAT1 or min(lats) > LAT0:
                    if k == 0:
                        break          # 整塊在範圍外（離島、東沙等）
                    continue
                xy = simplify([project(*p) for p in pts], TOL)
                if len(xy) < 4:
                    continue
                d.append("M" + "L".join("%.1f,%.1f" % p for p in xy) + "Z")
        if d:
            counties[name] = "".join(d)
    out = {
        "source": "taiwan-atlas (MIT) / 內政部村里界圖",
        "lon0": LON0, "lat0": LAT0, "k": round(K, 6), "s": round(S, 4),
        "width": WIDTH, "height": HEIGHT, "counties": counties,
    }
    dest = Path(__file__).resolve().parent.parent / "reservoir" / "taiwan-map.json"
    dest.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(dest, len(counties), "counties", dest.stat().st_size, "bytes", "height", HEIGHT)


if __name__ == "__main__":
    main(sys.argv[1])
