"""Gunluk borsa anlik goruntusu.

BtcTurk gecmis sembol listesi vermiyor. "2025'te hangi pariteler islem
goruyordu" sorusu bugun cevaplanamaz. Bugunden itibaren kaydedersek bir yil
sonra gercek bir tarihsel liste olacak. Her gecen gun geri kazanilamaz kayip.

daily_snapshot tablosu olusturulmustu ama hicbir sey yazmiyordu.
"""
import json
from datetime import datetime

from database import get_connection
from data.btcturk_api import api

# exchangeinfo blob'unun sembol alanina yazildigi ozel anahtar.
EXCHANGEINFO_ANAHTARI = "__exchangeinfo__"


class SnapshotHatasi(Exception):
    pass


def snapshot_al(tarih=None):
    """exchangeinfo + tum ticker ciktisini ham JSON olarak yazar.

    Ayni gun ikinci kez calisirsa UNIQUE(date, symbol) sayesinde uzerine
    yazar, kopya satir acmaz.
    """
    if tarih is None:
        tarih = datetime.now().strftime("%Y-%m-%d")

    info = api.get_exchange_info()
    if not info or "data" not in info:
        raise SnapshotHatasi("exchangeinfo alinamadi, snapshot yazilmadi.")

    tickers = api.get_all_tickers()
    if not tickers or "data" not in tickers:
        raise SnapshotHatasi("ticker listesi alinamadi, snapshot yazilmadi.")

    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        INSERT OR REPLACE INTO daily_snapshot (date, symbol, data)
        VALUES (?, ?, ?)
    """, (tarih, EXCHANGEINFO_ANAHTARI, json.dumps(info["data"], ensure_ascii=False)))

    yazilan = 0
    for t in tickers["data"]:
        pair = t.get("pair")
        if not pair:
            raise SnapshotHatasi(f"ticker kaydinda 'pair' yok: {sorted(t.keys())}")
        c.execute("""
            INSERT OR REPLACE INTO daily_snapshot (date, symbol, data)
            VALUES (?, ?, ?)
        """, (tarih, pair, json.dumps(t, ensure_ascii=False)))
        yazilan += 1

    conn.commit()
    toplam = c.execute("SELECT COUNT(*) FROM daily_snapshot WHERE date = ?", (tarih,)).fetchone()[0]
    conn.close()

    print(f"  Snapshot {tarih}: {yazilan} ticker + 1 exchangeinfo yazildi "
          f"(tabloda o gune ait {toplam} satir).")
    return {"tarih": tarih, "ticker": yazilan, "satir": toplam}


def snapshot_gunleri():
    conn = get_connection()
    c = conn.cursor()
    rows = c.execute("""
        SELECT date, COUNT(*) FROM daily_snapshot GROUP BY date ORDER BY date
    """).fetchall()
    conn.close()
    return [(r[0], r[1]) for r in rows]


if __name__ == "__main__":
    print("=== GUNLUK SNAPSHOT ===")
    snapshot_al()
    print("Kayitli gunler:")
    for gun, n in snapshot_gunleri():
        print(f"  {gun}: {n} satir")
