"""Canli taraf icin durum makinesi: saf TetiklemeDurumu + signal_state tablosu.

Mantik burada DEGIL, sistem/tetikleme.py'da. Bu dosya sadece o mantigi
veritabanina baglar. Backtest ayni sinifi bellek icinde kullanir; boylece
iki taraf ayni davranir.
"""
from datetime import datetime
from database import get_connection
from config import COOLDOWN_HOURS
from sistem.tetikleme import TetiklemeDurumu, ARMED, FIRED

__all__ = [
    "ARMED", "FIRED", "TetiklemeDurumu",
    "get_state", "set_state", "degerlendir_canli", "get_all_states",
]


def get_state(symbol, rule_name):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT status, last_fired FROM signal_state
        WHERE symbol = ? AND rule_name = ?
    """, (symbol, rule_name))
    row = c.fetchone()
    conn.close()
    return row


def set_state(symbol, rule_name, status, last_fired):
    if last_fired is not None and not isinstance(last_fired, datetime):
        raise TypeError(f"last_fired datetime olmali, {type(last_fired).__name__} geldi.")
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT OR REPLACE INTO signal_state (symbol, rule_name, status, last_fired)
        VALUES (?, ?, ?, ?)
    """, (symbol, rule_name, status, last_fired.isoformat() if last_fired else None))
    conn.commit()
    conn.close()


def degerlendir_canli(symbol, rule_name, kosul_saglandi, zaman=None):
    """Canli akisin tek giris noktasi. Sinyal uretilmeli mi?

    Durumu signal_state'ten okur, saf sinifa verir, sonucu geri yazar.
    """
    if zaman is None:
        zaman = datetime.now()

    anahtar = f"{symbol}|{rule_name}"
    makine = TetiklemeDurumu(COOLDOWN_HOURS)

    row = get_state(symbol, rule_name)
    if row is not None:
        status, last_fired = row["status"], row["last_fired"]
        if status not in (ARMED, FIRED):
            raise ValueError(
                f"signal_state tablosunda gecersiz durum: {symbol}/{rule_name} -> {status!r}"
            )
        makine.durum_yaz(
            anahtar,
            status,
            datetime.fromisoformat(last_fired) if last_fired else None,
        )

    ateslendi = makine.degerlendir(anahtar, bool(kosul_saglandi), zaman)

    yeni_status, yeni_last_fired = makine.durum_al(anahtar)
    set_state(symbol, rule_name, yeni_status, yeni_last_fired)

    return ateslendi


def get_all_states():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM signal_state")
    rows = c.fetchall()
    conn.close()
    return rows
