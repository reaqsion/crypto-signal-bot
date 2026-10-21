from data.veri_indir import download_symbol
from kurallar.motor import get_all_rules
from database import get_connection
import pandas as pd
from datetime import datetime, timedelta

print("=== KURAL MOTORU TESTI ===\n")

# Once veri indir (son 30 gun)
start = int((datetime.now() - timedelta(days=30)).timestamp())
download_symbol("BTCTRY", "60", start)

# Veritabanindan oku
conn = get_connection()
query = """
    SELECT open_time, open, high, low, close, volume
    FROM klines
    WHERE symbol = 'BTCTRY' AND resolution = '60'
    ORDER BY open_time
"""
df = pd.read_sql_query(query, conn)
conn.close()

print(f"Toplam mum sayisi: {len(df)}")

# Kurallari test et
rules = get_all_rules()
print(f"\nTest edilecek kural sayisi: {len(rules)}")

for rule in rules:
    lookback = rule.get_required_lookback()
    sinyal_sayisi = 0

    for i in range(lookback, len(df)):
        if rule.evaluate(df, i):
            sinyal_sayisi += 1

    print(f"\n{rule.name}:")
    print(f"  Aciklama: {rule.description}")
    print(f"  Lookback: {lookback} mum")
    print(f"  Bulunan sinyal: {sinyal_sayisi}")
