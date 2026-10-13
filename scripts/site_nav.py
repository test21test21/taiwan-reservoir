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
    ("reservoir", "水庫水情", "/reservoir/"),
    ("births", "出生與死亡", "/births/"),
    ("flights", "機場航班", "/flights/"),
    ("travel", "旅遊統計", "/travel/"),
    ("about", "關於本站", "/about/"),
]
# 英文版選單：(代號, 名稱, 英文網址)；英文網址空白就連到中文頁、旁邊標「中文」
MENU_EN = {
    "home": ("Home", "/en/"),
    "reservoir": ("Reservoirs", "/en/reservoir/"),
    "births": ("Births &amp; deaths", "/en/births/"),
    "flights": ("Flights", "/en/flights/"),
    "travel": ("Travel", "/en/travel/"),
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
.langsw { margin-left: auto; flex: none; padding: 6px 10px; border: 1px solid var(--line); border-radius: 999px; font-size: 13px; font-weight: 500; line-height: 1; color: var(--fg); text-decoration: none; white-space: nowrap; }
.langsw:hover { background: var(--chip); }
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

def js(en=False):
    return JS.replace("關閉選單", "Close menu").replace("開啟選單", "Open menu") if en else JS


JS = """<script>
(function () {
  var b = document.getElementById("menu-btn"), m = document.getElementById("sitemenu");
  function set(open) { m.hidden = !open; b.setAttribute("aria-expanded", open); b.setAttribute("aria-label", open ? "關閉選單" : "開啟選單"); }
  b.addEventListener("click", function (ev) { ev.stopPropagation(); set(m.hidden); });
  document.addEventListener("click", function (ev) { if (!m.hidden && !m.contains(ev.target)) set(false); });
  document.addEventListener("keydown", function (ev) { if (ev.key === "Escape" && !m.hidden) { set(false); b.focus(); } });
})();
</script>"""


def nav(current, section="", lang="zh", alt=""):
    """section：網站名稱右邊、豎線後面的頁面名稱（HTML，例如 <h1 class="sitesection">…</h1>）。
    lang："zh" 或 "en"；alt：另一種語言的同一頁網址，有的話頂欄右邊放「EN／中文」切換。"""
    en = lang == "en"
    items = ""
    for key, name, url in MENU:
        cur = ' aria-current="page"' if key == current else ""
        if en:
            name, url_en = MENU_EN[key]
            if url_en:
                url = url_en
            elif url:
                name += '<small>中文</small>'
        items += (f'<li><a href="{url}"{cur}>{name}</a></li>' if url
                  else f"<li><span>{name}<small>{'Coming soon' if en else '即將推出'}</small></span></li>")
    switch = (f'<a class="langsw" href="{alt}" hreflang="{"zh-Hant" if en else "en"}" lang="{"zh-Hant" if en else "en"}">'
              f'{"中文" if en else "EN"}</a>') if alt else ""
    return f"""<style>{CSS}</style>
<header class="sitebar">
  <div class="sitebar-in">
    <button type="button" class="menu-btn" id="menu-btn" aria-expanded="false" aria-controls="sitemenu" aria-label="{'Open menu' if en else '開啟選單'}">
      <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
    </button>
    <a class="sitename" href="{'/en/' if en else '/'}"><img src="/icon-192.png" alt="" width="28" height="28"><span><b>{'Taiwan Data' if en else 'Taiwan Data 台灣數據'}</b><small>taiwandata.info</small></span></a>
    {section}{switch}
  </div>
  <nav class="sitemenu" id="sitemenu" aria-label="{'Site menu' if en else '網站選單'}" hidden><ul>{items}</ul></nav>
</header>
{js(en)}"""
