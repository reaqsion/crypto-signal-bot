"""Canli sinyal kaydi ve bildirim metinleri.

Gunluk bildirim limiti dolunca sinyal SILINMEZ: signal_log'a suppressed = 1
ile yazilir. Boylece "bugun kac sinyal bastirildi" sorusu cevaplanabilir ve
bastirilan sinyaller de olcume dahil olur.
"""
from datetime import datetime
from database import get_connection
from config import MAX_DAILY_NOTIFICATIONS


def get_daily_notification_count():
    """Bugun GONDERILEN (bastirilmamis) canli sinyal sayisi."""
    conn = get_connection()
    c = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    c.execute("""
        SELECT COUNT(*) FROM signal_log
        WHERE DATE(timestamp) = ? AND source = 'live'
          AND (suppressed IS NULL OR suppressed = 0)
    """, (today,))
    count = c.fetchone()[0]
    conn.close()
    return count


def can_send_notification():
    return get_daily_notification_count() < MAX_DAILY_NOTIFICATIONS


def get_suppressed_count_today():
    """Bugun limit yuzunden gonderilmeyen sinyal sayisi."""
    conn = get_connection()
    c = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    c.execute("""
        SELECT COUNT(*) FROM signal_log
        WHERE DATE(timestamp) = ? AND suppressed = 1
    """, (today,))
    count = c.fetchone()[0]
    conn.close()
    return count


def sinyal_kaydet(signal_data):
    """Canli sinyali signal_log'a yazar.

    Gunluk limit dolduysa suppressed = 1 ile yazilir ve gonderilmez.
    Doner: (signal_id, gonderilmeli)
    """
    zorunlu = ("symbol", "rule_name", "direction", "price")
    eksik = [k for k in zorunlu if signal_data.get(k) is None]
    if eksik:
        raise KeyError(f"Canli sinyal kaydinda zorunlu alan eksik: {eksik} -> {signal_data}")

    gonderilmeli = can_send_notification()
    zaman = signal_data.get("timestamp") or datetime.now()
    if isinstance(zaman, datetime):
        zaman = zaman.isoformat()

    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO signal_log
        (timestamp, symbol, rule_name, direction, price, btc_price,
         ret_30d_prior, market_wide, source, suppressed)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'live', ?)
    """, (
        zaman,
        signal_data["symbol"],
        signal_data["rule_name"],
        signal_data["direction"],
        signal_data["price"],
        signal_data.get("btc_price"),
        signal_data.get("ret_30d_prior"),
        signal_data.get("market_wide", False),
        0 if gonderilmeli else 1,
    ))
    signal_id = c.lastrowid
    conn.commit()
    conn.close()

    return signal_id, gonderilmeli


def format_signal_message(signal_data):
    symbol = signal_data.get("symbol")
    rule_name = signal_data.get("rule_name")
    price = signal_data.get("price", 0)
    direction = signal_data.get("direction")
    market_wide = signal_data.get("market_wide", False)

    mesaj = f"""
🔔 SINYAL TETIKLENDI!

Sembol: {symbol}
Kural: {rule_name}
Yon: {direction.upper()}
Fiyat: {price:,.2f} TL

💰 Maliyet Analizi:
1000 TL alim icin ~4 TL komisyon
Basabas icin +%0.40 hareket gerekli

⚠️ Dikkat: Bu bir tavsiye degil, sadece sinyaldir.
Karar senin!
    """

    if market_wide:
        mesaj += "\n📈 Piyasa genelinde hareket var."

    return mesaj


def format_summary_message(suppressed_count):
    if suppressed_count == 0:
        return None

    return f"📊 Bugun {suppressed_count} sinyal bastirildi. (Gunluk limit: {MAX_DAILY_NOTIFICATIONS})"
