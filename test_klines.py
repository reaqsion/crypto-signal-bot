from data.btcturk_api import api
from datetime import datetime, timedelta

print("Tarihsel veri testi...")

# Son 7 gunun verisini cek
end_date = int(datetime.now().timestamp())
start_date = int((datetime.now() - timedelta(days=7)).timestamp())

print(f"Baslangic: {datetime.fromtimestamp(start_date)}")
print(f"Bitis: {datetime.fromtimestamp(end_date)}")

data = api.get_klines("BTCTRY", "60", start_date, end_date)

if data and "t" in data:
    mum_sayisi = len(data["t"])
    print(f"\nBasarili! {mum_sayisi} mum verisi alindi.")

    if mum_sayisi > 0:
        print("\nSon 5 mum:")
        for i in range(-5, 0):
            t = datetime.fromtimestamp(data["t"][i])
            o = data["o"][i]
            h = data["h"][i]
            l = data["l"][i]
            c = data["c"][i]
            v = data["v"][i]
            print(f"  {t}: O={o:,.0f} H={h:,.0f} L={l:,.0f} C={c:,.0f} V={v:.4f}")
else:
    print("Veri alinamadi.")
    print(f"Response keys: {list(data.keys()) if data else 'None'}")
