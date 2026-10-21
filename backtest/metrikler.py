"""Karar metrikleri.

Bu proje TRY paritelerinde calisiyor. Ham getiri tek basina yaniltici:
BTCTRY yukari egimli cunku hem BTC degerleniyor hem lira deger kaybediyor.
Bir kuralin ise yarayip yaramadigini soyleyebilmek icin ham getiriden dort
bileseni ayirmak gerekiyor:

    net_getiri = ham_getiri
               - (ROUND_TRIP_COST * 100)   # komisyon
               - usdtry_getirisi           # kur etkisi (enflasyon)
               - btc_getirisi              # piyasa etkisi

Dordu de ayri ayri raporlanir; hangi bilesenin ne kadar katki yaptigi gorunur.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from database import get_connection
from data.deflator import DeflatorHatasi, deflator_araligi
from kurallar.motor import get_all_rules
from config import ROUND_TRIP_COST

# Ayristirmanin yapildigi ufuk. Dort bilesenin tamami bu ufukta uretiliyor.
ANA_UFUK = "forward_7d"
UFUKLAR = ["forward_1d", "forward_7d", "forward_30d"]

NAN = float("nan")


class MetrikHatasi(Exception):
    pass


def deneme_sayisi():
    """HYPOTHESIS.md ile ayni sayim: kac farkli (kural, tutma suresi) denemesi var."""
    return len(get_all_rules()) * len(UFUKLAR)


# ------------------------------------------------------------------ veri okuma

def son_run_id():
    conn = get_connection()
    c = conn.cursor()
    row = c.execute("SELECT MAX(run_id) FROM signal_log WHERE run_id IS NOT NULL").fetchone()
    conn.close()
    return row[0] if row else None


def load_signals(run_id=None):
    """Sinyalleri okur. run_id verilmezse SON kosu okunur.

    Duzeltme oncesi 32k satirin run_id'si NULL; onlar karismasin diye.
    """
    if run_id is None:
        run_id = son_run_id()
    if run_id is None:
        raise MetrikHatasi(
            "signal_log'da run_id'li kayit yok. Once backtest calistir: "
            "python backtest/olay_calismasi.py"
        )

    conn = get_connection()
    df = pd.read_sql_query(
        "SELECT * FROM signal_log WHERE run_id = ? ORDER BY timestamp",
        conn, params=(run_id,)
    )
    conn.close()
    return df


def load_controls(run_id=None):
    """Sinyaller + canli kontrol fiyatlari."""
    if run_id is None:
        run_id = son_run_id()
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT sl.*, sc.price_1d, sc.price_7d, sc.price_30d,
               sc.btc_price_1d, sc.btc_price_7d, sc.btc_price_30d,
               sc.usdtry_price_1d, sc.usdtry_price_7d, sc.usdtry_price_30d
        FROM signal_log sl
        LEFT JOIN signal_controls sc ON sl.id = sc.signal_id
        WHERE sl.run_id = ?
        ORDER BY sl.timestamp
    """, conn, params=(run_id,))
    conn.close()
    return df


# ------------------------------------------------------------------- hesaplama

def _kolon_zorunlu(df, kolon):
    if kolon not in df.columns:
        raise MetrikHatasi(
            f"signal_log'da '{kolon}' kolonu yok. Migrasyon calismamis olabilir: "
            f"python migrasyon.py"
        )


def ayristir(df):
    """7 gunluk getiriyi dort bilesene ayirir."""
    for kolon in (ANA_UFUK, "btc_forward_7d", "usdtry_forward_7d"):
        _kolon_zorunlu(df, kolon)

    ham_var = df[df[ANA_UFUK].notna()]
    if ham_var.empty:
        raise MetrikHatasi(
            f"Hicbir sinyalde {ANA_UFUK} yok. Ya backtest calismadi ya da tum "
            f"sinyaller veri sonuna cok yakin."
        )

    # GOREV 5.4: deflator eksikse sessizce sifir kabul etme, bagir.
    kur_eksik = ham_var[ham_var["usdtry_forward_7d"].isna()]
    if not kur_eksik.empty:
        n, ilk, son = deflator_araligi()
        tarihler = sorted(kur_eksik["timestamp"].str[:10].unique())
        raise DeflatorHatasi(
            f"{len(kur_eksik)} sinyalde usdtry_forward_7d yok -> deflator tablosu "
            f"o tarihleri kapsamiyor. Eksik tarihler (ilk 5): {tarihler[:5]}. "
            f"Deflator tablosu: {n} satir, {ilk} -> {son}. "
            f"Kur arindirmasi yapilmadan getiri yorumlanamaz. "
            f"Duzeltmek icin: python -m data.deflator"
        )

    piyasa_var = ham_var[ham_var["btc_forward_7d"].notna()]
    komisyon = ROUND_TRIP_COST * 100

    ham = ham_var[ANA_UFUK]
    kur = ham_var["usdtry_forward_7d"]

    sonuc = {
        "n_sinyal": len(df),
        "n_ham": len(ham_var),
        "n_piyasa": len(piyasa_var),
        "n_btc_eksik": len(ham_var) - len(piyasa_var),

        "ham_getiri": ham.mean(),
        "komisyon": komisyon,
        "kur_etkisi": kur.mean(),

        "komisyon_sonrasi": (ham - komisyon).mean(),
        "kur_arindirilmis": (ham - komisyon - kur).mean(),

        "ham_pozitif_oran": (ham > 0).mean() * 100,
        "kur_arindirilmis_pozitif_oran": ((ham - komisyon - kur) > 0).mean() * 100,
    }

    if piyasa_var.empty:
        sonuc["piyasa_etkisi"] = None
        sonuc["net_getiri"] = None
        sonuc["net_pozitif_oran"] = None
        sonuc["net_std"] = None
        sonuc["net_t_istatistik"] = None
    else:
        p_ham = piyasa_var[ANA_UFUK]
        p_kur = piyasa_var["usdtry_forward_7d"]
        p_btc = piyasa_var["btc_forward_7d"]
        net = p_ham - komisyon - p_kur - p_btc

        sonuc["piyasa_etkisi"] = p_btc.mean()
        sonuc["net_getiri"] = net.mean()
        sonuc["net_pozitif_oran"] = (net > 0).mean() * 100
        sonuc["net_std"] = net.std()
        sonuc["net_t_istatistik"] = calc_t_statistic(net.mean(), net.std(), len(net))

    return sonuc


