from backtest.olay_calismasi import run_event_study, save_events
from backtest.metrikler import calc_metrics, print_metrics, group_by_rule
from config import SYMBOLS
import pandas as pd

print("=== BACKTEST TESTI ===\n")

# Sadece BTC ile test et
symbol = "BTCTRY"
print(f"{symbol} icin olay calismasi baslatiliyor...")

events = run_event_study(symbol)
print(f"Bulunan olay sayisi: {len(events)}")

if events:
    events_df = pd.DataFrame(events)
    print(f"\n--- OLAY DETAYLARI ---")
    print(events_df.head())

    # Metrikleri hesapla
    print(f"\n--- METRIKLER ---")
    metrics = calc_metrics(events_df)
    print_metrics(metrics)

    # Kural bazli analiz
    print(f"\n--- KURAL BAZLI ANALIZ ---")
    grouped = group_by_rule(events_df)
    for rule_name, rule_metrics in grouped.items():
        print(f"\n{rule_name}:")
        print_metrics(rule_metrics)

    # Veritabanina kaydet
    save_events(events)
    print(f"\nOlaylar veritabanina kaydedildi.")
else:
    print("Henuz olay yok.")
