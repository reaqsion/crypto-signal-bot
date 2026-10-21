from datetime import datetime, timedelta
from data.veri_indir import download_symbol
from data.deflator import update_deflator
from data.veri_sagligi import print_health_report
from backtest.olay_calismasi import run_event_study, save_events
from backtest.metrikler import calc_metrics, print_metrics, group_by_rule
from backtest.walk_forward import walk_forward_test, print_walk_forward_results
from config import SYMBOLS
import pandas as pd

print("=" * 60)
print("KRIPTO BOT KAPSAMLI TEST")
print("=" * 60)

# 1. Veri indir (son 3 ay)
print("\n1. VERI INDIRME")
print("-" * 40)
start = int((datetime.now() - timedelta(days=90)).timestamp())
for symbol in SYMBOLS[:3]:  # Sadece ilk 3 symbol
    ozet = download_symbol(symbol, "60", start)
    print(f"  {symbol}: {ozet['kaydedilen']} mum")

# 2. Deflatör güncelle
print("\n2. DEFLATOR GUNCELLEME")
print("-" * 40)
update_deflator()

# 3. Sağlık raporu
print("\n3. SAGLIK RAPORU")
print("-" * 40)
print_health_report()

# 4. Backtest
print("\n4. BACKTEST")
print("-" * 40)
all_events = []
for symbol in SYMBOLS[:3]:
    events = run_event_study(symbol)
    all_events.extend(events)
    print(f"  {symbol}: {len(events)} sinyal")

save_events(all_events)

# 5. Metrikler
print("\n5. METRIKLER")
print("-" * 40)
if all_events:
    events_df = pd.DataFrame(all_events)
    metrics = calc_metrics(events_df)
    print_metrics(metrics)

    print("\n--- KURAL BAZLI ---")
    grouped = group_by_rule(events_df)
    for rule_name, rule_metrics in grouped.items():
        print(f"\n{rule_name}:")
        print_metrics(rule_metrics)

# 6. Walk-forward
print("\n6. WALK-FORWARD DOGRULAMA")
print("-" * 40)
for symbol in SYMBOLS[:2]:
    results = walk_forward_test(symbol)
    if results:
        print_walk_forward_results(results)
    else:
        print(f"  {symbol}: Yeterli veri yok")

print("\n" + "=" * 60)
print("TEST TAMAMLANDI")
print("=" * 60)
