"""Sinyal sonrasi kontrol fiyatlarini doldurur + alarmlari kontrol eder.

Onceki hali YANLIS FIYATI yaziyordu: mevcut ticker fiyatini alip price_1d,
price_7d, price_30d alanlarina koyuyordu. 8. gunde kontrol edilen bir sinyalde
price_1d bugunun fiyati oluyordu -- 1. gunun degil.

Artik `klines` tablosundan sinyal ani + N saat noktasindaki kapanis okunuyor.
O noktada mum yoksa alan NULL kaliyor; uydurulmuyor.
"""
from datetime import datetime, timedelta
from database import get_connection
from data.btcturk_api import api
from config import DEFLATOR_SYMBOL, KONTROL_TOLERANS_SAAT

# (alan_soneki, sinyal aninda kac saat sonrasi)
UFUKLAR = [("1d", 24), ("7d", 24 * 7), ("30d", 24 * 30)]

# Hangi sembolun hangi kolon onekine yazilacagi.
# None = sinyalin kendi sembolu.
KARSILASTIRMALAR = [
    ("price", None),
    ("btc_price", "BTCTRY"),
    ("usdtry_price", DEFLATOR_SYMBOL),
]


def kline_kapanis(symbol, hedef_zaman, resolution="60"):
    """hedef_zaman noktasindaki kapanis. Yoksa None -- uydurma yok.

    Tam o saatte mum olmayabilir (borsa boslugu). En fazla
    config.KONTROL_TOLERANS_SAAT kadar geriye bakilir; daha eskisi kabul
    edilmez, cunku 1 gun sonrasi yerine 5 gun oncesini yazmak yanlis olur.
    """
    hedef_ts = int(hedef_zaman.timestamp())
    en_erken = hedef_ts - KONTROL_TOLERANS_SAAT * 3600

    conn = get_connection()
    c = conn.cursor()
    row = c.execute("""
        SELECT close, open_time FROM klines
        WHERE symbol = ? AND resolution = ?
          AND open_time <= ? AND open_time >= ?
        ORDER BY open_time DESC
        LIMIT 1
    """, (symbol, resolution, hedef_ts, en_erken)).fetchone()
    conn.close()

    return row[0] if row else None


def _kontrol_satiri(c, signal_id):
    """signal_controls satirini garantiler ve mevcut halini doner."""
    c.execute("INSERT OR IGNORE INTO signal_controls (signal_id) VALUES (?)", (signal_id,))
    c.execute("SELECT * FROM signal_controls WHERE signal_id = ?", (signal_id,))
    return c.fetchone()


def check_pending_signals(source="live", verbose=True):
    """Suresi dolmus ufuklari klines'tan doldurur.

    Her ufuk BAGIMSIZ doldurulur: 7 gunluk alan dolduruldugunda 1 gunluk
    alanin uzerine yazilmaz (eski kod tek INSERT OR REPLACE ile hepsini
    birden eziyordu).
    """
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT id, symbol, timestamp FROM signal_log
        WHERE source = ?
        ORDER BY id
    """, (source,))
    sinyaller = c.fetchall()

    simdi = datetime.now()
    dolduruldu = 0
    bos_birakildi = 0

    for signal_id, symbol, timestamp in sinyaller:
        sinyal_zamani = datetime.fromisoformat(timestamp)
        mevcut = _kontrol_satiri(c, signal_id)

        for onek, karsilastirma_sembolu in KARSILASTIRMALAR:
            hedef_sembol = karsilastirma_sembolu or symbol

            for sonek, saat in UFUKLAR:
                kolon = f"{onek}_{sonek}"
                if mevcut[kolon] is not None:
                    continue  # zaten dolu, dokunma

                hedef_zaman = sinyal_zamani + timedelta(hours=saat)
                if hedef_zaman > simdi:
                    continue  # ufuk henuz dolmadi

                kapanis = kline_kapanis(hedef_sembol, hedef_zaman)
                if kapanis is None:
                    bos_birakildi += 1
                    continue

                c.execute(
                    f"UPDATE signal_controls SET {kolon} = ? WHERE signal_id = ?",
                    (kapanis, signal_id)
                )
                dolduruldu += 1

        c.execute(
            "UPDATE signal_controls SET checked_at = ? WHERE signal_id = ?",
            (simdi.isoformat(), signal_id)
        )

    conn.commit()
    conn.close()

    if verbose:
        print(f"  Kontrol: {len(sinyaller)} sinyal tarandi, {dolduruldu} alan dolduruldu, "
              f"{bos_birakildi} alan mum bulunamadigi icin NULL birakildi.")

    return {"taranan": len(sinyaller), "dolduruldu": dolduruldu, "bos": bos_birakildi}


def check_alarms(user_id=None):
    conn = get_connection()
    c = conn.cursor()

    if user_id:
        c.execute("""
            SELECT id, symbol, direction, target_price
            FROM alarms
            WHERE active = 1 AND user_id = ?
        """, (user_id,))
    else:
        c.execute("""
            SELECT id, user_id, symbol, direction, target_price
            FROM alarms
            WHERE active = 1
        """)

    alarmlar = c.fetchall()
    conn.close()

    tetiklenenler = []
    for alarm in alarmlar:
        if user_id:
            alarm_id, symbol, direction, target = alarm
            alarm_user_id = user_id
        else:
            alarm_id, alarm_user_id, symbol, direction, target = alarm

        data = api.get_symbol_ticker(symbol)
        if not data:
            print(f"  ! Alarm {alarm_id}: {symbol} icin ticker alinamadi, atlandi.")
            continue

        mevcut_fiyat = float(data.get("last", 0))
        if mevcut_fiyat <= 0:
            print(f"  ! Alarm {alarm_id}: {symbol} fiyati gecersiz ({mevcut_fiyat}), atlandi.")
            continue

        tetiklendi = False
        if direction == "yukari" and mevcut_fiyat >= target:
            tetiklendi = True
        elif direction == "asagi" and mevcut_fiyat <= target:
            tetiklendi = True

        if tetiklendi:
            tetiklenenler.append({
                "alarm_id": alarm_id,
                "user_id": alarm_user_id,
                "symbol": symbol,
                "direction": direction,
                "target": target,
                "current": mevcut_fiyat
            })
            deactivate_alarm(alarm_id)

    return tetiklenenler


def deactivate_alarm(alarm_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE alarms SET active = 0 WHERE id = ?", (alarm_id,))
    conn.commit()
    conn.close()


def run_control_jobs():
    print(f"Kontrol job'lari calisiyor: {datetime.now()}")
    check_pending_signals()
    tetiklenen = check_alarms()
    print(f"  Tetiklenen alarm: {len(tetiklenen)}")

    mesajlar = []
    for alarm in tetiklenen:
        yon = "YUKARI" if alarm["direction"] == "yukari" else "ASAGI"
        mesaj = (
            f"ALARM TETIKLENDI!\n"
            f"Hisse: {alarm['symbol']}\n"
            f"Yon: {yon}\n"
            f"Hedef: {alarm['target']:.2f} TL\n"
            f"Mevcut: {alarm['current']:.2f} TL"
        )
        mesajlar.append({"user_id": alarm["user_id"], "mesaj": mesaj})

    return mesajlar


if __name__ == "__main__":
    run_control_jobs()
