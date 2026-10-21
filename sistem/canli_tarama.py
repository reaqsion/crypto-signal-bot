"""Canli sinyal taramasi -- YAKALAMALI (catch-up) mod.

Parcalar zaten vardi ama birbirine bagli degildi: durum makinesi, bildirim
ve kontrol job'i canli bir sinyal akisi oldugunu varsayiyordu, ama o akisi
uretecek kimse yoktu. Bu dosya var olan parcalari birlestiriyor.

ONEMLI -- 7/24 acik kalamayan makine icin:
Tarama SADECE son muma bakmaz. `tarama_durumu` tablosunda her sembol icin
en son islenen mumu tutar ve her kosuda oradan bugune kadar butun mumlari
SIRAYLA isler. Yani bilgisayar 3 gun kapali kalirsa:

  - klines zaten geriye donuk indirilebiliyor (kayip yok)
  - acilista o 3 gunun mumlari sirayla durum makinesinden gecer
  - kacan sinyaller KENDI ZAMAN DAMGALARIYLA kaydedilir

Sinyal gec GORULUR ama kaybolmaz. Olcum icin bu yeterli, cunku ileri
getiriler sinyalin zaman damgasindan itibaren hesaplanir -- senin ne zaman
baktigindan bagimsiz. Gercek zamanli bildirim ancak Faz 3'te (gercek para)
zorunlu hale gelir.
"""
from datetime import datetime, timedelta, timezone

from database import get_connection
from data.sembol_dogrula import dogrula, SembolHatasi
from data.veri_indir import download_symbol, IndirmeHatasi
from backtest.olay_calismasi import (
    load_klines, get_btc_price, check_market_wide, calc_prior_return,
)
from kurallar.motor import get_all_rules
from sistem.durum_makinesi import degerlendir_canli
from sistem.bildirim import sinyal_kaydet, format_signal_message
from config import SYMBOLS, CANLI_TARAMA_TAZELEME_GUN

# Bir sinyal bu kadar saatten eskiyse mesaja "gecikmeli" notu dusulur.
GECIKME_UYARI_SAAT = 3


# ------------------------------------------------------------- tarama durumu

def son_islenen(symbol, resolution="60"):
    conn = get_connection()
    c = conn.cursor()
    row = c.execute("""
        SELECT son_islenen_open_time FROM tarama_durumu
        WHERE symbol = ? AND resolution = ?
    """, (symbol, resolution)).fetchone()
    conn.close()
    return row[0] if row else None


