"""Tum gecerli sembolleri + deflator sembolunu BACKTEST_START'tan itibaren indirir.

Kullanim:  python scripts/tam_indir.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.sembol_dogrula import dogrula  # noqa: E402
from data.veri_indir import download_all, download_symbol, IndirmeHatasi  # noqa: E402
from data.deflator import update_deflator  # noqa: E402
from config import SYMBOLS, DEFLATOR_SYMBOL  # noqa: E402

if __name__ == "__main__":
    print("=== SEMBOL DOGRULAMA ===")
    gecerli, eksik = dogrula(SYMBOLS)

    # DEFLATOR_SYMBOL kontrol job'i icin klines tablosunda da lazim.
    hedefler = list(gecerli)
    if DEFLATOR_SYMBOL not in hedefler:
        hedefler.append(DEFLATOR_SYMBOL)

    print(f"\n=== KLINES INDIRME ({len(hedefler)} sembol) ===")
    try:
        download_all(semboller=hedefler)
    except IndirmeHatasi as e:
        print(f"\nBAZI SEMBOLLER BASARISIZ: {e}")

    print("\n=== DEFLATOR ===")
    update_deflator()
