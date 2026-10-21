from database import get_connection
from config import SYMBOLS


def check_missing_hours(symbol, resolution="60"):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT open_time FROM klines
        WHERE symbol = ? AND resolution = ?
        ORDER BY open_time
    """, (symbol, resolution))
    times = [row[0] for row in c.fetchall()]
    conn.close()

    if not times:
        return {"status": "empty", "missing": 0}

    expected_interval = 3600 if resolution == "60" else 14400
    missing = 0
    for i in range(1, len(times)):
        diff = times[i] - times[i-1]
        if diff > expected_interval * 1.5:
            missing += (diff // expected_interval) - 1

    return {"status": "ok" if missing == 0 else "warning", "missing": missing}


def check_zero_volume(symbol, resolution="60"):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT COUNT(*) FROM klines
        WHERE symbol = ? AND resolution = ? AND volume = 0
    """, (symbol, resolution))
    count = c.fetchone()[0]
    conn.close()
    return {"count": count, "status": "ok" if count == 0 else "warning"}


def check_price_spikes(symbol, resolution="60", threshold=30):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT open_time, open, close FROM klines
        WHERE symbol = ? AND resolution = ?
        ORDER BY open_time
    """, (symbol, resolution))
    rows = c.fetchall()
    conn.close()

    spikes = []
    for i in range(1, len(rows)):
        if rows[i-1][2] > 0:
            change = abs(rows[i][2] - rows[i-1][2]) / rows[i-1][2] * 100
            if change > threshold:
                spikes.append({"time": rows[i][0], "change": change})

    return {"count": len(spikes), "spikes": spikes[:5]}


def check_invalid_prices(symbol, resolution="60"):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT COUNT(*) FROM klines
        WHERE symbol = ? AND resolution = ? AND (close <= 0 OR open <= 0)
    """, (symbol, resolution))
    count = c.fetchone()[0]
    conn.close()
    return {"count": count, "status": "ok" if count == 0 else "error"}


def full_health_report(symbol, resolution="60"):
    report = {
        "symbol": symbol,
        "resolution": resolution,
        "missing_hours": check_missing_hours(symbol, resolution),
        "zero_volume": check_zero_volume(symbol, resolution),
        "price_spikes": check_price_spikes(symbol, resolution),
        "invalid_prices": check_invalid_prices(symbol, resolution)
    }

    has_error = (report["missing_hours"]["status"] == "error" or
                 report["invalid_prices"]["count"] > 0)

    report["overall"] = "error" if has_error else "ok"
    return report


def print_health_report():
    print("=== VERI SAGLIK RAPORU ===\n")
    for symbol in SYMBOLS:
        report = full_health_report(symbol)
        status = "OK" if report["overall"] == "ok" else "HATA"
        print(f"{status} {symbol}")
        print(f"  Eksik saat: {report['missing_hours']['missing']}")
        print(f"  Sifir hacim: {report['zero_volume']['count']}")
        print(f"  Fiyat spike: {report['price_spikes']['count']}")
        print(f"  Gecersiz fiyat: {report['invalid_prices']['count']}")
        print()


if __name__ == "__main__":
    print_health_report()
