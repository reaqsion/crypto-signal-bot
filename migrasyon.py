"""Sema migrasyonlari.

Kural: tablo silinmez, veri kaybedilmez. Her migrasyon bir kez calisir,
`schema_migrations` tablosuna yazilir. Idempotent.

Calistir:  python migrasyon.py
"""
from database import get_connection


_SESSIZ = False


def _yaz(mesaj):
    if not _SESSIZ:
        print(mesaj)


def _kolonlar(c, tablo):
    return {r[1] for r in c.execute(f"PRAGMA table_info({tablo})")}


def _kolon_ekle(c, tablo, kolon, tip):
    if kolon in _kolonlar(c, tablo):
        _yaz(f"    - {tablo}.{kolon} zaten var, atlandi")
        return
    c.execute(f"ALTER TABLE {tablo} ADD COLUMN {kolon} {tip}")
    _yaz(f"    + {tablo}.{kolon} eklendi")


# ---------------------------------------------------------------- migrasyonlar

def m001_signal_log_ileri_getiriler(c):
    """run_event_study forward_* hesapliyordu ama yazacak kolon yoktu.

    run_id: signal_log'da duzeltme oncesi 32k bozuk satir var. Silmiyoruz;
    her backtest kosusu kendi run_id'siyle yaziliyor, metrikler son kosuyu
    okuyor. Eski satirlar run_id = NULL kaliyor.
    """
    for kolon in ("forward_1d", "forward_7d", "forward_30d",
                  "btc_forward_7d", "usdtry_forward_7d"):
        _kolon_ekle(c, "signal_log", kolon, "REAL")
    _kolon_ekle(c, "signal_log", "run_id", "TEXT")


def m002_signal_controls_unique(c):
    """signal_id uzerinde UNIQUE yoktu, bu yuzden INSERT OR REPLACE replace
    etmiyor kopya satir aciyordu. SQLite ALTER ile constraint eklemiyor;
    yeni tablo + veri kopyasi + rename. Veri kaybi yok.

    usdtry_price_* kolonlari Gorev 5/6'nin ihtiyaci olan kur karsilastirmasi
    icin ayni migrasyonda ekleniyor (tablo zaten yeniden kuruluyor).
    """
    mevcut = _kolonlar(c, "signal_controls")
    eski_sayi = c.execute("SELECT COUNT(*) FROM signal_controls").fetchone()[0]

    c.execute("""
        CREATE TABLE IF NOT EXISTS signal_controls_yeni (
            signal_id INTEGER PRIMARY KEY,
            price_1d REAL,
            price_7d REAL,
            price_30d REAL,
            btc_price_1d REAL,
            btc_price_7d REAL,
            btc_price_30d REAL,
            usdtry_price_1d REAL,
            usdtry_price_7d REAL,
            usdtry_price_30d REAL,
            checked_at TEXT,
            FOREIGN KEY(signal_id) REFERENCES signal_log(id)
        )
    """)

    tasinacak = [k for k in ("signal_id", "price_1d", "price_7d", "price_30d",
                             "btc_price_1d", "btc_price_7d", "btc_price_30d")
                 if k in mevcut]
    kolon_listesi = ", ".join(tasinacak)
    # Kopya satirlar varsa en cok dolu olani kalsin.
    c.execute(f"""
        INSERT OR REPLACE INTO signal_controls_yeni ({kolon_listesi})
        SELECT {kolon_listesi} FROM signal_controls
        ORDER BY (price_1d IS NOT NULL) + (price_7d IS NOT NULL) + (price_30d IS NOT NULL)
    """)
    yeni_sayi = c.execute("SELECT COUNT(*) FROM signal_controls_yeni").fetchone()[0]

    c.execute("DROP TABLE signal_controls")
    c.execute("ALTER TABLE signal_controls_yeni RENAME TO signal_controls")
    _yaz(f"    signal_controls yeniden kuruldu: {eski_sayi} satir -> {yeni_sayi} "
          f"(UNIQUE(signal_id) eklendi, {eski_sayi - yeni_sayi} kopya birlestirildi)")


def m003_signal_log_suppressed(c):
    """sistem/bildirim.py `suppressed` kolonunu sorguluyordu ama kolon yoktu.
    Kolon eklendi; gunluk bildirim limiti yuzunden gonderilmeyen sinyaller
    signal_log'a suppressed = 1 ile yaziliyor (kaybolmuyorlar)."""
    _kolon_ekle(c, "signal_log", "suppressed", "INTEGER DEFAULT 0")


def m004_tarama_durumu(c):
    """Canli taramanin nereye kadar isledigini tutar.

    PC 7/24 acik kalamadigi icin tarama son mumu degil, EN SON ISLENEN
    mumdan sonrasini bastan sona islemeli. Boylece kapali gecen sure
    sinyal kaybina degil, gecikmeye donusur.
    """
    c.execute("""
        CREATE TABLE IF NOT EXISTS tarama_durumu (
            symbol TEXT,
            resolution TEXT,
            son_islenen_open_time INTEGER,
            guncellendi_at TEXT,
            UNIQUE(symbol, resolution)
        )
    """)
    _yaz("    + tarama_durumu tablosu")


def m005_abone(c):
    """Canli sinyalin gonderilecegi chat_id'ler.

    Bug: canli tarama job'i chat_id olmadan kaydedilmisti, dolayisiyla
    uretilen sinyal signal_log'a yaziliyor ama Telegram'a HIC gonderilmiyordu.
    /basla calistiran her sohbet buraya yaziliyor.
    """
    c.execute("""
        CREATE TABLE IF NOT EXISTS abone (
            chat_id INTEGER PRIMARY KEY,
            kullanici TEXT,
            kayit_at TEXT,
            aktif INTEGER DEFAULT 1
        )
    """)
    _yaz("    + abone tablosu")


MIGRASYONLAR = [
    ("001_signal_log_ileri_getiriler", m001_signal_log_ileri_getiriler),
    ("002_signal_controls_unique", m002_signal_controls_unique),
    ("003_signal_log_suppressed", m003_signal_log_suppressed),
    ("004_tarama_durumu", m004_tarama_durumu),
    ("005_abone", m005_abone),
]


# ---------------------------------------------------------------------- calistir

def migrasyonlari_uygula(sessiz=False):
    global _SESSIZ
    _SESSIZ = sessiz
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            ad TEXT PRIMARY KEY,
            uygulandi_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    uygulanmis = {r[0] for r in c.execute("SELECT ad FROM schema_migrations")}

    yeni = 0
    for ad, fn in MIGRASYONLAR:
        if ad in uygulanmis:
            continue
        _yaz(f"  -> {ad}")
        fn(c)
        c.execute("INSERT INTO schema_migrations (ad) VALUES (?)", (ad,))
        yeni += 1

    conn.commit()
    conn.close()

    _yaz(f"{yeni} migrasyon uygulandi." if yeni else "Tum migrasyonlar zaten uygulanmis.")
    return yeni


if __name__ == "__main__":
    print("=== MIGRASYON ===")
    migrasyonlari_uygula()
