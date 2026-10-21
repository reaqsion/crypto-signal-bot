from datetime import datetime
from database import get_connection
from backtest.metrikler import load_controls, calc_metrics, group_by_rule, print_metrics
from backtest.walk_forward import walk_forward_test, print_walk_forward_results
from config import SYMBOLS, ROUND_TRIP_COST


def generate_full_report():
    print("=" * 60)
    print("KRIPTO BOT BACKTEST RAPORU")
    print(f"Tarih: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    df = load_controls()
    if df.empty:
        print("\nHenuz sinyal yok. Once backtest calistirin.")
        return

    print("\n--- GENEL METRIKLER ---")
    metrics = calc_metrics(df)
    print_metrics(metrics, "GENEL")

    print("\n--- KURAL BAZLI ANALIZ ---")
    grouped = group_by_rule(df)
    for rule_name, rule_metrics in grouped.items():
        print(f"\n{rule_name}:")
        print_metrics(rule_metrics)

    print("\n--- WALK-FORWARD DOGRULAMA ---")
    for symbol in SYMBOLS[:5]:
        print(f"\n{symbol}:")
        results = walk_forward_test(symbol)
        if results:
            print_walk_forward_results(results)
        else:
            print("Yeterli veri yok.")

    print("\n--- OZET ---")
    total = metrics.get("total_signals", 0)
    avg_net_7d = metrics.get("avg_net_forward_7d", 0)
    positive_rate = metrics.get("positive_rate_net_forward_7d", 0)

    print(f"Toplam sinyal: {total}")
    print(f"Ortalama net getiri (7 gun): %{avg_net_7d:.2f}")
    print(f"Pozitif orani: %{positive_rate:.1f}")

    if avg_net_7d > 0 and positive_rate > 55:
        print("\nSONUC: Kural potansiyel olarak karli.")
    elif avg_net_7d > 0:
        print("\nSONUC: Kural sinirli, dikkatli kullanilmali.")
    else:
        print("\nSONUC: Kural karli degil. Eşikler gozden gecirilmeli.")


def export_report_to_file(filename="backtest_raporu.txt"):
    import sys
    import io

    old_stdout = sys.stdout
    sys.stdout = buffer = io.StringIO()

    generate_full_report()

    sys.stdout = old_stdout
    report = buffer.getvalue()

    with open(filename, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"Rapor {filename} dosyasina kaydedildi.")
    return report


if __name__ == "__main__":
    generate_full_report()
