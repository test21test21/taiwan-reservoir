"""全站共用：瀏覽器分頁小圖示、固定在最上方的列表按鈕＋網站名稱。

build_pages.py 會把 index.html、reservoir/index.html 裡的 <!--SITE_ICONS-->、<!--SITE_NAV--> 換成這裡的內容，
每座水庫頁也用同一份。
"""

ICONS = """<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32.png">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">"""

# 選單項目：(代號, 名稱, 網址)；網址空白代表即將推出
MENU = [
    ("home", "首頁", "/"),
    ("reservoir", "台灣水庫水情", "/reservoir/"),
    ("power", "台灣今日電力", "/power/"),
    ("births", "台灣出生與死亡", "/births/"),
    ("flights", "台灣航班", "/flights/"),
    ("travel", "台灣旅客人次", "/tourism/"),
    ("about", "關於本站", "/about/"),
]
# 英文版選單：(代號, 名稱, 英文網址)；英文網址空白就連到中文頁、旁邊標「中文」
MENU_EN = {
    "home": ("Home", "/en/"),
    "reservoir": ("Taiwan Reservoirs", "/en/reservoir/"),
    "power": ("Taiwan Power", "/en/power/"),
    "births": ("Taiwan Births &amp; Deaths", "/en/births/"),
    "flights": ("Taiwan Flights", "/en/flights/"),
    "travel": ("Taiwan Tourism", "/en/tourism/"),
    "about": ("About", "/en/about/"),
}

CSS = """
body { margin: 0; }
.sitebar { position: sticky; top: 0; z-index: 50; background: var(--surface); border-bottom: 1px solid var(--line); }
.sitebar-in { max-width: 1840px; margin: 0 auto; height: 52px; display: flex; align-items: center; gap: 6px; padding-inline: max(8px, env(safe-area-inset-left)) max(16px, env(safe-area-inset-right)); }
.menu-btn { width: 44px; height: 44px; display: grid; place-items: center; border: 0; border-radius: 10px; background: none; color: var(--fg); cursor: pointer; flex: none; }
.menu-btn:hover { background: var(--chip); }
.menu-btn svg { width: 24px; height: 24px; }
.sitename { display: flex; align-items: center; gap: 8px; color: var(--fg); text-decoration: none; white-space: nowrap; min-width: 0; flex: none; }
.sitename img { width: 28px; height: 28px; flex: none; }
.sitename b { display: block; font-weight: 700; font-size: 17px; line-height: 1.15; letter-spacing: .02em; }
.sitename small { display: block; text-align: center; font-size: 11px; line-height: 1.2; color: var(--muted); letter-spacing: .04em; }
.sitesection { margin: 0 0 0 4px; padding-left: 12px; border-left: 1.5px solid var(--line-strong, #c9ccd0); font-size: 17px; font-weight: 700; line-height: 30px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; min-width: 0; color: var(--fg); text-decoration: none; }
a.sitesection:hover { text-decoration: underline; }
.langsw-wrap { margin-left: auto; flex: none; position: relative; }
.langsw { display: inline-flex; align-items: center; gap: 4px; padding: 5px 9px; border: 1px solid var(--line); border-radius: 999px; background: none; font: inherit; font-size: 13px; font-weight: 500; line-height: 1; color: var(--fg); white-space: nowrap; cursor: pointer; }
.langsw svg { width: 15px; height: 15px; fill: none; stroke: currentColor; stroke-width: 1.6; }
.langsw:hover { background: var(--chip); }
@media (max-width: 480px) { .sitesection { white-space: normal; font-size: 14px; line-height: 1.2; display: -webkit-box; -webkit-box-orient: vertical; -webkit-line-clamp: 2; } .sn-loc { display: none; } .langsw { padding: 6px; } .langsw span { display: none; } .langsw svg { width: 18px; height: 18px; } }
.langmenu { position: absolute; right: 0; top: calc(100% + 6px); list-style: none; margin: 0; padding: 6px; min-width: 132px; background: var(--surface); border: 1px solid var(--line); border-radius: 12px; box-shadow: 0 8px 24px rgba(12,30,46,.14); z-index: 60; }
.langmenu a { display: block; padding: 8px 12px; border-radius: 8px; color: var(--fg); text-decoration: none; font-size: 15px; }
.langmenu a:hover { background: var(--chip); }
.langmenu a[aria-current] { font-weight: 700; background: var(--chip); }
@media (max-width: 420px) { .sitename b, .sitesection { font-size: 15px; } .sitename small { font-size: 10px; } .sitename img { width: 24px; height: 24px; } .sitebar-in { gap: 4px; } .sitesection { padding-left: 10px; } }
@media (max-width: 380px) { .sitename b, .sitesection { font-size: 14px; } .menu-btn { width: 38px; } .sitename img { width: 22px; height: 22px; } .sitename { gap: 6px; } .sitesection { padding-left: 8px; } }
.sitemenu { position: absolute; top: 100%; left: 0; width: min(300px, 100vw); max-height: calc(100vh - 52px); overflow: auto; background: var(--surface); border: 1px solid var(--line); border-top: 0; border-radius: 0 0 14px 0; box-shadow: 0 8px 24px rgba(12,30,46,.14); padding: 8px; }
.sitemenu ul { list-style: none; margin: 0; padding: 0; display: grid; gap: 2px; }
.sitemenu a, .sitemenu span { display: flex; justify-content: space-between; align-items: center; padding: 10px 12px; border-radius: 10px; color: var(--fg); text-decoration: none; font-size: 16px; }
.sitemenu a:hover { background: var(--chip); }
.sitemenu a[aria-current="page"] { background: var(--chip); font-weight: 700; }
.sitemenu span { color: var(--muted); }
.sitemenu small { font-size: 12px; color: var(--muted); }
"""

