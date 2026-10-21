"""Saf tetikleme durum makinesi.

Veritabani bilmez, zaman bilmez, sembol bilmez. Tek isi: bir kosulun
surekli dogru kalmasi durumunda TEK sinyal uretilmesini saglamak.

Backtest bunu bellek icinde, canli taraf ayni sinifi signal_state tablosuyla
besleyerek kullanir. Iki taraf ayni kodu calistirdigi icin backtest sonucu
canliya tasinabilir olur.
"""
from datetime import datetime, timedelta

ARMED = "ARMED"
FIRED = "FIRED"


class TetiklemeDurumu:
    def __init__(self, cooldown_saat):
        if cooldown_saat is None:
            raise ValueError("cooldown_saat None olamaz. config.COOLDOWN_HOURS bekleniyor.")
        self.cooldown = timedelta(hours=cooldown_saat)
        self._durum = {}

    def durum_al(self, anahtar):
        """Doner: (status, last_fired). Hic gorulmemis anahtar icin (ARMED, None)."""
        return self._durum.get(anahtar, (ARMED, None))

    def durum_yaz(self, anahtar, status, last_fired):
        """Disaridan (orn. veritabanindan) durum yuklemek icin."""
        if status not in (ARMED, FIRED):
            raise ValueError(f"Gecersiz durum: {status!r}. ARMED ya da FIRED bekleniyor.")
        if last_fired is not None and not isinstance(last_fired, datetime):
            raise TypeError(f"last_fired datetime olmali, {type(last_fired).__name__} geldi.")
        self._durum[anahtar] = (status, last_fired)

    def degerlendir(self, anahtar, kosul_saglandi, zaman):
        """Bu anda sinyal uretilmeli mi?

        ARMED + kosul dogru            -> True dondur, FIRED'a gec.
        FIRED + kosul YANLIS + cooldown gecmis -> ARMED'a don (bu turda ateslemez).
        Diger her durum                -> False.

        Onceki kod sadece sureye bakiyordu; kosulun dustugunu kontrol etmiyordu.
        Bu yuzden surekli dogru kalan bir kosul cooldown basina bir kez daha
        atesliyordu. Artik kosulun once yanlisa donmesi sart.
        """
        if not isinstance(zaman, datetime):
            raise TypeError(
                f"zaman datetime olmali, {type(zaman).__name__} geldi. "
                "Backtest tarafinda open_time'i datetime'a cevir."
            )
        if not isinstance(kosul_saglandi, bool):
            raise TypeError(
                f"kosul_saglandi bool olmali, {type(kosul_saglandi).__name__} geldi."
            )

        status, last_fired = self.durum_al(anahtar)

        if status == ARMED:
            if kosul_saglandi:
                self._durum[anahtar] = (FIRED, zaman)
                return True
            return False

        # status == FIRED
        if kosul_saglandi:
            # Kosul hala dogru: yeniden atesleme yok, sure ne olursa olsun.
            return False

        if last_fired is None:
            raise RuntimeError(
                f"{anahtar!r} FIRED durumda ama last_fired yok. Durum bozuk."
            )

        if zaman - last_fired >= self.cooldown:
            self._durum[anahtar] = (ARMED, last_fired)

        return False
