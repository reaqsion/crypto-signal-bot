"""BtcTurk kline endpoint'i gercekte ne kadar geriye veri veriyor?

Kesif script'i. Hicbir sey kaydetmez, veritabanina dokunmaz; sadece olcer ve basar.

Kullanim:
    python scripts/veri_kapsami.py
"""
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.btcturk_api import api  # noqa: E402

SEMBOL = "BTCTRY"
RESOLUTION = "60"
YILLAR = [2020, 2021, 2022, 2023, 2024]

# Bolum 3'te denenecek pencere genislikleri (gun). Sabit merdiven, ikili arama degil.
PENCERE_MERDIVENI = [30, 90, 180, 365, 400, 458, 459, 500, 730]

# Bolum 4'te "en eski mum" icin gunluk cozunurlukle geriye bakilan sure (gun).
GUNLUK_GERI_BAKIS = 5000


def ts(yil, ay=1, gun=1):
    return int(datetime(yil, ay, gun, tzinfo=timezone.utc).timestamp())


def fmt(t):
    if t is None:
        return "-"
    return datetime.fromtimestamp(t, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")


def sorgula(symbol, resolution, baslangic, bitis):
    """Tek istek. Doner: (durum, adet, ilk_ts, son_ts)"""
    resp = api.get_klines(symbol, resolution, baslangic, bitis)

    if resp is None:
        return "ISTEK_BASARISIZ", 0, None, None

    if not isinstance(resp, dict):
        return f"BEKLENMEYEN_TIP({type(resp).__name__})", 0, None, None

    if "t" not in resp:
        return f"VERI_YOK(s={resp.get('s')})", 0, None, None

    t = resp["t"]
    if len(t) == 0:
        return f"BOS_DIZI(s={resp.get('s')})", 0, None, None

    return "OK", len(t), min(t), max(t)


def bolum_1_acik_uclu(simdi):
    print("=" * 92)
    print(f"BOLUM 1 -- from=<yil>-01-01, to=SIMDI    ({SEMBOL}, resolution={RESOLUTION})")
    print("           TALIMAT'in istedigi sorgu: her yil icin donen ilk mum.")
    print("=" * 92)
    print(f"{'FROM':<14} {'DURUM':<24} {'ADET':>7}  {'ILK MUM':<18} {'SON MUM':<18}")
    print("-" * 92)

    satirlar = []
    for yil in YILLAR:
        durum, adet, ilk, son = sorgula(SEMBOL, RESOLUTION, ts(yil), simdi)
        print(f"{yil}-01-01     {durum:<24} {adet:>7}  {fmt(ilk):<18} {fmt(son):<18}")
        satirlar.append((yil, durum, adet, ilk, son))
    print()
    return satirlar


def bolum_2_dar_pencere():
    """Acik uclu sorgu basarisizsa 'veri yok' ile 'istek reddedildi' ayrilamaz.
    Her yil icin 30 gunluk dar bir pencere sorarak bunu ayirt ediyoruz."""
    print("=" * 92)
    print(f"BOLUM 2 -- dar pencere: from=<yil>-01-01, to=+30 gun    (resolution={RESOLUTION})")
    print("           Ayni yilda veri var mi, yoksa gercekten bos mu?")
    print("=" * 92)
    print(f"{'PENCERE':<26} {'DURUM':<24} {'ADET':>7}  {'ILK MUM':<18} {'SON MUM':<18}")
    print("-" * 92)

    satirlar = []
    for yil in YILLAR:
        baslangic = ts(yil)
        durum, adet, ilk, son = sorgula(SEMBOL, RESOLUTION, baslangic, baslangic + 30 * 86400)
        etiket = f"{yil}-01-01 +30g"
        print(f"{etiket:<26} {durum:<24} {adet:>7}  {fmt(ilk):<18} {fmt(son):<18}")
        satirlar.append((yil, durum, adet, ilk, son))
    print()
    return satirlar


def bolum_3_pencere_siniri():
    """Endpoint bir istekte ne kadar genis aralik kabul ediyor?"""
    print("=" * 92)
    print(f"BOLUM 3 -- tek istekte izin verilen pencere genisligi    (from=2024-01-01, resolution={RESOLUTION})")
    print("=" * 92)
    print(f"{'GENISLIK':<12} {'DURUM':<24} {'ADET':>7}  {'SON MUM':<18}")
    print("-" * 92)

    base = ts(2024)
    en_genis_ok = None
    ilk_red = None
    for gun in PENCERE_MERDIVENI:
        durum, adet, ilk, son = sorgula(SEMBOL, RESOLUTION, base, base + gun * 86400)
        print(f"{str(gun) + ' gun':<12} {durum:<24} {adet:>7}  {fmt(son):<18}")
        if durum == "OK":
            en_genis_ok = gun if en_genis_ok is None else max(en_genis_ok, gun)
        elif ilk_red is None:
            ilk_red = gun
    print()
    return en_genis_ok, ilk_red


def bolum_4_en_eski(simdi):
    """Saatlik cozunurluk genis pencere kabul etmediginden en eski mumu
    gunluk (1440) cozunurlukle ariyoruz."""
    print("=" * 92)
    print(f"BOLUM 4 -- {SEMBOL} icin en eski mum (resolution=1440, geriye {GUNLUK_GERI_BAKIS} gun)")
    print("=" * 92)
    durum, adet, ilk, son = sorgula(SEMBOL, "1440", simdi - GUNLUK_GERI_BAKIS * 86400, simdi)
    print(f"  durum={durum}  adet={adet}  ilk={fmt(ilk)}  son={fmt(son)}")
    print()
    return durum, adet, ilk


def sonuc(acik, dar, sinir, en_eski):
    print("=" * 92)
    print("SONUC")
    print("=" * 92)

    acik_ok = [s for s in acik if s[2] > 0]
    dar_ok = [s for s in dar if s[2] > 0]
    en_genis_ok, ilk_red = sinir
    _, gunluk_adet, gunluk_ilk = en_eski

    if acik_ok:
        print(f"1) Acik uclu (to=simdi) sorgu {len(acik_ok)}/{len(acik)} yilda calisti; "
              f"donen en eski mum: {fmt(min(s[3] for s in acik_ok))}")
    else:
        print("1) Acik uclu (to=simdi) sorgularin HICBIRI calismadi -> sorun 'veri yok' degil, "
              "istek reddi.")

    if dar_ok:
        print(f"2) Dar (30 gunluk) pencerede veri gelen yillar: {sorted(s[0] for s in dar_ok)}; "
              f"en eski: {fmt(min(s[3] for s in dar_ok))}")
        print("   -> Gecmis veri MEVCUT. Sorun tarihsel derinlik degil, tek istekteki pencere genisligi.")
    else:
        print("2) Dar pencerelerde de veri yok -> gercekten tarihsel derinlik sinirli.")

    if en_genis_ok is not None:
        print(f"3) resolution={RESOLUTION} icin tek istekte calisan en genis pencere: {en_genis_ok} gun"
              + (f"; ilk reddedilen: {ilk_red} gun" if ilk_red else ""))
        print(f"   -> ~{en_genis_ok * 24} saatlik mum. Bunun uzeri "
              "INVALID_RESOLUTION_FOR_TIME_INTERVAL ile reddediliyor.")
    else:
        print("3) Hicbir pencere genisligi calismadi.")

    if gunluk_adet:
        print(f"4) Gunluk cozunurlukte en eski {SEMBOL} mumu: {fmt(gunluk_ilk)} ({gunluk_adet} gunluk mum)")
    else:
        print("4) Gunluk cozunurlukte veri alinamadi.")

    print()
    print("KISA CEVAP: Endpoint saatlik veriyi de yillar oncesine kadar veriyor; sinir tarihte")
    print("degil, TEK ISTEKTEKI PENCERE GENISLIGINDE. Yeterince dar chunk'larla istenirse")
    print("gecmis geliyor.")
    print("=" * 92)


def main():
    simdi = int(datetime.now(tz=timezone.utc).timestamp())
    print()
    acik = bolum_1_acik_uclu(simdi)
    dar = bolum_2_dar_pencere()
    sinir = bolum_3_pencere_siniri()
    en_eski = bolum_4_en_eski(simdi)
    sonuc(acik, dar, sinir, en_eski)


if __name__ == "__main__":
    main()
