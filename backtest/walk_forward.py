"""Walk-forward dogrulama.

Onceki hali esik SECMIYORDU: her esigi hem train hem test diliminde calistirip
sonuclari yan yana basiyordu. Bu, test diliminde de tum esikleri gormek
demek -- yani test dilimi de arama alanina dahil oluyordu ve "dogrulama"
olmaktan cikiyordu.

Dogrusu: train diliminde en iyi esigi SEC, sonra SADECE o esigi test
diliminde calistir. Test dilimi tek bir hipotezi gorur.

`degradation < 50` olcutu de keyfiydi (%49 bozulma "gecti" sayiliyordu);
artik config.WALK_FORWARD_MAX_BOZULMA'dan geliyor.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime

import pandas as pd
from database import get_connection
from kurallar.motor import get_all_rules
from sistem.tetikleme import TetiklemeDurumu
from backtest.olay_calismasi import (
    load_klines, calc_forward_return, btc_forward_return, usdtry_forward_return,
)
from config import (
    ROUND_TRIP_COST, COOLDOWN_HOURS,
    WALK_FORWARD_MAX_BOZULMA, WALK_FORWARD_SECIM_OLCUTU, WALK_FORWARD_MIN_SINYAL,
)

KOMISYON = ROUND_TRIP_COST * 100
UFUK_SAAT = 24 * 7


class WalkForwardHatasi(Exception):
    pass


def split_data(df, train_ratio=0.6):
    split_idx = int(len(df) * train_ratio)
    return df.iloc[:split_idx].reset_index(drop=True), df.iloc[split_idx:].reset_index(drop=True)


def kural_aileleri(rules=None):
    """Kurallari sinifina gore gruplar: {'MOM_1W': [rule, rule, rule], ...}"""
    if rules is None:
        rules = get_all_rules()
    aileler = {}
    for rule in rules:
        aile = type(rule).__name__
        aileler.setdefault(aile, []).append(rule)
    return aileler


def simulate_rule(rule, df, symbol, btc_df):
    """Bir kurali bir dilimde calistirir. Durum makinesi DAHIL -- backtest,
    canli ve walk-forward ayni tetikleme mantigini kullanir.

    Doner: her sinyal icin dort bilesenli kayit listesi.
    """
    makine = TetiklemeDurumu(COOLDOWN_HOURS)
    anahtar = f"{symbol}|{rule.name}"
    olaylar = []

    for i in range(rule.get_required_lookback(), len(df)):
        kosul = bool(rule.evaluate(df, i))
        zaman_ts = df.iloc[i]["open_time"]
        if not makine.degerlendir(anahtar, kosul, datetime.fromtimestamp(zaman_ts)):
            continue

        ham = calc_forward_return(df, i, UFUK_SAAT)
        if ham is None:
            continue  # ufuk dilim sonuna sigmiyor

        olaylar.append({
            "timestamp": zaman_ts,
            "rule_name": rule.name,
            "symbol": symbol,
            "price": df.iloc[i]["close"],
            "ham_7d": ham,
            "btc_7d": btc_forward_return(btc_df, zaman_ts, UFUK_SAAT),
            "usdtry_7d": usdtry_forward_return(zaman_ts, 7),
        })

    return olaylar


def dilim_metrigi(olaylar):
    """Bir dilimdeki olaylardan dort bilesenli ozet."""
    if not olaylar:
        return {"n": 0, "n_net": 0, "ham_getiri": None,
                "kur_arindirilmis": None, "net_getiri": None, "pozitif_oran": None}

    df = pd.DataFrame(olaylar)
    ham = df["ham_7d"]

    kur_var = df[df["usdtry_7d"].notna()]
    net_var = kur_var[kur_var["btc_7d"].notna()]

    ozet = {
        "n": len(df),
        "n_net": len(net_var),
        "ham_getiri": ham.mean(),
        "kur_arindirilmis": (kur_var["ham_7d"] - KOMISYON - kur_var["usdtry_7d"]).mean()
        if len(kur_var) else None,
        "net_getiri": None,
        "pozitif_oran": None,
    }

    if len(net_var):
        net = net_var["ham_7d"] - KOMISYON - net_var["usdtry_7d"] - net_var["btc_7d"]
        ozet["net_getiri"] = net.mean()
        ozet["pozitif_oran"] = (net > 0).mean() * 100

    return ozet


def walk_forward_test(symbol, resolution="60", train_ratio=0.6):
    """Train diliminde esik SEC, test diliminde SADECE o esigi calistir."""
    df = load_klines(symbol, resolution)
    if df.empty:
        raise WalkForwardHatasi(f"{symbol} icin klines tablosunda veri yok.")

    en_az_mum = UFUK_SAAT * 3
    if len(df) < en_az_mum:
        raise WalkForwardHatasi(
            f"{symbol}: {len(df)} mum var, walk-forward icin en az {en_az_mum} gerekiyor "
            f"(train + test dilimlerinin her birine 7 gunluk ufuk sigmali)."
        )

    btc_df = load_klines("BTCTRY", resolution)
    train_df, test_df = split_data(df, train_ratio)

    sonuclar = []
    for aile, rules in kural_aileleri().items():
        # --- 1) TRAIN: tum esikleri dene, en iyisini sec ---
        adaylar = []
        for rule in rules:
            ozet = dilim_metrigi(simulate_rule(rule, train_df, symbol, btc_df))
            adaylar.append((rule, ozet))

        uygun = [
            (r, o) for r, o in adaylar
            if o["n"] >= WALK_FORWARD_MIN_SINYAL and o[WALK_FORWARD_SECIM_OLCUTU] is not None
        ]

        if not uygun:
            sonuclar.append({
                "aile": aile,
                "secilen": None,
                "sebep": (f"train diliminde hicbir esik {WALK_FORWARD_MIN_SINYAL} sinyal "
                          f"esigini gecemedi ya da {WALK_FORWARD_SECIM_OLCUTU} hesaplanamadi "
                          f"(adaylar: {[(r.name, o['n']) for r, o in adaylar]})"),
            })
            continue

        secilen_rule, train_ozet = max(uygun, key=lambda x: x[1][WALK_FORWARD_SECIM_OLCUTU])

        # --- 2) TEST: SADECE secilen esik ---
        test_ozet = dilim_metrigi(simulate_rule(secilen_rule, test_df, symbol, btc_df))

        train_deger = train_ozet[WALK_FORWARD_SECIM_OLCUTU]
        test_deger = test_ozet[WALK_FORWARD_SECIM_OLCUTU]

        if test_deger is None:
            bozulma = None
            gecti = False
            sebep = "test diliminde olcut hesaplanamadi (sinyal yok ya da karsilastirma verisi eksik)"
        else:
            bozulma = ((train_deger - test_deger) / abs(train_deger) * 100) if train_deger else None
            gecti = (test_deger > 0) and (bozulma is not None) and (bozulma < WALK_FORWARD_MAX_BOZULMA)
            sebep = ""

        sonuclar.append({
            "aile": aile,
            "secilen": secilen_rule.name,
            "aday_sayisi": len(rules),
            "train": train_ozet,
            "test": test_ozet,
            "olcut": WALK_FORWARD_SECIM_OLCUTU,
            "train_deger": train_deger,
            "test_deger": test_deger,
            "bozulma": bozulma,
            "gecti": gecti,
            "sebep": sebep,
        })

    return sonuclar


def print_walk_forward_results(results, symbol=""):
    print(f"\n=== WALK-FORWARD DOGRULAMA {symbol} ===")
    print(f"Olcut: {WALK_FORWARD_SECIM_OLCUTU} | "
          f"max bozulma: %{WALK_FORWARD_MAX_BOZULMA} | "
          f"min train sinyali: {WALK_FORWARD_MIN_SINYAL}")
    print("Esik train diliminde SECILIR, test diliminde sadece o esik calisir.\n")

    for r in results:
        if r["secilen"] is None:
            print(f"{r['aile']}: SECIM YAPILAMADI -- {r['sebep']}")
            continue

        tr, te = r["train"], r["test"]
        print(f"{r['aile']}  ->  secilen esik: {r['secilen']}  "
              f"({r['aday_sayisi']} aday arasindan)")
        print(f"   train : n={tr['n']:<4} net={_f(tr['net_getiri'])}  "
              f"kur_arindirilmis={_f(tr['kur_arindirilmis'])}  ham={_f(tr['ham_getiri'])}")
        print(f"   test  : n={te['n']:<4} net={_f(te['net_getiri'])}  "
              f"kur_arindirilmis={_f(te['kur_arindirilmis'])}  ham={_f(te['ham_getiri'])}")
        if r["bozulma"] is None:
            print(f"   bozulma: - ({r['sebep']})")
        else:
            print(f"   bozulma: %{r['bozulma']:.1f}   ->  "
                  f"{'GECTI' if r['gecti'] else 'KALDI'}")
        print()


def _f(x):
    return "   -   " if x is None else f"{x:+7.3f}%"


if __name__ == "__main__":
    from data.sembol_dogrula import dogrula
    from config import SYMBOLS

    semboller, _ = dogrula(SYMBOLS)
    for symbol in semboller:
        try:
            sonuclar = walk_forward_test(symbol)
        except WalkForwardHatasi as e:
            print(f"\n{symbol}: ATLANDI -- {e}")
            continue
        print_walk_forward_results(sonuclar, symbol)
