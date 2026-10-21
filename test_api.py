from data.btcturk_api import api

print("BtcTurk API test ediliyor...")

# Ticker test
data = api.get_symbol_ticker("BTCTRY")
if data:
    fiyat = data.get("last", "N/A")
    degisim = data.get("dailyChange", "N/A")
    hacim = data.get("dailyVolume", "N/A")
    print(f"BTCTRY Fiyat: {fiyat} TL")
    print(f"Degisim: {degisim}%")
    print(f"Hacim: {hacim}")
    print("Ticker API calisiyor!")
else:
    print("Ticker API baglantisi kurulamadi.")

print("\n--- Tum Fiyatlar ---")
tum = api.get_all_tickers()
if tum and "data" in tum:
    for item in tum["data"][:5]:
        pair = item.get("pair", "")
        son = item.get("last", 0)
        print(f"{pair}: {son} TL")
    print(f"\nToplam {len(tum['data'])} parite bulundu.")
else:
    print("Tum fiyatlar alinamadi.")
