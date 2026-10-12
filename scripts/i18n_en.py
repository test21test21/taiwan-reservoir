"""英文版用的名稱對照：水庫、地區、縣市、水情燈號、用途、壩型。

水庫英文名大多照維基百科／水利署的常見寫法，其他用漢語拼音。
這裡沒列到的水庫，英文頁就退回顯示中文名。
"""

RESERVOIRS = {
    "10201": "Shihmen Reservoir", "10203": "Xishi Reservoir", "10204": "Xinshan Reservoir",
    "10205": "Feitsui Reservoir", "10206": "Ronghua Dam", "10211": "Qingtan Weir", "10212": "Zhitan Dam",
    "10401": "Baoshan Reservoir", "10405": "Baoshan Second Reservoir", "10501": "Yongheshan Reservoir",
    "10503": "Dapu Reservoir", "10601": "Mingde Reservoir", "10802": "Luodong Weir",
    "20101": "Liyutan Reservoir", "20201": "Deji Reservoir", "20202": "Shigang Dam", "20405": "Shilin Weir",
    "20501": "Wushe Reservoir", "20502": "Sun Moon Lake Reservoir", "20503": "Jiji Weir", "20507": "Wujie Dam",
    "20508": "Minghu Lower Reservoir", "20509": "Hushan Reservoir",
    "30301": "Renyitan Reservoir", "30302": "Lantan Reservoir", "30306": "Neipuzi Reservoir",
    "30401": "Baihe Reservoir", "30403": "Deyuanpi Reservoir", "30501": "Wushantou Reservoir",
    "30502": "Zengwen Reservoir", "30503": "Nanhua Reservoir", "30504": "Jingmian Reservoir",
    "30601": "Hutoupi Reservoir", "30602": "Yanshuipi Reservoir", "30802": "Agongdian Reservoir",
    "30803": "Fengshan Reservoir", "31002": "Jiaxian Weir", "31201": "Mudan Reservoir",
    "31301": "Chenggong Reservoir",
    "50102": "Xingren Reservoir", "50103": "Dongwei Reservoir", "50104": "Chikan Underground Reservoir",
    "50105": "Xi'an Reservoir", "50106": "Qimei Reservoir", "50108": "Xiaochi Reservoir", "50109": "Wugou Pond",
    "50201": "Taihu Reservoir", "50202": "Tianpu Reservoir", "50203": "Yangminghu Reservoir",
    "50204": "Shanxi Reservoir", "50205": "Ronghu Reservoir", "50206": "Qingtian Reservoir",
    "50207": "Jinsha Reservoir", "50208": "Lianhu Reservoir", "50209": "Linghu Reservoir",
    "50210": "Xihu Reservoir", "50212": "Jinhu Reservoir", "50213": "Qionglin Reservoir", "50214": "Lanhu Reservoir",
    "50301": "Shengli Reservoir", "50302": "Qiuguishan Reservoir", "50303": "Zhuluo Dam",
    "50304": "Chushuiwo Upper Dam", "50305": "Chushuiwo Reservoir", "50306": "Jinsha Reservoir (Matsu)",
    "50307": "Jinsha No. 1 Reservoir", "50308": "Banli Reservoir", "50309": "Dongyong Reservoir",
    "50310": "Houwo Reservoir",
}

REGIONS = {
    "全部": "All", "北部": "North", "中部": "Central", "南部": "South", "東部": "East",
    "離島": "Islands", "澎湖": "Penghu", "金門": "Kinmen", "馬祖": "Matsu",
}