def son_isleneni_yaz(symbol, open_time, resolution="60"):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT OR REPLACE INTO tarama_durumu
        (symbol, resolution, son_islenen_open_time, guncellendi_at)
        VALUES (?, ?, ?, ?)
    """, (symbol, resolution, int(open_time), datetime.now().isoformat()))
    conn.commit()
    conn.close()


# ------------------------------------------------------------------- indirme

def taze_veri_cek(semboller, resolution="60"):
    """Son CANLI_TARAMA_TAZELEME_GUN gunu yeniden indirir (INSERT OR IGNORE).

    Kapali gecen sure bu penceredan uzunsa eksik mumlar gelmez; o yuzden
    pencere `tarama_durumu`'na gore genisletilir.
    """
    basarisiz = []
    simdi = datetime.now(tz=timezone.utc)

    for symbol in semboller:
        gerekli_gun = CANLI_TARAMA_TAZELEME_GUN
        son = son_islenen(symbol, resolution)
        if son is not None:
            bosluk_gun = (simdi - datetime.fromtimestamp(son, tz=timezone.utc)).days + 2
            gerekli_gun = max(gerekli_gun, bosluk_gun)

        baslangic = int((simdi - timedelta(days=gerekli_gun)).timestamp())
        try:
            download_symbol(symbol, resolution, baslangic)
        except IndirmeHatasi as e:
            basarisiz.append((symbol, str(e)))
            print(f"  ! {symbol} tazelenemedi: {e}")

    return basarisiz


# -------------------------------------------------------------------- tarama

def tara(semboller=None, resolution="60", veri_tazele=True):
    """En son islenen mumdan bugune kadar butun mumlari sirayla degerlendirir.

    Doner: gonderilecek mesajlarin listesi.
    """
    if semboller is None:
        semboller, _ = dogrula(SYMBOLS)

    if veri_tazele:
        taze_veri_cek(semboller, resolution)

    btc_df = load_klines("BTCTRY", resolution)
    rules = get_all_rules()
    mesajlar = []
    uretilen = 0
    bastirilan = 0
    islenen_mum = 0

    simdi = datetime.now()

    for symbol in semboller:
        df = load_klines(symbol, resolution)
        if df.empty:
            print(f"  ! {symbol}: klines bos, atlandi.")
            continue

        onceki = son_islenen(symbol, resolution)

        # Ilk kosuda gecmisi bastan taramiyoruz -- o backtest'in isi.
        # Sadece son mumdan baslayip ileriye dogru yakalama yapiyoruz.
        if onceki is None:
            baslangic_konum = len(df) - 1
        else:
            sonrakiler = df.index[df["open_time"] > onceki]
            if len(sonrakiler) == 0:
                continue  # yeni mum yok
            baslangic_konum = int(sonrakiler[0])

        en_dusuk = max(rule.get_required_lookback() for rule in rules)
        baslangic_konum = max(baslangic_konum, en_dusuk)

        for i in range(baslangic_konum, len(df)):
            open_time = df.iloc[i]["open_time"]
            mum_zamani = datetime.fromtimestamp(open_time)
            islenen_mum += 1

            for rule in rules:
                if i < rule.get_required_lookback():
                    continue

                kosul = bool(rule.evaluate(df, i))

                # Durum signal_state tablosundan okunur/yazilir; mantik
                # backtest ile ayni sinifta.
                if not degerlendir_canli(symbol, rule.name, kosul, mum_zamani):
                    continue

                sinyal = {
                    "timestamp": mum_zamani,
                    "symbol": symbol,
                    "rule_name": rule.name,
                    "direction": rule.direction,
                    "price": float(df.iloc[i]["close"]),
                    "btc_price": get_btc_price(btc_df, open_time),
                    "ret_30d_prior": calc_prior_return(df, i, 30 * 24),
                    "market_wide": check_market_wide(btc_df, open_time),
                }

                _, gonderilmeli = sinyal_kaydet(sinyal)
                uretilen += 1

                if gonderilmeli:
                    mesajlar.append(_mesaj(sinyal, simdi))
                else:
                    bastirilan += 1

            son_isleneni_yaz(symbol, open_time, resolution)

    print(f"  Canli tarama: {islenen_mum} mum islendi, {uretilen} sinyal uretildi, "
          f"{bastirilan} tanesi gunluk limit nedeniyle bastirildi (suppressed = 1).")
    return mesajlar


def _mesaj(sinyal, simdi):
    """Gec gorulen sinyale gecikme notu dusuyoruz -- taze sanilmasin."""
    metin = format_signal_message(sinyal)
    gecikme = (simdi - sinyal["timestamp"]).total_seconds() / 3600
    if gecikme >= GECIKME_UYARI_SAAT:
        metin += (f"\n\n⏱ GECIKMELI SINYAL: bu sinyal {gecikme:.0f} saat once olustu "
                  f"({sinyal['timestamp']:%Y-%m-%d %H:%M}). Fiyat o andaki fiyattir, "
                  f"su anki degil.")
    return metin


if __name__ == "__main__":
    import sys

    # Windows konsolu varsayilan olarak cp1254; mesajdaki emojiler
    # UnicodeEncodeError firlatiyordu. Telegram tarafi UTF-8, sorun yalnizca
    # bu script'in kendi ciktisinda.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

    try:
        mesajlar = tara()
    except SembolHatasi as e:
        print(f"Sembol dogrulama basarisiz: {e}")
        raise

    if not mesajlar:
        print("  Gonderilecek mesaj yok.")
    for m in mesajlar:
        print(m)
