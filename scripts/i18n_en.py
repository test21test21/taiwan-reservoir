"""英文版用的名稱對照：水庫、地區、縣市、水情燈號、用途、壩型。

水庫英文名大多照維基百科／水利署的常見寫法，其他用漢語拼音。
這裡沒列到的水庫，英文頁就退回顯示中文名。
"""

RESERVOIRS = {
    "10201": "Shihmen Reservoir", "10203": "Xishi Reservoir", "10204": "Xinshan Reservoir",
    "10205": "Feitsui Reservoir", "10206": "Ronghua Dam", "10211": "Qingtan Weir", "10212": "Zhitan Dam",
    "10401": "Baoshan Reservoir", "10405": "Second Baoshan Reservoir", "10501": "Yongheshan Reservoir",
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
    ('<meta property="og:site_name" content="Taiwan Data 台灣數據">', '<meta property="og:site_name" content="Taiwan Data">'),
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
     '<div>An independent site, not affiliated with the government. All figures come from government open data. <a href="/en/about/">About</a></div>'),
]

# 首頁（index.html）的文字：(中文, 英文)
HOME_HTML = [
    ('<meta property="og:site_name" content="Taiwan Data 台灣數據">', '<meta property="og:site_name" content="Taiwan Data">'),
    ('<html lang="zh-Hant-TW">', '<html lang="en">'),
    ("<title>Taiwan Data 台灣數據：一眼看懂台灣的即時數字</title>", "<title>Taiwan Data: Taiwan's Live Numbers at a Glance</title>"),
    ('content="把政府開放資料整理成一眼看懂的工具：台灣水庫即時蓄水率與水情燈號、即時用電與供電燈號、每月出生與死亡人數、航班載客率、旅客人次，更多台灣數據陸續推出。"',
     'content="Government open data turned into easy-to-read tools: live reservoir levels and water alerts across Taiwan, live electricity demand and supply lights, monthly births and deaths, flight load factors, passenger and tourism statistics, with more to come."'),
    ('<link rel="canonical" href="https://taiwandata.info/">', '<link rel="canonical" href="https://taiwandata.info/en/">'),
    ('<meta property="og:locale" content="zh_TW">', '<meta property="og:locale" content="en_US">'),
    ('content="Taiwan Data 台灣數據：一眼看懂台灣的即時數字"', 'content="Taiwan Data: Taiwan\'s Live Numbers at a Glance"'),
    ('<meta property="og:url" content="https://taiwandata.info/">', '<meta property="og:url" content="https://taiwandata.info/en/">'),
    ("<h1>Taiwan Data 台灣數據</h1>", "<h1>Taiwan Data</h1>"),
    ('<p class="lead">把政府開放資料整理成一眼看懂的工具。</p>', '<p class="lead">Taiwan\'s government open data, turned into tools you can read at a glance.</p>'),
    ("<h2>水庫水情</h2>", "<h2>Reservoirs</h2>"),
    ("<p>各區官方水情燈號、主要水庫即時蓄水率，一張地圖看懂。</p>", "<p>Official water alert lights by region and live storage levels for every major reservoir, on one map.</p>"),
    ('<div class="num" id="res-updated">每小時更新</div>', '<div class="num" id="res-updated">Updated hourly</div>'),
    ("<h2>今日電力</h2>", "<h2>Electricity</h2>"),
    ("<p>現在用電多少、供電燈號、燃氣燃煤太陽能風力各佔多少。</p>", "<p>Live power demand, the supply light, and how much comes from gas, coal, solar and wind.</p>"),
    ('<div class="num">台電每 10 分鐘更新</div>', '<div class="num">Taipower updates every 10 minutes</div>'),
    ("<h2>出生與死亡</h2>", "<h2>Births and deaths</h2>"),
    ("<p>全台每月出生、死亡人數，各縣市比較與歷年趨勢。</p>", "<p>Monthly births and deaths across Taiwan, compared by county and over time.</p>"),
    ('<div class="num">內政部戶政司每月公布</div>', '<div class="num">Published monthly by the Ministry of the Interior</div>'),
    ("<h2>航班</h2>", "<h2>Flights</h2>"),
    ("<p>熱門航點與航空公司的旅客、載客率排行，哪條航線最滿一眼看懂。</p>", "<p>The busiest routes and airlines, and how full their flights are.</p>"),
    ('<div class="num">民航局每月公布</div>', '<div class="num">Published monthly by the Civil Aeronautics Administration</div>'),
    ("<h2>旅客人次</h2>", "<h2>Tourism</h2>"),
    ("<p>各機場旅客、來台旅客來源、出國目的地。</p>", "<p>Passengers at every airport, visitor origins and destinations abroad.</p>"),
    ('<div class="num">民航局每月、觀光署每年公布</div>', '<div class="num">Monthly airport and yearly tourism figures</div>'),
    ('<footer>本站為個人經營，非政府網站；所有數據皆來自政府開放資料。<a href="about/">關於本站</a></footer>',
     '<footer>An independent site, not affiliated with the government. All figures come from government open data. <a href="about/">About</a></footer>'),
    ('fetch("data/latest.json"', 'fetch("/data/latest.json"'),
    ('toLocaleString("zh-TW", { timeZone: "Asia/Taipei", month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit", hour12: false });',
     'toLocaleString("en-US", { timeZone: "Asia/Taipei", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit", hour12: false });'),
    ('textContent = "資料更新 " + t;', 'textContent = "Updated " + t;'),
]

