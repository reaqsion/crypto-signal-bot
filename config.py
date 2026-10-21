import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

BTCTURK_BASE_URL = "https://api.btcturk.com"
BTCTURK_GRAPH_URL = "https://graph-api.btcturk.com"

REQUEST_DELAY_MS = 200
MAX_RETRIES = 3

# Tek istekte kac gunluk pencere istenecek.
# BtcTurk graph API resolution=60 icin ~11.000 mum (458 gun) siniri koyuyor;
# 459 gunde INVALID_RESOLUTION_FOR_TIME_INTERVAL donuyor. 400 gun = 9.600 mum,
# emniyetli. Eski deger 30'du ve gereksiz yere 15 kat fazla istek atiyordu.
CHUNK_GUN = 400

TAKER_FEE = 0.0020
MAKER_FEE = 0.0012
ROUND_TRIP_COST = TAKER_FEE * 2

SYMBOLS = [
    "BTCTRY",
    "ETHTRY",
    "SOLTRY",
    "XRPTRY",
    "DOGETRY",
    "ADATRY",
    "AVAXTRY",
    "DOTTRY",
    "LINKTRY",
    "MATICTRY"
]

DEFLATOR_SYMBOL = "USDTTRY"

DB_PATH = "data/bot.db"

# Ham mum indirmenin baslangici. Saatlik mum BTCTRY icin 2014-01-01'e kadar
# geliyor (scripts/veri_kapsami.py ile olculdu); sembol bazinda gercek
# baslangic degisir ve indirici her sembolun gercek araligini basiyor.
INDIRME_START = "2014-01-01"

# Backtest'in baslangici. INDIRME_START'tan farkli olmasinin sebebi:
# deflator (USDTTRY) borsada 2018-07-10'da basliyor. Ondan oncesi icin kur
# arindirmasi YAPILAMAZ, dolayisiyla getiri yorumlanamaz. Baglayici kisit
# BTC'nin gecmisi degil, USDTTRY'nin gecmisi.
BACKTEST_START = "2018-07-10"
BACKTEST_END = "2026-09-01"

MAX_DAILY_NOTIFICATIONS = 3
COOLDOWN_HOURS = 24

# --- Ayarlanabilir parametreler ---
# Koda gomulmedi, buraya kondu.

# Kontrol job'i sinyal ani + N saat noktasindaki mumu arar. Tam o saatte mum
# yoksa en fazla bu kadar geriye bakar; disindaysa alani NULL birakir.
KONTROL_TOLERANS_SAAT = 6

# Walk-forward: test diliminin train dilimine gore kabul edilebilir en fazla
# bozulmasi (%). Eski kod 50 kullaniyordu, yani %49 bozulma "gecti" sayiliyordu.
WALK_FORWARD_MAX_BOZULMA = 30

# Walk-forward'da train diliminde en iyi esigi secerken kullanilan olcut.
# 'net_getiri' = komisyon + kur + piyasa arindirilmis ortalama 7 gunluk getiri.
WALK_FORWARD_SECIM_OLCUTU = "net_getiri"

# Train diliminde bir esigin degerlendirilebilmesi icin gereken en az sinyal.
WALK_FORWARD_MIN_SINYAL = 10

# Canli tarama her kosuda son kac gunluk mumu yeniden indirsin.
# (En uzun lookback 7 gun; 10 gun emniyet payi birakiyor.)
CANLI_TARAMA_TAZELEME_GUN = 10

# Canli tarama araligi (dakika). Mumlar saatlik oldugu icin daha sik taramanin
# anlami yok.
CANLI_TARAMA_DAKIKA = 60

# Gunluk snapshot araligi (saat).
SNAPSHOT_ARALIK_SAAT = 24

BIST_TOP_30 = [
    "THYAO", "GARAN", "AKBNK", "ASELS", "KCHOL",
    "BIMAS", "SAHOL", "EREGL", "SISE", "KOZAL",
    "TUPRS", "TCELL", "HEKTS", "PGSUS", "KOZAA",
    "TAVHL", "ARCLK", "TOASO", "FROTO", "VESTL",
    "YKBNK", "HALKB", "VAKBN", "SASA", "EKGYO",
    "ENKAI", "PETKM", "TCTR", "MGROS", "TKFEN"
]

BIST_BACKTEST_START = "2025-09-01"
BIST_BACKTEST_END = "2026-09-01"
