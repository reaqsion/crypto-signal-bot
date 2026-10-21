"""Abone (sinyal hedefi) testleri -- gecici veritabaninda.

Bug'in regresyonu: canli tarama job'i chat_id olmadan kaydedilmisti, uretilen
sinyal Telegram'a HIC gonderilmiyordu.

Calistir:  python test_abone.py
"""
import os
import tempfile

import database

_gecici = os.path.join(tempfile.mkdtemp(prefix="kriptobot_abone_"), "test.db")
database.DB_PATH = _gecici

from sistem.abone import abone_ekle, abone_cikar, aktif_aboneler  # noqa: E402

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


if __name__ == "__main__":
    print("=== Abone testleri ===")
    database.init_db()

    kontrol("baslangicta abone yok", [], aktif_aboneler())

    abone_ekle(12345, "test_user")
    kontrol("abone eklendi", [12345], aktif_aboneler())

    abone_ekle(12345, "test_user")
    kontrol("ayni chat_id kopya satir acmiyor", [12345], aktif_aboneler())

    abone_ekle(67890, "ikinci")
    kontrol("ikinci abone eklendi", [12345, 67890], sorted(aktif_aboneler()))

    abone_cikar(12345)
    kontrol("cikarilan abone listede yok", [67890], aktif_aboneler())

    abone_ekle(12345, "test_user")
    kontrol("cikarilan abone tekrar eklenebiliyor", [12345, 67890], sorted(aktif_aboneler()))

    print(f"\n{'=' * 50}")
    print(f"GECEN: {gecen}   KALAN: {kalan}")
    print("=" * 50)
    raise SystemExit(1 if kalan else 0)