# 航班頁：航點（民航局表上的城市名）英文名；沒列到的英文頁顯示中文
DESTS = {
    "上海浦東": "Shanghai Pudong", "上海虹橋": "Shanghai Hongqiao", "下地島": "Shimojishima", "亞庇": "Kota Kinabalu",
    "仙台": "Sendai", "伊斯坦堡": "Istanbul", "休士頓": "Houston", "佐賀": "Saga", "倫敦希斯洛": "London Heathrow",
    "克拉克": "Clark", "函館": "Hakodate", "北九州": "Kitakyushu", "北京": "Beijing", "南京": "Nanjing",
    "吉隆坡": "Kuala Lumpur", "名古屋": "Nagoya", "墨爾本": "Melbourne", "多倫多": "Toronto", "大分": "Oita",
    "大邱": "Daegu", "大阪": "Osaka", "奧克蘭": "Auckland", "安大略": "Ontario (California)", "宮崎": "Miyazaki",
    "宿霧": "Cebu", "富國島": "Phu Quoc", "寧波": "Ningbo", "小松": "Komatsu", "岡山": "Okayama", "峇里島": "Bali",
    "峴港": "Da Nang", "巴黎": "Paris", "布拉格": "Prague", "布里斯本": "Brisbane", "帛琉": "Palau", "廈門": "Xiamen",
    "廣島": "Hiroshima", "廣州": "Guangzhou", "慕尼黑": "Munich", "成都天府": "Chengdu Tianfu", "新加坡": "Singapore",
    "新潟": "Niigata", "旭川": "Asahikawa", "普吉": "Phuket", "曼谷廊曼": "Bangkok Don Mueang",
    "曼谷蘇凡納布": "Bangkok Suvarnabhumi", "札幌": "Sapporo", "杜拜": "Dubai", "杭州": "Hangzhou",
    "東京成田": "Tokyo Narita", "東京羽田": "Tokyo Haneda", "松山": "Matsuyama", "榮市": "Vinh", "檀香山": "Honolulu",
    "檳城": "Penang", "武漢": "Wuhan", "汶萊": "Brunei", "沖繩": "Okinawa", "河內": "Hanoi", "法蘭克福": "Frankfurt",
    "洛杉磯": "Los Angeles", "深圳": "Shenzhen", "清州": "Cheongju", "清邁": "Chiang Mai", "溫哥華": "Vancouver",
    "澳門": "Macau", "濟州": "Jeju", "熊本": "Kumamoto", "石垣島": "Ishigaki", "神戶": "Kobe", "福岡": "Fukuoka",
    "福島": "Fukushima", "福州": "Fuzhou", "秋田": "Akita", "米子": "Yonago", "米蘭": "Milan", "紐約": "New York",
    "維也納": "Vienna", "羅馬": "Rome", "胡志明市": "Ho Chi Minh City", "舊金山": "San Francisco", "芝加哥": "Chicago",
    "花卷": "Hanamaki", "芽莊金蘭": "Nha Trang (Cam Ranh)", "茨城": "Ibaraki", "蓮姜": "Da Lat", "薄荷島": "Bohol",
    "西雅圖": "Seattle", "達拉斯": "Dallas", "鄭州": "Zhengzhou", "重慶": "Chongqing", "金邊": "Phnom Penh",
    "釜山": "Busan", "長灘島(卡提克蘭)": "Boracay (Caticlan)", "關島": "Guam", "阿姆斯特丹": "Amsterdam",
    "阿布達比": "Abu Dhabi", "雅加達": "Jakarta", "雪梨": "Sydney", "青島": "Qingdao", "青森": "Aomori",
    "靜岡": "Shizuoka", "首爾仁川": "Seoul Incheon", "首爾金浦": "Seoul Gimpo", "香港": "Hong Kong", "馬尼拉": "Manila",
    "高松": "Takamatsu", "高知": "Kochi", "鳳凰城": "Phoenix", "鹿兒島": "Kagoshima", "仰光": "Yangon",
    "天津": "Tianjin", "瀋陽": "Shenyang", "大連": "Dalian", "長沙": "Changsha", "西安": "Xi'an", "昆明": "Kunming",
    "南昌": "Nanchang", "合肥": "Hefei", "濟南": "Jinan", "煙台": "Yantai", "溫州": "Wenzhou", "泉州": "Quanzhou",
    "無錫": "Wuxi", "揚州": "Yangzhou", "南寧": "Nanning", "貴陽": "Guiyang", "海口": "Haikou", "三亞": "Sanya",
    "哈爾濱": "Harbin", "石家莊": "Shijiazhuang", "太原": "Taiyuan", "蘭州": "Lanzhou", "常州": "Changzhou",
    "那霸": "Naha", "宮古島": "Miyako", "德里": "Delhi", "孟買": "Mumbai", "胡志明": "Ho Chi Minh City",
    "海防": "Hai Phong", "金蘭": "Cam Ranh", "暹粒": "Siem Reap", "曼谷": "Bangkok", "塞班": "Saipan",
    "加州安大略": "Ontario (California)", "倫敦": "London",
}

