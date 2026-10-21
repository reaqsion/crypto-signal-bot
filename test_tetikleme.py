"""TetiklemeDurumu birim testleri.

Calistir:  python test_tetikleme.py
"""
from datetime import datetime, timedelta
from sistem.tetikleme import TetiklemeDurumu, ARMED, FIRED

BASLANGIC = datetime(2026, 1, 1, 0, 0)
COOLDOWN = 24

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


def saat(n):
    return BASLANGIC + timedelta(hours=n)


def test_surekli_dogru_kosul_tek_sinyal():
    """TALIMAT Gorev 3.4: kosul 10 mum boyunca dogru kalirsa TEK sinyal."""
    m = TetiklemeDurumu(COOLDOWN)
    sonuclar = [m.degerlendir("BTCTRY|MOM_1W_5", True, saat(i)) for i in range(10)]
    kontrol("10 mum boyunca dogru kosul -> tek sinyal", 1, sum(sonuclar))
    kontrol("sinyal ilk mumda uretildi", True, sonuclar[0])


def test_cooldown_gecse_bile_kosul_dusmeden_atesleme_yok():
    """Eski hata: sadece sureye bakiliyordu. 40 saat dogru kalan kosul
    cooldown sonrasi tekrar atesliyordu. Artik atesememeli."""
    m = TetiklemeDurumu(COOLDOWN)
    sonuclar = [m.degerlendir("k", True, saat(i)) for i in range(100)]
    kontrol("100 saat kesintisiz dogru kosul -> hala tek sinyal", 1, sum(sonuclar))


def test_kosul_dustu_ama_cooldown_gecmedi():
    m = TetiklemeDurumu(COOLDOWN)
    m.degerlendir("k", True, saat(0))          # ates
    m.degerlendir("k", False, saat(1))         # kosul dustu, cooldown gecmedi
    tekrar = m.degerlendir("k", True, saat(2))  # cooldown dolmadan tekrar dogru
    kontrol("kosul dustu + cooldown gecmedi -> ikinci sinyal YOK", False, tekrar)


def test_kosul_dustu_ve_cooldown_gecti():
    m = TetiklemeDurumu(COOLDOWN)
    m.degerlendir("k", True, saat(0))
    m.degerlendir("k", False, saat(25))         # kosul yanlis + cooldown gecti -> ARMED
    kontrol("cooldown sonrasi kosul yanlis -> ARMED", ARMED, m.durum_al("k")[0])
    tekrar = m.degerlendir("k", True, saat(26))
    kontrol("ARMED'a donduktan sonra tekrar ateslenir", True, tekrar)


def test_anahtarlar_birbirini_etkilemez():
    m = TetiklemeDurumu(COOLDOWN)
    a = m.degerlendir("BTCTRY|MOM", True, saat(0))
    b = m.degerlendir("ETHTRY|MOM", True, saat(0))
    kontrol("farkli sembol-kural ciftleri bagimsiz", (True, True), (a, b))


def test_kosul_hic_saglanmazsa_sinyal_yok():
    m = TetiklemeDurumu(COOLDOWN)
    sonuclar = [m.degerlendir("k", False, saat(i)) for i in range(50)]
    kontrol("kosul hic dogru degilse sinyal yok", 0, sum(sonuclar))
    kontrol("durum ARMED kaliyor", ARMED, m.durum_al("k")[0])


def test_atesledikten_sonra_durum_fired():
    m = TetiklemeDurumu(COOLDOWN)
    m.degerlendir("k", True, saat(0))
    durum, son_ates = m.durum_al("k")
    kontrol("atesleme sonrasi durum FIRED", FIRED, durum)
    kontrol("last_fired atesleme anina esit", saat(0), son_ates)


def test_yanlis_tip_sessizce_gecmez():
    m = TetiklemeDurumu(COOLDOWN)
    try:
        m.degerlendir("k", True, 1767225600)  # datetime degil, epoch
        kontrol("epoch zaman TypeError firlatmali", "TypeError", "hata yok")
    except TypeError:
        kontrol("epoch zaman TypeError firlatmali", "TypeError", "TypeError")


def test_disaridan_durum_yukleme():
    """Canli taraf signal_state'ten durumu bu sekilde yukluyor."""
    m = TetiklemeDurumu(COOLDOWN)
    m.durum_yaz("k", FIRED, saat(0))
    kontrol("yuklenen FIRED durumu korunuyor -> atesleme yok",
            False, m.degerlendir("k", True, saat(1)))


if __name__ == "__main__":
    print("=== TetiklemeDurumu birim testleri ===")
    for ad, fn in sorted(globals().items()):
        if ad.startswith("test_") and callable(fn):
            print(f"\n{ad}")
            fn()
    print(f"\n{'=' * 50}")
    print(f"GECEN: {gecen}   KALAN: {kalan}")
    print("=" * 50)
    raise SystemExit(1 if kalan else 0)
