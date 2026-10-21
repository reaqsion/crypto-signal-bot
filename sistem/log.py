from datetime import datetime
from database import get_connection


def log_signal(symbol, rule_name, direction, price, btc_price=None,
               ret_30d_prior=None, market_wide=False, source="live"):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO signal_log (timestamp, symbol, rule_name, direction, price,
                               btc_price, ret_30d_prior, market_wide, source)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.now().isoformat(),
        symbol,
        rule_name,
        direction,
        price,
        btc_price,
        ret_30d_prior,
        market_wide,
        source
    ))
    signal_id = c.lastrowid
    conn.commit()
    conn.close()
    return signal_id


def update_control_prices(signal_id, price_1d, price_7d, price_30d,
                          btc_price_1d=None, btc_price_7d=None, btc_price_30d=None):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT OR REPLACE INTO signal_controls
        (signal_id, price_1d, price_7d, price_30d, btc_price_1d, btc_price_7d, btc_price_30d)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (signal_id, price_1d, price_7d, price_30d,
          btc_price_1d, btc_price_7d, btc_price_30d))
    conn.commit()
    conn.close()


def mark_executed(signal_id, entry_price):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        UPDATE signal_log SET
        gercekten_aldim = 1,
        gercek_giris_fiyati = ?
        WHERE id = ?
    """, (entry_price, signal_id))
    conn.commit()
    conn.close()


def get_recent_signals(limit=10):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT * FROM signal_log
        ORDER BY id DESC
        LIMIT ?
    """, (limit,))
    rows = c.fetchall()
    conn.close()
    return rows
