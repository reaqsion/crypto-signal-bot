import time
from data.btcturk_api import api

print("API yanit suresi testi:\n")

start = time.time()
data = api.get_symbol_ticker("BTCTRY")
elapsed = time.time() - start

if data:
    fiyat = data.get("last", "N/A")
    print(f"Ticker: {elapsed:.2f} saniye")
    print(f"BTCTRY: {fiyat} TL")
else:
    print("API yanit vermedi!")

start2 = time.time()
klines = api.get_klines("BTCTRY", "60")
elapsed2 = time.time() - start2

if klines and "t" in klines:
    print(f"Klines: {elapsed2:.2f} saniye ({len(klines['t'])} mum)")
else:
    print("Klines alinamadi!")
