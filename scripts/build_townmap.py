#!/usr/bin/env python3
"""把 taiwan-atlas 的鄉鎮市區 TopoJSON 轉成所得頁用的 SVG 路徑（data/income/town-map.json）。

只在要更新底圖時手動執行一次（GitHub Actions 或能連 npm 的電腦）：
    npm pack taiwan-atlas && tar xzf taiwan-atlas-*.tgz
    python3 scripts/build_townmap.py package/towns-10t.json

投影、範圍和縣市地圖（scripts/build_map.py）一樣；離島（澎湖、金門、馬祖）在範圍外，不畫。
"""
import json
import sys
from pathlib import Path

import build_map as bm

TOL = 0.5


def main(src):
    topo = json.loads(Path(src).read_text(encoding="utf-8"))
    arcs = bm.decode_arcs(topo)
    towns = {}
    for g in topo["objects"]["towns"]["geometries"]:
        p = g["properties"]
        name = (p["COUNTYNAME"] + p["TOWNNAME"]).replace("台", "臺")
        polys = g["arcs"] if g["type"] == "MultiPolygon" else [g["arcs"]]
        d = []
        for poly in polys:
            for k, r in enumerate(poly):
                pts = bm.ring(arcs, r)
                lons = [q[0] for q in pts]
                lats = [q[1] for q in pts]
                if max(lons) < bm.LON0 or min(lons) > bm.LON1 or max(lats) < bm.LAT1 or min(lats) > bm.LAT0:
                    if k == 0:
                        break
                    continue
                xy = bm.simplify([bm.project(*q) for q in pts], TOL)
                if len(xy) < 4:
                    continue
                d.append("M" + "L".join("%.1f,%.1f" % q for q in xy) + "Z")
        towns[name] = {"en": p["TOWNENG"], "county_en": p["COUNTYENG"], "code": p["TOWNCODE"], "d": "".join(d)}
    out = {"source": "taiwan-atlas (MIT) / 內政部鄉鎮市區界", "width": bm.WIDTH, "height": bm.HEIGHT, "towns": towns}
    dest = Path(__file__).resolve().parent.parent / "data/income/town-map.json"
    dest.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(dest, len(towns), "towns", dest.stat().st_size, "bytes")


if __name__ == "__main__":
    main(sys.argv[1])