COUNTIES = {
    "基隆市": "Keelung", "臺北市": "Taipei", "新北市": "New Taipei", "桃園市": "Taoyuan",
    "新竹市": "Hsinchu City", "新竹縣": "Hsinchu County", "苗栗縣": "Miaoli", "臺中市": "Taichung",
    "彰化縣": "Changhua", "南投縣": "Nantou", "雲林縣": "Yunlin", "嘉義市": "Chiayi City",
    "嘉義縣": "Chiayi County", "臺南市": "Tainan", "高雄市": "Kaohsiung", "屏東縣": "Pingtung",
    "宜蘭縣": "Yilan", "花蓮縣": "Hualien", "臺東縣": "Taitung", "澎湖縣": "Penghu",
    "金門縣": "Kinmen", "連江縣": "Lienchiang (Matsu)",
}

# 官方水情燈號：(燈名, 短稱, 說明)
LIGHTS = {
    "N": ("Blue", "Normal", "Normal water supply"),
    "G": ("Green", "Advisory", "Advisory: tighter water allocation"),
    "Y": ("Yellow", "Low pressure", "Reduced pressure at off-peak hours"),
    "O": ("Orange", "Cutbacks", "Reduced supply to large users, pools, car washes"),
    "R": ("Red", "Rationing", "Rotating supply cuts by district, or fixed-point supply"),
}

PURPOSES = {
    "公共給水": "Public water supply", "灌溉": "Irrigation", "觀光": "Tourism", "發電": "Hydropower",
    "防洪": "Flood control", "工業用水": "Industrial water",
}

DAM_TYPES = {
    "土石壩": "Earth and rockfill", "滾壓式土石壩": "Rolled earth and rockfill", "滾壓土石壩": "Rolled earth and rockfill",
    "土壩": "Earthfill", "滾壓式土壩": "Rolled earthfill", "中央心層分土壩": "Zoned earthfill (central core)",
    "混凝土心牆土壩": "Earthfill with concrete core", "混凝土重力壩": "Concrete gravity",
    "混凝土拱壩": "Concrete arch", "混凝土双曲線拱壩": "Concrete double-curvature arch",
    "拱形重力式混凝土壩": "Concrete arch-gravity", "混凝土堰": "Concrete weir",
    "混凝土壩及堆石壩": "Concrete and rockfill",
}


def name(rid, zh):
    return RESERVOIRS.get(str(rid), zh)


def purposes(zh):
    return ", ".join(PURPOSES.get(p.strip(), p.strip()) for p in str(zh or "").replace(",", "、").split("、") if p.strip())

# 水庫總覽頁（reservoir/index.html）JavaScript 裡的介面文字
TXT = {
    "無資料": "No data", "各區水情": "By region", "燈號資料暫時讀不到": "Alert lights unavailable",
    "這區沒有水庫資料": "No reservoir data here", "燈號看官網": "See WRA website", "亮燈：": "Alerts: ",
    "水情燈號": "Alert light", "水庫蓄水率": "Storage", "比昨天": "vs yesterday",
    "資料異常": "Data error", "無蓄水率": "No storage %", "偏低": "Low",
    "官方數字疑似有誤": "Official figure looks wrong", "觀測 ": "Observed ", "日報 ": "Daily report ",
    "資料更新 ": "Updated ", "目前讀不到水庫資料，請稍後再重新整理。": "Can't load reservoir data right now. Please refresh in a moment.",
}