# 航班頁：航空公司（民航局表上的簡稱）英文名
AIRLINES = {
    "上海": "Shanghai Airlines", "中華": "China Airlines", "全亞洲": "AirAsia X", "全日空": "ANA", "南方": "China Southern",
    "可依": "Aero K", "台灣虎航": "Tigerair Taiwan", "吉祥": "Juneyao Air", "四川": "Sichuan Airlines",
    "國泰": "Cathay Pacific", "國航": "Air China", "土耳其": "Turkish Airlines", "大灣區": "Greater Bay Airlines",
    "大韓": "Korean Air", "太陽富國": "Sun PhuQuoc Airways", "宿霧太平洋": "Cebu Pacific", "山東": "Shandong Airlines",
    "廈門": "Xiamen Airlines", "德威": "T'way Air", "捷星日本": "Jetstar Japan", "新加坡": "Singapore Airlines",
    "日本": "Japan Airlines", "日本越洋": "Japan Transocean Air", "易斯達": "Eastar Jet", "星宇": "STARLUX",
    "春秋": "Spring Airlines", "東方": "China Eastern", "樂桃": "Peach", "汶萊皇家": "Royal Brunei",
    "泰亞洲": "Thai AirAsia", "泰國": "Thai Airways", "泰獅": "Thai Lion Air", "泰瑞(德威)": "T'way Air",
    "泰越捷": "Thai Vietjet", "海南": "Hainan Airlines", "深圳": "Shenzhen Airlines", "澳門": "Air Macau",
    "濟州": "Jeju Air", "真航": "Jin Air", "立榮": "UNI Air", "紐西蘭": "Air New Zealand", "聯合": "United Airlines",
    "荷蘭皇家": "KLM", "華信": "Mandarin Airlines", "菲亞洲": "Philippines AirAsia", "菲律賓": "Philippine Airlines",
    "菲律賓皇家": "Royal Air Philippines", "越南": "Vietnam Airlines", "越捷": "Vietjet", "越竹": "Bamboo Airways",
    "達美": "Delta", "酷航": "Scoot", "釜山": "Air Busan", "長榮": "EVA Air", "長龍": "Loong Air",
    "阿提哈德": "Etihad", "阿聯酋": "Emirates", "韓亞": "Asiana", "香港": "Hong Kong Airlines",
    "香港快運": "HK Express", "馬亞洲": "AirAsia", "馬來西亞": "Malaysia Airlines", "馬印": "Batik Air Malaysia",
    "緬甸": "Myanmar Airways", "首爾": "Air Seoul", "印尼亞洲": "Indonesia AirAsia",
    "天津": "Tianjin Airlines", "峇迪": "Batik Air",
    "美國": "American Airlines", "加拿大": "Air Canada", "法國": "Air France", "德國漢莎": "Lufthansa",
    "新加坡酷航": "Scoot", "印度": "Air India", "以色列": "El Al", "卡達": "Qatar Airways",
}

# 航班頁：機場代號 → (中文短名, 英文名)
AIRPORTS = {
    "ALL": ("全部機場", "All airports"), "TPE": ("桃園", "Taoyuan"), "KHH": ("高雄", "Kaohsiung"),
    "TSA": ("松山", "Taipei Songshan"), "RMQ": ("台中", "Taichung"), "HUN": ("花蓮", "Hualien"),
    "TTT": ("台東", "Taitung"), "MZG": ("澎湖", "Penghu"), "TNN": ("台南", "Tainan"), "CYI": ("嘉義", "Chiayi"),
    "CMJ": ("七美", "Qimei"), "WOT": ("望安", "Wang-an"), "KYD": ("蘭嶼", "Lanyu"), "GNI": ("綠島", "Green Island"),
    "KNH": ("金門", "Kinmen"), "MFK": ("馬祖北竿", "Matsu Beigan"), "PIF": ("屏東", "Pingtung"),
    "HSZ": ("新竹", "Hsinchu"), "LZN": ("馬祖南竿", "Matsu Nangan"), "HCN": ("恆春", "Hengchun"),
}
