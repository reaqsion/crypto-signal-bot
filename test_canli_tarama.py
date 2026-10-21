"""Canli taramanin yakalamali (catch-up) davranisi -- gecici veritabaninda.

Sorulan soru: bilgisayar kapali kalirsa sinyal kaybolur mu?
Cevap bu testte: kaybolmaz, gecikir.

Calistir:  python test_canli_tarama.py
"""
import os
import tempfile
from datetime import datetime, timedelta

import database

_gecici = os.path.join(tempfile.mkdtemp(prefix="kriptobot_canli_"), "test.db")
database.DB_PATH = _gecici

import sistem.canli_tarama as ct  # noqa: E402
from kurallar.motor import get_all_rules  # noqa: E402

gecen = 0
kalan = 0

SEMBOL = "TESTTRY"
BASLANGIC = datetime.now().replace(minute=0, second=0, microsecond=0) - timedelta(days=30)
LOOKBACK = 7 * 24  # en uzun kural lookback'i


def kontrol(ad, beklenen, gercek):
    global gecen, kalan
    if beklenen == gercek:
        gecen += 1
        print(f"  [GECTI] {ad}")
    else:
        kalan += 1
        print(f"  [KALDI] {ad}: beklenen={beklenen!r} gercek={gercek!r}")


def mum_yaz(saat_baslangic, saat_bitis):
    """Fiyat duz gider, sonra keskin bir sicrama yapar ki kural tetiklensin."""
    conn = database.get_connection()
    c = conn.cursor()
    for sembol in (SEMBOL, "BTCTRY"):
        for saat in range(saat_baslangic, saat_bitis):
            # Ilk LOOKBACK saat duz, sonrasi her saat +%0.2 -> 7 gunde %5'i gecer
            fiyat = 100.0 if saat < LOOKBACK else 100.0 * (1.002 ** (saat - LOOKBACK))
            ts = int((BASLANGIC + timedelta(hours=saat)).timestamp())
            c.execute("""
                INSERT OR IGNORE INTO klines
                (symbol, resolution, open_time, open, high, low, close, volume)
                VALUES (?, '60', ?, ?, ?, ?, ?, 1.0)
            """, (sembol, ts, fiyat, fiyat, fiyat, fiyat))
    conn.commit()
    conn.close()


def sinyal_sayisi():
    conn = database.get_connection()
    n = conn.execute("SELECT COUNT(*) FROM signal_log WHERE source = 'live'").fetchone()[0]
    conn.close()
    return n


def sinyal_zamanlari():
    conn = database.get_connection()
    rows = conn.execute(
        "SELECT timestamp FROM signal_log WHERE source='live' ORDER BY id").fetchall()
    conn.close()
    return [r[0] for r in rows]


# ------------------------------------------------------------------- testler

def test_ilk_kosu_sadece_son_mumu_isler():
    """Ilk kosuda gecmisi bastan taramaz -- o backtest'in isi."""
    kontrol("ilk kosudan sonra tarama_durumu yazildi",
            True, ct.son_islenen(SEMBOL) is not None)

    # 10 gunluk (240) mum var ama ilk kosu SADECE son mumu islemeli.
    beklenen_son = int((BASLANGIC + timedelta(hours=10 * 24 - 1)).timestamp())
    kontrol("ilk kosu son mumda durdu", beklenen_son, ct.son_islenen(SEMBOL))

    # Tek mumda birden fazla kural ayni anda tetiklenebilir (MOM_1W_5/10/15),
    # ama sinyal sayisi kural sayisini gecemez -- gecerse gecmis taranmis demektir.
    kontrol("sinyal sayisi kural sayisini gecmiyor (gecmis taranmadi)",
            True, sinyal_sayisi() <= len(get_all_rules()))


