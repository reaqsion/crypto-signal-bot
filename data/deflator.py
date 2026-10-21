"""USDTTRY deflatoru.

Proje TRY paritelerinde calisiyor. BTCTRY yukari egimli, cunku hem BTC
degerleniyor hem lira deger kaybediyor. Kur etkisi ayiklanmazsa her momentum
kurali yapay olarak iyi gorunur.

Onceki hali `api.get_klines(DEFLATOR_SYMBOL, "1440")` diyordu; tarih vermeyince
API varsayilan olarak son 30 gunu donuyordu ve tablo 30 satirda kaliyordu.
Artik istenen araligi chunk'layarak indiriyor ve hic veri gelmezse bagiriyor.
"""
from datetime import datetime, timedelta, timezone
from data.btcturk_api import api
from database import get_connection
from config import DEFLATOR_SYMBOL, INDIRME_START


class DeflatorHatasi(Exception):
    pass


# Gunluk cozunurlukte tek istekte guvenle alinabilen aralik.
# (Endpoint ~11.000 mum siniri koyuyor; gunlukte 5 yil rahat siginiyor.)
CHUNK_GUN = 365 * 5


def update_deflator(start_date=None, end_date=None):
    """Deflatoru [start_date, end_date] araliginda gunceller.

    start_date/end_date: "YYYY-MM-DD" ya da None (varsayilan: BACKTEST_START -> bugun)
    """
    if start_date is None:
        start_date = INDIRME_START
    baslangic = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)

    if end_date is None:
        bitis = datetime.now(tz=timezone.utc)
    else:
        bitis = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)

    if baslangic >= bitis:
        raise DeflatorHatasi(f"Gecersiz aralik: {start_date} -> {end_date}")

    conn = get_connection()
    c = conn.cursor()

    toplam = 0
    chunk_istendi = 0
    chunk_bos = 0
    chunk_hata = 0
    imlec = baslangic

    while imlec < bitis:
        chunk_bitis = min(imlec + timedelta(days=CHUNK_GUN), bitis)
        chunk_istendi += 1

        response = api.get_klines(
            DEFLATOR_SYMBOL, "1440",
            int(imlec.timestamp()), int(chunk_bitis.timestamp())
        )

        if response is None:
            chunk_hata += 1
            print(f"  ! deflator {imlec:%Y-%m-%d}..{chunk_bitis:%Y-%m-%d}: istek basarisiz")
        elif "t" not in response or len(response["t"]) == 0:
            chunk_bos += 1
        else:
            for i in range(len(response["t"])):
                tarih = datetime.fromtimestamp(response["t"][i], tz=timezone.utc).strftime("%Y-%m-%d")
                c.execute("""
                    INSERT OR REPLACE INTO deflator (date, usdtry_close)
                    VALUES (?, ?)
                """, (tarih, response["c"][i]))
            toplam += len(response["t"])

        imlec = chunk_bitis

    conn.commit()
    satir = c.execute("SELECT COUNT(*), MIN(date), MAX(date) FROM deflator").fetchone()
    conn.close()

    print(f"Deflator: {toplam} gun cekildi, {chunk_bos}/{chunk_istendi} chunk bos, "
          f"{chunk_hata}/{chunk_istendi} chunk hata")
    print(f"Deflator tablosu: {satir[0]} satir, {satir[1]} -> {satir[2]}")

    if toplam == 0:
        raise DeflatorHatasi(
            f"{DEFLATOR_SYMBOL} icin hic deflator verisi gelmedi "
            f"({start_date} -> {bitis:%Y-%m-%d}). Kur arindirmasi yapilamaz."
        )

    return toplam


def get_deflator(date_str):
    """O tarihteki USDTTRY kapanisi. Yoksa None (cagiran karar verir)."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT usdtry_close FROM deflator WHERE date = ?", (date_str,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None


def get_deflator_zorunlu(date_str):
    """O tarihteki USDTTRY kapanisi. Yoksa EXCEPTION -- sessizce sifir kabul etme."""
    deger = get_deflator(date_str)
    if deger is None:
        araligi = deflator_araligi()
        raise DeflatorHatasi(
            f"deflator tablosunda {date_str} yok. Mevcut aralik: {araligi[1]} -> {araligi[2]} "
            f"({araligi[0]} satir). Once `python -m data.deflator` ile araligi genislet."
        )
    return deger


def deflator_araligi():
    conn = get_connection()
    c = conn.cursor()
    row = c.execute("SELECT COUNT(*), MIN(date), MAX(date) FROM deflator").fetchone()
    conn.close()
    return row


def get_deflator_series(start_date, end_date):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT date, usdtry_close FROM deflator
        WHERE date BETWEEN ? AND ?
        ORDER BY date
    """, (start_date, end_date))
    rows = c.fetchall()
    conn.close()
    return {row[0]: row[1] for row in rows}


if __name__ == "__main__":
    update_deflator()