# 語言：(代號, 網址開頭, 顯示名稱, hreflang)
# 網址資料夾：日文用國碼 jp（Shane 2026-10-17），語言代號（html lang、hreflang）仍是標準的 ja
DIR = {"zh": "", "en": "en", "ja": "jp"}
LANGS = [("zh", "", "中文", "zh-Hant"), ("en", "/en", "English", "en"), ("ja", "/jp", "日本語", "ja")]
CUR = ' aria-current="true"'
SHORT = {"zh": "中文", "en": "EN", "ja": "日本語"}
UI = {  # 選單按鈕、語言按鈕的說明文字
    "zh": ("開啟選單", "關閉選單", "網站選單", "即將推出", "語言", "Taiwan Data 台灣數據", "/"),
    "en": ("Open menu", "Close menu", "Site menu", "Coming soon", "Language", "Taiwan Data", "/en/"),
    "ja": ("メニューを開く", "メニューを閉じる", "サイトメニュー", "近日公開", "言語", 'Taiwan Data<span class="sn-loc"> 台湾データ</span>', "/jp/"),
}


def js(lang="zh"):
    ui = UI[lang]
    return JS.replace("關閉選單", ui[1]).replace("開啟選單", ui[0])


JS = """<script>
(function () {
  var b = document.getElementById("menu-btn"), m = document.getElementById("sitemenu");
  function set(open) { m.hidden = !open; b.setAttribute("aria-expanded", open); b.setAttribute("aria-label", open ? "關閉選單" : "開啟選單"); }
  b.addEventListener("click", function (ev) { ev.stopPropagation(); set(m.hidden); });
  document.addEventListener("click", function (ev) { if (!m.hidden && !m.contains(ev.target)) set(false); });
  document.addEventListener("keydown", function (ev) { if (ev.key === "Escape" && !m.hidden) { set(false); b.focus(); } });
  // 語言選單
  var lb = document.getElementById("lang-btn"), lm = document.getElementById("langmenu");
  if (!lb) return;
  function setL(open) { lm.hidden = !open; lb.setAttribute("aria-expanded", open); }
  lb.addEventListener("click", function (ev) { ev.stopPropagation(); setL(lm.hidden); });
  document.addEventListener("click", function (ev) { if (!lm.hidden && !lm.contains(ev.target)) setL(false); });
  document.addEventListener("keydown", function (ev) { if (ev.key === "Escape" && !lm.hidden) { setL(false); lb.focus(); } });
})();
</script>"""


def lang_url(lang, path):
    """path：中文版網址（/reservoir/10201/）→ 該語言的網址。"""
    pre = dict((k, p) for k, p, _, _ in LANGS)[lang]
    return pre + path


def nav(current, section="", lang="zh", path=""):
    """section：網站名稱右邊、豎線後面的頁面名稱（HTML，例如 <h1 class="sitesection">…</h1>）。
    lang："zh"、"en" 或 "ja"；path：這一頁的中文版網址（例如 /reservoir/），有的話頂欄右邊放語言選單。"""
    import i18n_ja
    ui = UI[lang]
    items = ""
    for key, name, url in MENU:
        cur = ' aria-current="page"' if key == current else ""
        if lang != "zh":
            name, url_l = (MENU_EN if lang == "en" else i18n_ja.MENU)[key]
            if url_l:
                url = url_l
            elif url:
                name += '<small>中文</small>'
        items += (f'<li><a href="{url}"{cur}>{name}</a></li>' if url
                  else f"<li><span>{name}<small>{ui[3]}</small></span></li>")
    switch = ""
    if path:
        opts = "".join(
            f'<li><a href="{lang_url(k, path)}" hreflang="{h}" lang="{h}"{CUR if k == lang else ""}>{label}</a></li>'
            for k, _, label, h in LANGS)
        switch = (f'<div class="langsw-wrap"><button type="button" class="langsw" id="lang-btn" aria-expanded="false" aria-controls="langmenu" aria-label="{ui[4]}">'
                  f'<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c2.5 2.6 3.8 5.6 3.8 9s-1.3 6.4-3.8 9c-2.5-2.6-3.8-5.6-3.8-9s1.3-6.4 3.8-9z"/></svg>'
                  f'<span>{SHORT[lang]}</span></button><ul class="langmenu" id="langmenu" hidden>{opts}</ul></div>')
    return f"""<style>{CSS}</style>
<header class="sitebar">
  <div class="sitebar-in">
    <button type="button" class="menu-btn" id="menu-btn" aria-expanded="false" aria-controls="sitemenu" aria-label="{ui[0]}">
      <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
    </button>
    <a class="sitename" href="{ui[6]}"><img src="/icon-192.png" alt="" width="28" height="28"><span><b>{ui[5]}</b><small>taiwandata.info</small></span></a>
    {section}{switch}
  </div>
  <nav class="sitemenu" id="sitemenu" aria-label="{ui[2]}" hidden><ul>{items}</ul></nav>
</header>
{js(lang)}"""
