#!/usr/bin/env python3
"""用 reservoir/taiwan-map.json 的縣市界線畫網站小圖示（透明背景、綠色台灣），只在要改圖示時手動執行一次：
    python3 scripts/build_icons.py
先畫成 SVG，再用 Chromium 轉成 PNG 與 favicon.ico（網站左上角與瀏覽器分頁用）。
"""
import json
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GREEN = "#1f9d55"

m = json.loads((ROOT / "reservoir/taiwan-map.json").read_text(encoding="utf-8"))
paths = list(m["counties"].values())
nums = [float(x) for p in paths for x in re.findall(r"-?\d+\.?\d*", p)]
xs, ys = nums[0::2], nums[1::2]
x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
# 台灣是直長形：放在正方形中間，上下只留一點點
side = (y1 - y0) / 0.96
cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
vb = f"{cx - side / 2:.1f} {cy - side / 2:.1f} {side:.1f} {side:.1f}"
d = "".join(paths)
svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}">'
       f'<path d="{d}" fill="{GREEN}" stroke="{GREEN}" stroke-width="{side / 160:.1f}" stroke-linejoin="round"/></svg>')
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
# iPhone 主畫面圖示不能透明（會變黑底）：白底、四周留白
t = Image.open(ROOT / "apple-touch-icon.png").convert("RGBA").resize((140, 140), Image.LANCZOS)
bg = Image.new("RGBA", (180, 180), "white")
bg.alpha_composite(t, (20, 20))
bg.convert("RGB").save(ROOT / "apple-touch-icon.png")
print("favicon.ico、favicon-32.png、apple-touch-icon.png、icon-192.png")