def test_kapali_kalan_sure_yakalaniyor():
    """PC 5 gun kapali kaldi -> 5 gunluk mum eklendi -> hepsi islenmeli."""
    onceki_isaret = ct.son_islenen(SEMBOL)

    mum_yaz(10 * 24, 15 * 24)          # 5 gun daha mum
    ct.tara(semboller=[SEMBOL], veri_tazele=False)

    yeni_isaret = ct.son_islenen(SEMBOL)
    kontrol("tarama_durumu ilerledi", True, yeni_isaret > onceki_isaret)

    beklenen_son = int((BASLANGIC + timedelta(hours=15 * 24 - 1)).timestamp())
    kontrol("son islenen mum = elimizdeki EN SON mum", beklenen_son, yeni_isaret)


def test_sinyal_kendi_zamaniyla_kaydediliyor():
    """Gec gorulen sinyal, gorulme aniyla degil OLUSMA aniyla kaydedilmeli --
    yoksa ileri getiri olcumu yanlis noktadan hesaplanir."""
    zamanlar = sinyal_zamanlari()
    if not zamanlar:
        kontrol("en az bir sinyal uretildi", True, False)
        return

    simdi = datetime.now()
    en_son = datetime.fromisoformat(zamanlar[-1])
    kontrol("sinyal zaman damgasi GECMISTE (gorulme ani degil)",
            True, en_son < simdi - timedelta(hours=1))

    en_erken = datetime.fromisoformat(zamanlar[0])
    kontrol("sinyal zaman damgasi mum araliginda",
            True, BASLANGIC <= en_erken <= BASLANGIC + timedelta(days=15))


def test_ikinci_kosu_ayni_mumu_tekrar_islemez():
    onceki = sinyal_sayisi()
    ct.tara(semboller=[SEMBOL], veri_tazele=False)
    kontrol("yeni mum yokken yeni sinyal uretilmiyor", onceki, sinyal_sayisi())


def test_durum_makinesi_hala_tek_sinyal_veriyor():
    """Yakalama modunda bile surekli dogru kalan kosul tek sinyal uretmeli."""
    conn = database.get_connection()
    rows = conn.execute("""
        SELECT rule_name, COUNT(*) FROM signal_log
        WHERE source = 'live' GROUP BY rule_name
    """).fetchall()
    conn.close()
    # 15 gunluk yukselen seride MOM kurallari surekli dogru kalir;
    # kural basina 1-2 sinyal olmali, yuzlerce degil.
    asiri = [(r[0], r[1]) for r in rows if r[1] > 3]
    kontrol("hicbir kural 3'ten fazla sinyal uretmedi", [], asiri)


def test_gecikme_notu_ekleniyor():
    sinyal = {"symbol": SEMBOL, "rule_name": "X", "direction": "long",
              "price": 100.0, "timestamp": datetime.now() - timedelta(hours=50),
              "market_wide": False}
    metin = ct._mesaj(sinyal, datetime.now())
    kontrol("eski sinyalde GECIKMELI notu var", True, "GECIKMELI SINYAL" in metin)

    taze = dict(sinyal, timestamp=datetime.now())
    kontrol("taze sinyalde gecikme notu yok",
            False, "GECIKMELI SINYAL" in ct._mesaj(taze, datetime.now()))


if __name__ == "__main__":
    print("=== Canli tarama (yakalamali mod) testleri ===")
    print(f"gecici DB: {_gecici}")
    database.init_db()
    mum_yaz(0, 10 * 24)                        # 10 gunluk baslangic verisi
    ct.tara(semboller=[SEMBOL], veri_tazele=False)   # ilk kosu

    for ad in ["test_ilk_kosu_sadece_son_mumu_isler",
               "test_kapali_kalan_sure_yakalaniyor",
               "test_sinyal_kendi_zamaniyla_kaydediliyor",
               "test_ikinci_kosu_ayni_mumu_tekrar_islemez",
               "test_durum_makinesi_hala_tek_sinyal_veriyor",
               "test_gecikme_notu_ekleniyor"]:
        print(f"\n{ad}")
        globals()[ad]()

    print(f"\n{'=' * 50}")
    print(f"GECEN: {gecen}   KALAN: {kalan}")
    print("=" * 50)
    raise SystemExit(1 if kalan else 0)
