"""Lookahead (gelecege bakma) regresyon testi -- gecici veritabaninda.

TALIMAT Gorev 7.4: ayni kurala veriyi `t`'de kesilmis halde ve kesilmemis
halde ver. `t` anindaki sonuc ikisinde de AYNI olmali. Farkliysa kod
gelecekten bilgi siziyor demektir.

Calistir:  python test_lookahead.py
"""
import os
import random
import tempfile
from datetime import datetime, timedelta

import database

_gecici = os.path.join(tempfile.mkdtemp(prefix="kriptobot_look_"), "test.db")
database.DB_PATH = _gecici

import pandas as pd  # noqa: E402
from backtest.olay_calismasi import (  # noqa: E402
    run_event_study, index_at_or_before, get_btc_price, check_market_wide,
)
from kurallar.motor import get_all_rules  # noqa: E402

gecen = 0
kalan = 0

# Gelecege bagli olmasi MESRU olan alanlar -- karsilastirmadan cikarilir.
ILERI_ALANLAR = {"forward_1d", "forward_7d", "forward_30d",
                 "btc_forward_7d", "usdtry_forward_7d"}

BASLANGIC = datetime(2026, 1, 1)
MUM_SAYISI = 24 * 60          # 60 gun saatlik
KESME_NOKTASI = 24 * 40       # t = 40. gun


def kontrol(ad, beklenen, gercek):
    global gecen, kalan
    if beklenen == gercek:
        gecen += 1
        print(f"  [GECTI] {ad}")
    else:
        kalan += 1
        print(f"  [KALDI] {ad}\n          beklenen={beklenen!r}\n          gercek  ={gercek!r}")


def seri_uret(tohum, baslangic_fiyat):
    random.seed(tohum)
    fiyat = baslangic_fiyat
    satirlar = []
    for saat in range(MUM_SAYISI):
        fiyat *= (1 + random.uniform(-0.01, 0.01))
        satirlar.append({
            "open_time": int((BASLANGIC + timedelta(hours=saat)).timestamp()),
            "open": fiyat, "high": fiyat, "low": fiyat, "close": fiyat, "volume": 1.0,
        })
    return satirlar


def db_kur(kesme=None):
    """kesme verilirse klines tablosu ilk `kesme` mumla sinirli yazilir."""
    if os.path.exists(database.DB_PATH):
        os.remove(database.DB_PATH)
    database.init_db()
    conn = database.get_connection()
    c = conn.cursor()
    for sembol, tohum, fiyat in (("TESTTRY", 1, 100.0), ("BTCTRY", 2, 2_000_000.0)):
        satirlar = seri_uret(tohum, fiyat)
        if kesme is not None:
            satirlar = satirlar[:kesme]
        for k in satirlar:
            c.execute("""
                INSERT OR IGNORE INTO klines
                (symbol, resolution, open_time, open, high, low, close, volume)
                VALUES (?, '60', ?, ?, ?, ?, ?, ?)
            """, (sembol, k["open_time"], k["open"], k["high"], k["low"], k["close"], k["volume"]))
    conn.commit()
    conn.close()


def kesme_zamani():
    return int((BASLANGIC + timedelta(hours=KESME_NOKTASI - 1)).timestamp())


# ------------------------------------------------------------------- testler

def test_index_at_or_before_gelecegi_secmiyor():
    df = pd.DataFrame(seri_uret(1, 100.0))
    # Tam mumlar arasina dusen bir an: 10. mumdan 30 dakika sonrasi.
    ara_an = df.loc[10, "open_time"] + 1800
    idx = index_at_or_before(df, ara_an)
    kontrol("iki mum arasindaki an -> ONCEKI mum secilir", 10, int(idx))

    # Eski hatali davranis en yakini seciyordu; 31. dakikada 11. mumu secerdi.
    ara_an2 = df.loc[10, "open_time"] + 3500  # 11. muma cok daha yakin
    kontrol("sonraki muma daha yakin olsa bile ONCEKI secilir",
            10, int(index_at_or_before(df, ara_an2)))


def test_veri_baslangicinda_none():
    """Gorev 7.2: uygun mum yoksa exception degil, None."""
    df = pd.DataFrame(seri_uret(1, 100.0))
    onceki_an = df.loc[0, "open_time"] - 3600
    kontrol("veri baslangicindan once -> None", None, index_at_or_before(df, onceki_an))
    kontrol("get_btc_price veri oncesinde None", None, get_btc_price(df, onceki_an))
    kontrol("check_market_wide veri oncesinde False", False, check_market_wide(df, onceki_an))
    kontrol("bos df -> None", None, index_at_or_before(pd.DataFrame(columns=["open_time"]), 0))


def test_kesilmis_ve_kesilmemis_veri_ayni_sonucu_veriyor():
    """Ana regresyon testi."""
    db_kur(kesme=None)
    tam = run_event_study("TESTTRY")

    db_kur(kesme=KESME_NOKTASI)
    kesik = run_event_study("TESTTRY")

    t = kesme_zamani()
    tam_t = [e for e in tam if e["timestamp"] <= t]
    kesik_t = [e for e in kesik if e["timestamp"] <= t]

    kontrol("t'ye kadar uretilen sinyal SAYISI ayni", len(tam_t), len(kesik_t))

    farklar = []
    for a, b in zip(tam_t, kesik_t):
        for alan in a:
            if alan in ILERI_ALANLAR:
                continue
            if a[alan] != b[alan]:
                farklar.append((a["timestamp"], alan, a[alan], b[alan]))
    kontrol("t'ye kadar hicbir gecmise donuk alan farkli degil", [], farklar)


def test_ileri_getiriler_kesildiginde_none_oluyor():
    """Kesilmis veride gelecek yok -> forward_* None olmali, uydurulmamali.
    Bu testin amaci ILERI_ALANLAR'i karsilastirma disi birakmanin
    dogru oldugunu gostermek."""
    db_kur(kesme=KESME_NOKTASI)
    kesik = run_event_study("TESTTRY")
    if not kesik:
        kontrol("kesik veride en az bir sinyal var", True, False)
        return
    son = kesik[-1]
    kontrol("kesik verinin son sinyalinde forward_30d None",
            None, son["forward_30d"])


def test_kural_kendisi_gelecege_bakmiyor():
    """Kurallar dogrudan: ayni indekste tam ve kesik df ayni sonucu vermeli."""
    tam_df = pd.DataFrame(seri_uret(1, 100.0))
    kesik_df = tam_df.iloc[:KESME_NOKTASI].copy()
    farklar = []
    for rule in get_all_rules():
        for i in range(rule.get_required_lookback(), KESME_NOKTASI):
            if rule.evaluate(tam_df, i) != rule.evaluate(kesik_df, i):
                farklar.append((rule.name, i))
    kontrol("hicbir kural kesilme durumunda farkli sonuc vermiyor", [], farklar)


if __name__ == "__main__":
    print("=== Lookahead regresyon testleri ===")
    print(f"gecici DB: {_gecici}")
    for ad in ["test_index_at_or_before_gelecegi_secmiyor",
               "test_veri_baslangicinda_none",
               "test_kural_kendisi_gelecege_bakmiyor",
               "test_kesilmis_ve_kesilmemis_veri_ayni_sonucu_veriyor",
               "test_ileri_getiriler_kesildiginde_none_oluyor"]:
        print(f"\n{ad}")
        globals()[ad]()

    print(f"\n{'=' * 50}")
    print(f"GECEN: {gecen}   KALAN: {kalan}")
    print("=" * 50)
    raise SystemExit(1 if kalan else 0)
