from data.veri_indir import download_symbol
from data.veri_sagligi import full_health_report
from database import get_connection

print("=== KUCUK TEST: BTC 1 HAFTA ===\n")

# Sadece son 1 haftayi indir
from datetime import datetime, timedelta
start = int((datetime.now() - timedelta(days=7)).timestamp())

ozet = download_symbol("BTCTRY", "60", start)
print(f"\nIndirilen mum sayisi: {ozet['kaydedilen']}")

# Veritabanindan oku
conn = get_connection()
c = conn.cursor()
c.execute("SELECT COUNT(*) FROM klines WHERE symbol = 'BTCTRY'")
db_count = c.fetchone()[0]
conn.close()

print(f"Veritabanindaki toplam mum: {db_count}")

# Saglik raporu
print("\n=== SAGLIK RAPORU ===")
report = full_health_report("BTCTRY")
print(f"Durum: {report['overall']}")
print(f"Eksik saat: {report['missing_hours']['missing']}")
print(f"Sifir hacim: {report['zero_volume']['count']}")
print(f"Fiyat spike: {report['price_spikes']['count']}")
print(f"Gecersiz fiyat: {report['invalid_prices']['count']}")
