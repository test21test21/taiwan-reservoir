#!/usr/bin/env python3
"""IndexNow：網站更新後主動通知搜尋引擎（Naver、Bing 等）有哪些頁面，不需要任何帳號。

- build_pages.py 呼叫 write_key()，在網站根目錄放驗證檔 /<KEY>.txt（IndexNow 規定公開，不是密碼）。
- 部署完成後，update.yml 執行：python3 scripts/indexnow.py _site/sitemap.xml
  讀網站地圖裡的全部網址，送到 Naver 與 IndexNow 共用入口。失敗只印訊息，不讓部署失敗。
"""
import json
import re
import sys
import urllib.request
from pathlib import Path

SITE = "https://taiwandata.info"
HOST = "taiwandata.info"
KEY = "582790584fa751b118eaa0140ee98550"
ENDPOINTS = [
    "https://searchadvisor.naver.com/indexnow",  # Naver
    "https://api.indexnow.org/indexnow",         # 共用入口（Bing、Yandex、Seznam 等會互相分享）
]


def write_key(out):
    (Path(out) / f"{KEY}.txt").write_text(KEY, encoding="utf-8")


def urls_from(sitemap):
    return re.findall(r"<loc>([^<]+)</loc>", Path(sitemap).read_text(encoding="utf-8"))


def submit(urls):
    body = json.dumps({"host": HOST, "key": KEY, "keyLocation": f"{SITE}/{KEY}.txt", "urlList": urls}).encode("utf-8")
    for ep in ENDPOINTS:
        req = urllib.request.Request(ep, data=body, method="POST", headers={"Content-Type": "application/json; charset=utf-8"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                print(f"{ep}: {r.status}（{len(urls)} 個網址）")
        except urllib.error.HTTPError as e:
            print(f"{ep}: HTTP {e.code} {e.read()[:200]!r}")
        except Exception as e:  # 網路問題不影響部署
            print(f"{ep}: {e}")


if __name__ == "__main__":
    urls = [u for u in urls_from(sys.argv[1] if len(sys.argv) > 1 else "_site/sitemap.xml") if u.startswith(SITE + "/")]
    submit(urls[:10000])
