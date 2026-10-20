#!/usr/bin/env python3
"""把 scripts/i18n_ja.py 的日文對照表輸出成 docs/ja-glossary.md，給懂日文的人檢查。

    python3 scripts/ja_glossary.py
"""
from pathlib import Path

import i18n_en
import i18n_ja

ROOT = Path(__file__).resolve().parent.parent


def table(head, rows):
    out = "| " + " | ".join(head) + " |\n|" + "---|" * len(head) + "\n"
    return out + "".join("| " + " | ".join(str(c) for c in r) + " |\n" for r in rows)


def main():
    import json
    names = {r["id"]: r.get("name") for r in json.loads((ROOT / "data/latest.json").read_text(encoding="utf-8"))["reservoirs"]}
    md = ["# 日文版用詞對照表\n\n",
          "由 `scripts/i18n_ja.py` 自動產生（`python3 scripts/ja_glossary.py`）。狀態：**已核對**＝查到日文出處實際這樣寫；"
          "**常用寫法**＝日本官方或媒體的通用寫法，出處連結還沒逐一打開核對；**待確認**＝沒有現成寫法，請母語者確認。"
          "名稱表（水庫、航點、航空公司等）都還沒經母語者檢查。\n\n",
          "## 專業用詞與機關名\n\n", table(["中文", "日文", "狀態", "出處"], i18n_ja.GLOSSARY),
          "\n## 水庫\n\n", table(["代碼", "中文", "日文", "英文"],
                              [(k, names.get(k, ""), v, i18n_en.RESERVOIRS.get(k, "")) for k, v in i18n_ja.RESERVOIRS.items()]),
          "\n## 縣市\n\n", table(["中文", "日文"], i18n_ja.COUNTIES.items()),
          "\n## 水情燈號\n\n", table(["燈號", "日文名", "短稱", "說明", "地圖圖例"],
                                [(k, *v, i18n_ja.LEGEND[k]) for k, v in i18n_ja.LIGHTS.items()]),
          "\n## 水庫用途、壩型\n\n", table(["中文", "日文"], list(i18n_ja.PURPOSES.items()) + list(i18n_ja.DAM_TYPES.items())),
          "\n## 航點\n\n", table(["中文", "日文", "英文"], [(k, v, i18n_en.DESTS.get(k, "")) for k, v in i18n_ja.DESTS.items()]),
          "\n## 航空公司\n\n", table(["中文", "日文", "英文"], [(k, v, i18n_en.AIRLINES.get(k, "")) for k, v in i18n_ja.AIRLINES.items()]),
          "\n## 機場\n\n", table(["代碼", "日文"], i18n_ja.AIRPORTS.items()),
          "\n## 國家／地區、來台目的、入境地點\n\n",
          table(["中文", "日文"], list(i18n_ja.PLACES.items()) + list(i18n_ja.PURPOSE.items()) + list(i18n_ja.PORT.items()))]
    (ROOT / "docs").mkdir(exist_ok=True)
    (ROOT / "docs/ja-glossary.md").write_text("".join(md), encoding="utf-8")
    print("docs/ja-glossary.md")


if __name__ == "__main__":
    main()
