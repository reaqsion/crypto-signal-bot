import time
from datetime import datetime, timezone
from data.btcturk_api import api
from data.sembol_dogrula import dogrula
from database import get_connection
from config import SYMBOLS, INDIRME_START, CHUNK_GUN


class IndirmeHatasi(Exception):
    """Bir sembol icin hic veri gelmedigi ya da indirme tamamen bos dondugu durum."""
    pass


def _ts_to_str(ts):
    if ts is None:
        return "-"
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")


def parse_klines(response):
    """API cevabini mum listesine cevirir.

    Donen: (klines, durum) - durum 'ok' | 'bos' | 'hata'
    'hata' = istek basarisiz (api None dondu) ya da cevap beklenen sekilde degil.
    'bos'  = istek basarili ama o aralikta mum yok.
    """
    if response is None:
        return [], "hata"

    if not isinstance(response, dict):
        raise IndirmeHatasi(f"Beklenmeyen klines cevap tipi: {type(response)!r}")

    if "t" not in response:
        # BtcTurk graph API veri olmayan araliklarda {'s': 'no_data'} donuyor.
        if response.get("s") in ("no_data", "ok"):
            return [], "bos"
        return [], "hata"

    n = len(response["t"])
    if n == 0:
        return [], "bos"

    for kolon in ("o", "h", "l", "c", "v"):
        if kolon not in response:
            raise IndirmeHatasi(
                f"klines cevabinda '{kolon}' kolonu yok. Gelen anahtarlar: {sorted(response.keys())}"
            )
        if len(response[kolon]) != n:
            raise IndirmeHatasi(
                f"klines cevabinda '{kolon}' uzunlugu ({len(response[kolon])}) "
                f"zaman dizisi uzunlugundan ({n}) farkli."
            )

    klines = []
    for i in range(n):
        klines.append({
            "open_time": response["t"][i],
            "open": response["o"][i],
            "high": response["h"][i],
            "low": response["l"][i],
            "close": response["c"][i],
            "volume": response["v"][i],
        })
    return klines, "ok"


def save_klines(symbol, resolution, klines):
    conn = get_connection()
    c = conn.cursor()
    for k in klines:
        c.execute("""
            INSERT OR IGNORE INTO klines (symbol, resolution, open_time, open, high, low, close, volume)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (symbol, resolution, k["open_time"], k["open"], k["high"], k["low"], k["close"], k["volume"]))
    conn.commit()
    conn.close()


def db_kapsam(symbol, resolution):
    """Veritabanindaki gercek durum: (satir_sayisi, ilk_ts, son_ts)."""
    conn = get_connection()
    c = conn.cursor()
    row = c.execute("""
        SELECT COUNT(*), MIN(open_time), MAX(open_time)
        FROM klines WHERE symbol = ? AND resolution = ?
    """, (symbol, resolution)).fetchone()
    conn.close()
    return row[0], row[1], row[2]


def download_symbol(symbol, resolution="60", start_date=None):
    if start_date is None:
        start_date = int(datetime.strptime(INDIRME_START, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())

    end_date = int(datetime.now(tz=timezone.utc).timestamp())
    current_start = start_date
    chunk_days = CHUNK_GUN

    chunk_istendi = 0
    chunk_bos = 0
    chunk_hata = 0
    total_saved = 0
    ilk_ts = None
    son_ts = None

    print(f"{symbol} indiriliyor (istenen baslangic: {_ts_to_str(start_date)})...")

    while current_start < end_date:
        current_end = current_start + (chunk_days * 24 * 3600)
        if current_end > end_date:
            current_end = end_date

        chunk_istendi += 1
        response = api.get_klines(symbol, resolution, current_start, current_end)
        klines, durum = parse_klines(response)

        if durum == "hata":
            chunk_hata += 1
            print(f"  ! {symbol} {_ts_to_str(current_start)}..{_ts_to_str(current_end)}: istek basarisiz")
        elif durum == "bos":
            chunk_bos += 1
        else:
            save_klines(symbol, resolution, klines)
            total_saved += len(klines)
            parca_ilk = min(k["open_time"] for k in klines)
            parca_son = max(k["open_time"] for k in klines)
            ilk_ts = parca_ilk if ilk_ts is None else min(ilk_ts, parca_ilk)
            son_ts = parca_son if son_ts is None else max(son_ts, parca_son)

        current_start = current_end
        time.sleep(0.5)

    print(
        f"{symbol}: {total_saved} mum, gercek aralik {_ts_to_str(ilk_ts)} -> {_ts_to_str(son_ts)}, "
        f"{chunk_bos}/{chunk_istendi} chunk bos, {chunk_hata}/{chunk_istendi} chunk hata"
    )

    if total_saved == 0:
        raise IndirmeHatasi(
            f"{symbol} icin hic mum gelmedi. "
            f"{chunk_istendi} chunk istendi, {chunk_bos} bos dondu, {chunk_hata} hata verdi. "
            f"Istenen aralik: {_ts_to_str(start_date)} -> {_ts_to_str(end_date)}, resolution={resolution}. "
            f"Sembol borsada olmayabilir ya da endpoint bu araligi vermiyor olabilir."
        )

    return {
        "symbol": symbol,
        "kaydedilen": total_saved,
        "ilk_ts": ilk_ts,
        "son_ts": son_ts,
        "chunk_istendi": chunk_istendi,
        "chunk_bos": chunk_bos,
        "chunk_hata": chunk_hata,
    }


def download_all(resolution="60", semboller=None):
    if semboller is None:
        # Borsada olmayan sembol icin bos veri toplamak yerine once dogrula.
        semboller, _ = dogrula(SYMBOLS)

    sonuclar = []
    hatalar = []

    for symbol in semboller:
        try:
            sonuclar.append(download_symbol(symbol, resolution))
        except IndirmeHatasi as e:
            # Sessizce gecmiyoruz: kaydediyoruz, ozet tablodan sonra topluca firlatiyoruz.
            hatalar.append((symbol, str(e)))
            print(f"  !! {symbol} BASARISIZ: {e}")

    print()
    print("=" * 78)
    print("OZET (veritabanindaki gercek durum)")
    print("=" * 78)
    print(f"{'SEMBOL':<10} {'SATIR':>8}  {'ILK':<12} {'SON':<12}  {'BU KOSUDA':>10}")
    print("-" * 78)

    toplam_satir = 0
    for symbol in semboller:
        n, mn, mx = db_kapsam(symbol, resolution)
        toplam_satir += n
        bu_kosu = next((s["kaydedilen"] for s in sonuclar if s["symbol"] == symbol), 0)
        print(f"{symbol:<10} {n:>8}  {_ts_to_str(mn):<12} {_ts_to_str(mx):<12}  {bu_kosu:>10}")

    print("-" * 78)
    print(f"{'TOPLAM':<10} {toplam_satir:>8}")
    print(f"Basarili sembol: {len(sonuclar)}/{len(semboller)}, basarisiz: {len(hatalar)}")
    print("=" * 78)

    if hatalar:
        detay = "; ".join(f"{s}: {m}" for s, m in hatalar)
        raise IndirmeHatasi(f"{len(hatalar)} sembol icin hic veri gelmedi -> {detay}")

    return toplam_satir


if __name__ == "__main__":
    download_all()