def calc_metrics(df):
    """Tum ufuklar icin temel istatistikler + 7 gunluk ayristirma."""
    if df.empty:
        raise MetrikHatasi("Bos sinyal kumesi ile metrik hesaplanamaz.")

    metrics = {
        "toplam_sinyal": len(df),
        "kural_sayisi": df["rule_name"].nunique(),
        "sembol_sayisi": df["symbol"].nunique(),
        "deneme_sayisi": deneme_sayisi(),
    }

    for kolon in UFUKLAR:
        _kolon_zorunlu(df, kolon)
        gecerli = df[kolon].dropna()
        metrics[f"n_{kolon}"] = len(gecerli)
        if len(gecerli) > 0:
            metrics[f"ort_{kolon}"] = gecerli.mean()
            metrics[f"medyan_{kolon}"] = gecerli.median()
            metrics[f"std_{kolon}"] = gecerli.std()
            metrics[f"pozitif_oran_{kolon}"] = (gecerli > 0).mean() * 100

    metrics["ayristirma"] = ayristir(df)
    return metrics


def calc_t_statistic(mean, std, n):
    if std is None or n == 0 or pd.isna(std) or std == 0:
        return 0.0
    return mean / (std / (n ** 0.5))


def group_by_rule(df):
    grouped = {}
    for rule_name in df["rule_name"].unique():
        grouped[rule_name] = calc_metrics(df[df["rule_name"] == rule_name])
    return grouped


# --------------------------------------------------------------------- yazdirma

def print_metrics(metrics, title="METRIKLER"):
    a = metrics.get("ayristirma", {})

    print(f"\n=== {title} ===")
    # GOREV 10.3: deneme sayisi sonuca bakarken hep goz onunde olsun.
    print(f"DENEME SAYISI: {metrics['deneme_sayisi']}  "
          f"(ne kadar cok kombinasyon denendiyse tesaduf o kadar kolay iyi gorunur)")
    print(f"Sinyal: {metrics['toplam_sinyal']}  "
          f"Kural: {metrics['kural_sayisi']}  Sembol: {metrics['sembol_sayisi']}")

    print("\n-- KAPSAM --")
    for kolon in UFUKLAR:
        print(f"  {kolon:<14} dolu: {metrics.get('n_' + kolon, 0)}/{metrics['toplam_sinyal']}")
    if a.get("n_btc_eksik"):
        print(f"  ! {a['n_btc_eksik']} sinyalde btc_forward_7d yok "
              f"(BTCTRY klines o tarihleri kapsamiyor).")
        print(f"    Piyasa arindirilmis satirlar {a['n_piyasa']} sinyalden hesaplandi, "
              f"digerleri DISARIDA.")

    komisyon = a.get("komisyon", ROUND_TRIP_COST * 100)
    print(f"\n-- 7 GUNLUK GETIRI AYRISTIRMASI (N={a.get('n_ham', 0)}) --")
    print(f"  1. Ham getiri                 : {a.get('ham_getiri', NAN):+9.4f} %")
    print(f"  2. Komisyon (round trip)      : {-komisyon:+9.4f} %")
    print(f"     -> komisyon sonrasi        : {a.get('komisyon_sonrasi', NAN):+9.4f} %")
    print(f"  3. Kur etkisi (USDTRY)        : {-a.get('kur_etkisi', NAN):+9.4f} %")
    print(f"     -> kur arindirilmis        : {a.get('kur_arindirilmis', NAN):+9.4f} %")

    if a.get("net_getiri") is None:
        print("  4. Piyasa etkisi (BTC)        :  YOK -- btc_forward_7d hicbir sinyalde dolu degil")
        print("     -> NET                     :  HESAPLANAMADI")
    else:
        print(f"  4. Piyasa etkisi (BTC)        : {-a['piyasa_etkisi']:+9.4f} %   (N={a['n_piyasa']})")
        print(f"     -> NET                     : {a['net_getiri']:+9.4f} %")
        print(f"\n  Net pozitif oran              : {a['net_pozitif_oran']:.1f} %")
        print(f"  Net t-istatistigi             : {a['net_t_istatistik']:.3f}")

    print("\n-- UFUK BAZLI HAM GETIRI --")
    for kolon in UFUKLAR:
        if ("ort_" + kolon) in metrics:
            print(f"  {kolon:<14} ort {metrics['ort_' + kolon]:+7.3f} %  "
                  f"medyan {metrics['medyan_' + kolon]:+7.3f} %  "
                  f"pozitif {metrics['pozitif_oran_' + kolon]:5.1f} %  "
                  f"(N={metrics['n_' + kolon]})")


if __name__ == "__main__":
    run = son_run_id()
    print(f"run_id: {run}")
    df = load_signals(run)
    print_metrics(calc_metrics(df), title=f"TUM SINYALLER (run {run})")

    print("\n\n############ KURAL BAZLI ############")
    for rule_name, m in group_by_rule(df).items():
        print_metrics(m, title=rule_name)
