#!/usr/bin/env python3
"""用 reservoir/taiwan-map.json 的縣市界線畫網站小圖示（藍底白色台灣），只在要改圖示時手動執行一次：
    python3 scripts/build_icons.py
先畫成 SVG，再用 Chromium 轉成 PNG 與 favicon.ico（網站左上角與瀏覽器分頁用）。
"""
import json
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BLUE = "#0a6cc2"

m = json.loads((ROOT / "reservoir/taiwan-map.json").read_text(encoding="utf-8"))
paths = list(m["counties"].values())
nums = [float(x) for p in paths for x in re.findall(r"-?\d+\.?\d*", p)]
xs, ys = nums[0::2], nums[1::2]
x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
# 台灣是直長形：放在正方形中間，上下留 10%
side = (y1 - y0) / 0.8
cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
vb = f"{cx - side / 2:.1f} {cy - side / 2:.1f} {side:.1f} {side:.1f}"
r = side * 0.22
d = "".join(paths)
svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}">'
       f'<rect x="{cx - side / 2:.1f}" y="{cy - side / 2:.1f}" width="{side:.1f}" height="{side:.1f}" rx="{r:.1f}" fill="{BLUE}"/>'
       f'<path d="{d}" fill="#fff" stroke="#fff" stroke-width="{side / 160:.1f}" stroke-linejoin="round"/></svg>')
tmp = Path(tempfile.mkdtemp()) / "icon.svg"
tmp.write_text(svg, encoding="utf-8")

js = r"""
const { chromium } = require('playwright');
(async () => {
  const fs = require('fs');
  const svg = fs.readFileSync(process.argv[1], 'utf8');
  const b = await chromium.launch();
  const p = await b.newPage();
  for (const [n, out] of [[32, 'favicon-32.png'], [48, 'favicon-48.png'], [180, 'apple-touch-icon.png'], [192, 'icon-192.png']]) {
    await p.setViewportSize({ width: n, height: n });
    await p.setContent(`<style>html,body{margin:0;background:transparent}svg{width:${n}px;height:${n}px;display:block}</style>` + svg);
    await p.screenshot({ path: process.argv[2] + '/' + out, omitBackground: true });
  }
  await b.close();
})();
"""
subprocess.run(["node", "-e", js, str(tmp), str(ROOT)], check=True)

from PIL import Image  # noqa: E402
Image.open(ROOT / "favicon-48.png").save(ROOT / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])
(ROOT / "favicon-48.png").unlink()
print("favicon.ico、favicon-32.png、apple-touch-icon.png、icon-192.png")
