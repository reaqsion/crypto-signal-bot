from data.btcturk_api import api

print("=== TICKER VERI YAPISI ===\n")

data = api.get_ticker()
if data and "data" in data:
    for item in data["data"][:3]:
        print("Tum alanlar:")
        for key, value in item.items():
            print(f"  {key}: {value}")
        print()
