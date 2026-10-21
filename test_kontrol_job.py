"""Kontrol job testi -- gecici veritabaninda, uretim DB'sine dokunmaz.

TALIMAT Gorev 6 kabul kriteri: bir sinyal 30 gun sonra kontrol edildiginde
price_1d GERCEKTEN 1 gun sonraki fiyat olmali (bugunun fiyati degil).

Calistir:  python test_kontrol_job.py
"""
import os
import tempfile
from datetime import datetime, timedelta

import database

# --- uretim DB'sine dokunmamak icin gecici dosya -------------------------------
_gecici = os.path.join(tempfile.mkdtemp(prefix="kriptobot_test_"), "test.db")
database.DB_PATH = _gecici

import sistem.kontrol_job as kj  # noqa: E402

gecen = 0
kalan = 0


def kontrol(ad, beklenen, gercek):
    global gecen, kalan
    if beklenen == gercek:
        gecen += 1
        print(f"  [GECTI] {ad}")
    else:
        kalan += 1
        print(f"  [KALDI] {ad}: beklenen={beklenen!r} gercek={gercek!r}")


# --- kurulum -------------------------------------------------------------------
# Sinyal 40 gun once verilmis, yani 1/7/30 gunluk ufuklarin hepsi dolmus.
SINYAL_ZAMANI = datetime.now().replace(minute=0, second=0, microsecond=0) - timedelta(days=40)


def fiyat_formulu(saat_ofseti):
    """Her saatin fiyati benzersiz olsun ki yanlis saat okunursa yakalayalim."""
    return 100.0 + saat_ofseti


def kur():
    database.init_db()
    conn = database.get_connection()
    c = conn.cursor()

    # 45 gunluk saatlik mum: sinyal aninda 0. saat, sonrasi artan.
    for sembol, carpan in (("TESTTRY", 1.0), ("BTCTRY", 10.0), ("USDTTRY", 0.1)):
        for saat in range(0, 45 * 24):
            ts = int((SINYAL_ZAMANI + timedelta(hours=saat)).timestamp())
            fiyat = fiyat_formulu(saat) * carpan
            c.execute("""
                INSERT OR IGNORE INTO klines
                (symbol, resolution, open_time, open, high, low, close, volume)
                VALUES (?, '60', ?, ?, ?, ?, ?, 1.0)
            """, (sembol, ts, fiyat, fiyat, fiyat, fiyat))

    c.execute("""
        INSERT INTO signal_log (id, timestamp, symbol, rule_name, direction, price, source)
        VALUES (1, ?, 'TESTTRY', 'TEST_KURAL', 'long', ?, 'live')
    """, (SINYAL_ZAMANI.isoformat(), fiyat_formulu(0)))

    conn.commit()
    conn.close()


def satiri_oku():
    conn = database.get_connection()
    row = conn.execute("SELECT * FROM signal_controls WHERE signal_id = 1").fetchone()
    conn.close()
    return row


# --- testler -------------------------------------------------------------------

def test_dogru_saatin_fiyati_yaziliyor():
    """Ana kabul kriteri."""
    row = satiri_oku()
    kontrol("price_1d = sinyal + 24 saat", fiyat_formulu(24), row["price_1d"])
    kontrol("price_7d = sinyal + 168 saat", fiyat_formulu(24 * 7), row["price_7d"])
    kontrol("price_30d = sinyal + 720 saat", fiyat_formulu(24 * 30), row["price_30d"])


def test_bugunun_fiyati_yazilmiyor():
    """Eski hatanin regresyon testi: 40 gun sonra kontrol edilse bile
    price_1d bugunun fiyati OLMAMALI."""
    row = satiri_oku()
    bugunun_fiyati = fiyat_formulu(40 * 24)
    kontrol("price_1d bugunun fiyati DEGIL", True, row["price_1d"] != bugunun_fiyati)
    kontrol("price_1d != price_7d (hepsi ayni degere ezilmemis)",
            True, row["price_1d"] != row["price_7d"])


def test_karsilastirma_sembolleri():
    """Gorev 6.4: BTCTRY ve USDTTRY icin de ayni islem."""
    row = satiri_oku()
    kontrol("btc_price_7d = BTCTRY'nin +168. saati",
            fiyat_formulu(24 * 7) * 10.0, row["btc_price_7d"])
    kontrol("usdtry_price_7d = USDTTRY'nin +168. saati",
            round(fiyat_formulu(24 * 7) * 0.1, 6), round(row["usdtry_price_7d"], 6))


def test_mum_yoksa_null_kaliyor():
    """Gorev 6.2: o noktada mum yoksa alan NULL, uydurma yok."""
    conn = database.get_connection()
    c = conn.cursor()
    # Mumsuz sembolle ikinci bir sinyal.
    c.execute("""
        INSERT INTO signal_log (id, timestamp, symbol, rule_name, direction, price, source)
        VALUES (2, ?, 'MUMSUZTRY', 'TEST_KURAL', 'long', 1.0, 'live')
    """, (SINYAL_ZAMANI.isoformat(),))
    conn.commit()
    conn.close()

    kj.check_pending_signals(source="live", verbose=False)

    conn = database.get_connection()
    row = conn.execute("SELECT * FROM signal_controls WHERE signal_id = 2").fetchone()
    conn.close()
    kontrol("mumsuz sembolde price_1d NULL", None, row["price_1d"])
    kontrol("mumsuz sembolde price_7d NULL", None, row["price_7d"])
    kontrol("ayni satirda btc_price_7d yine de dolu", True, row["btc_price_7d"] is not None)


def test_tekrar_calistirmak_ustune_yazmiyor():
    """Gorev 6.3: her ufuk bagimsiz; ikinci kosu dolu alanlari bozmamali."""
    onceki = dict(satiri_oku())
    kj.check_pending_signals(source="live", verbose=False)
    sonraki = dict(satiri_oku())
    for kolon in ("price_1d", "price_7d", "price_30d", "btc_price_7d"):
        kontrol(f"ikinci kosuda {kolon} degismedi", onceki[kolon], sonraki[kolon])


def test_kopya_satir_acilmiyor():
    """Gorev 4.3: UNIQUE(signal_id) sayesinde kopya satir yok."""
    conn = database.get_connection()
    n = conn.execute("SELECT COUNT(*) FROM signal_controls WHERE signal_id = 1").fetchone()[0]
    conn.close()
    kontrol("signal_id=1 icin tek satir", 1, n)


if __name__ == "__main__":
    print("=== Kontrol job testleri ===")
    print(f"gecici DB: {_gecici}")
    kur()
    kj.check_pending_signals(source="live", verbose=False)

    for ad in ["test_dogru_saatin_fiyati_yaziliyor",
               "test_bugunun_fiyati_yazilmiyor",
               "test_karsilastirma_sembolleri",
               "test_mum_yoksa_null_kaliyor",
               "test_tekrar_calistirmak_ustune_yazmiyor",
               "test_kopya_satir_acilmiyor"]:
        print(f"\n{ad}")
        globals()[ad]()

    print(f"\n{'=' * 50}")
    print(f"GECEN: {gecen}   KALAN: {kalan}")
    print("=" * 50)
    raise SystemExit(1 if kalan else 0)