# 水庫總覽頁的靜態 HTML：(中文, 英文)，build_pages.py 產生 /en/reservoir/ 時逐一替換
OVERVIEW_HTML = [
    ("<title>台灣水庫水情：即時蓄水率與水情燈號｜Taiwan Data</title>",
     "<title>Taiwan Reservoir Levels: Live Storage and Water Alerts | Taiwan Data</title>"),
    ('content="台灣各水庫即時蓄水率、有效蓄水量與官方水情燈號，北中南東一張地圖看懂，每小時更新，資料來自經濟部水利署。"',
     'content="Live storage levels for every reservoir in Taiwan, with the official water supply alert lights, on one map. Updated hourly from Water Resources Agency open data."'),
    ('<link rel="canonical" href="https://taiwandata.info/reservoir/">', '<link rel="canonical" href="https://taiwandata.info/en/reservoir/">'),
    ('<meta property="og:locale" content="zh_TW">', '<meta property="og:locale" content="en_US">'),
    ('content="台灣水庫水情：即時蓄水率與水情燈號｜Taiwan Data"', 'content="Taiwan Reservoir Levels: Live Storage and Water Alerts | Taiwan Data"'),
    ('content="https://taiwandata.info/reservoir/"', 'content="https://taiwandata.info/en/reservoir/"'),
    ('aria-label="水情燈號地圖"', 'aria-label="Water alert map"'),
    ("<h2>水庫蓄水與官方水情燈號</h2>", "<h2>Reservoir storage and official water alerts</h2>"),
    ('aria-label="各縣市官方水情燈號與水庫蓄水率地圖"', 'aria-label="Map of official water alert lights by county and reservoir storage levels"'),
    ("圓圈是水庫，圓圈面積＝水庫有效容量；縣市底色是水利署公告的水情燈號。點圓圈可看該水庫。",
     "Each circle is a reservoir; its area shows effective capacity. County colours are the official alert lights from the Water Resources Agency. Tap a circle to see that reservoir."),
    ("<summary>各燈號代表什麼？</summary>", "<summary>What do the lights mean?</summary>"),
    ('aria-label="各區水情"', 'aria-label="By region"'),
    ('aria-label="廣告"><b>廣告</b>廣告位置 1（300×250）', 'aria-label="Advertisement"><b>AD</b>'),
    ('aria-label="水庫列表"', 'aria-label="Reservoir list"'),
    ("<h2>所有水庫</h2>", "<h2>All reservoirs</h2>"),
    ('aria-label="地區"', 'aria-label="Region"'),
    ('aria-label="排序">排序', 'aria-label="Sort">Sort'),
    ('aria-pressed="true">容量大到小</button>', 'aria-pressed="true">Largest first</button>'),
    ('aria-pressed="false">蓄水率低到高</button>', 'aria-pressed="false">Lowest % first</button>'),
    ('aria-label="各水庫頁面"', 'aria-label="Reservoir pages"'),
    ("<h2>各水庫頁面</h2>", "<h2>Reservoir pages</h2>"),
    ("讀取資料中…", "Loading…"),
    ("<div>資料來源：經濟部水利署開放資料（水庫水情資料、水庫每日營運狀況、水庫基本資料）與水利署官網水情燈號，每小時更新；縣市界線取自內政部村里界圖（經 taiwan-atlas 整理）。蓄水率＝有效蓄水量 ÷ 有效容量，1 萬立方公尺約等於 1 萬噸水。</div>",
     "<div>Source: Water Resources Agency (WRA), Ministry of Economic Affairs, open data (hourly reservoir conditions, daily operations, reservoir facts) and the alert lights published on the WRA website; updated hourly. County borders from the Ministry of the Interior (via taiwan-atlas). Storage % = effective storage ÷ effective capacity.</div>"),
    ('<div>水情燈號以 <a id="src-link" href="https://www.wra.gov.tw/EarlyWarning.aspx?n=18804&amp;sms=9114" target="_blank" rel="noopener">經濟部水利署公告</a> 為準。水庫圓點的藍色深淺只代表蓄水率，和燈號無關。</div>',
     '<div>The <a id="src-link" href="https://www.wra.gov.tw/EarlyWarning.aspx?n=18804&amp;sms=9114" target="_blank" rel="noopener">WRA announcement</a> is the official word on alert lights. The blue shades of the reservoir circles show storage only and are not alert lights.</div>'),
    ('<div>本站為個人經營，非政府網站；所有數據皆來自政府開放資料。<a href="../about/">關於本站</a></div>',
     '<div>An independent site, not affiliated with the government. All figures come from government open data. <a href="/about/" lang="zh-Hant">About (Chinese)</a></div>'),
]
