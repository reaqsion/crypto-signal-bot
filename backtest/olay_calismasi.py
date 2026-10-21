import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from datetime import datetime, timedelta
from database import get_connection
from kurallar.motor import get_all_rules, get_bist_rules
from sistem.tetikleme import TetiklemeDurumu
from data.deflator import get_deflator
from config import ROUND_TRIP_COST, COOLDOWN_HOURS, BACKTEST_START, BACKTEST_END


def _tarih_ts(tarih_str):
    return int(datetime.strptime(tarih_str, "%Y-%m-%d").timestamp())


def load_klines(symbol, resolution="60", baslangic=None, bitis=None):
    """Mumlari okur. Varsayilan aralik config.BACKTEST_START..BACKTEST_END.

    Bu filtre onceden YOKTU: config'de tarihler duruyordu ama backtest
    tabloda ne varsa hepsini okuyordu. Onemli, cunku deflator (USDTTRY)
    2018-07-10'dan once yok; o donemin sinyalleri kur arindirmasi
    yapilamadigi icin metrik tarafinda exception'a sebep oluyordu.

    baslangic/bitis: "YYYY-MM-DD" ya da None. Tum tabloyu istiyorsan
    acikca baslangic="1970-01-01" ver.
    """
    bas_ts = _tarih_ts(baslangic or BACKTEST_START)
    bit_ts = _tarih_ts(bitis or BACKTEST_END)

    conn = get_connection()
    query = """
        SELECT open_time, open, high, low, close, volume
        FROM klines
        WHERE symbol = ? AND resolution = ?
          AND open_time >= ? AND open_time <= ?
        ORDER BY open_time
    """
    df = pd.read_sql_query(query, conn, params=(symbol, resolution, bas_ts, bit_ts))
    conn.close()
    return df.reset_index(drop=True)


def load_bist_klines(symbol):
    conn = get_connection()
    query = """
        SELECT open_time, open, high, low, close, volume
        FROM bist_klines
        WHERE symbol = ?
        ORDER BY open_time
    """
    df = pd.read_sql_query(query, conn, params=(symbol,))
    conn.close()
    return df


def run_event_study(symbol, rules=None, resolution="60"):
    if rules is None:
        rules = get_all_rules()

    df = load_klines(symbol, resolution)
    if df.empty:
        return []

    events = []
    btc_df = load_klines("BTCTRY", resolution)

    # Canli tarafla AYNI durum makinesi. Kosul 40 saat dogru kalirsa 40 degil
    # 1 sinyal uretilir. Kural basina bir ornek, mumlar uzerinde sirayla.
    makine = TetiklemeDurumu(COOLDOWN_HOURS)

    for rule in rules:
        lookback = rule.get_required_lookback()
        anahtar = f"{symbol}|{rule.name}"
        for i in range(lookback, len(df)):
            kosul = bool(rule.evaluate(df, i))
            zaman = datetime.fromtimestamp(df.iloc[i]['open_time'])
            if makine.degerlendir(anahtar, kosul, zaman):
                event = {
                    "timestamp": df.iloc[i]['open_time'],
                    "symbol": symbol,
                    "rule_name": rule.name,
                    "direction": rule.direction,
                    "price": df.iloc[i]['close'],
                    "btc_price": get_btc_price(btc_df, df.iloc[i]['open_time']),
                    "ret_30d_prior": calc_prior_return(df, i, 30*24),
                    "market_wide": check_market_wide(btc_df, df.iloc[i]['open_time']),
                    "forward_1d": calc_forward_return(df, i, 24),
                    "forward_7d": calc_forward_return(df, i, 24*7),
                    "forward_30d": calc_forward_return(df, i, 24*30),
                    "btc_forward_7d": btc_forward_return(btc_df, df.iloc[i]['open_time'], 24*7),
                    "usdtry_forward_7d": usdtry_forward_return(df.iloc[i]['open_time'], 7),
                }
                events.append(event)

    return events


def run_bist_event_study(symbol, rules=None):
    if rules is None:
        rules = get_bist_rules()

    df = load_bist_klines(symbol)
    if df.empty:
        return []

    events = []
    makine = TetiklemeDurumu(COOLDOWN_HOURS)

    for rule in rules:
        lookback = rule.get_required_lookback()
        anahtar = f"{symbol}|{rule.name}"
        for i in range(lookback, len(df)):
            kosul = bool(rule.evaluate(df, i))
            zaman = _bist_zaman(df.iloc[i]['open_time'])
            if makine.degerlendir(anahtar, kosul, zaman):
                event = {
                    "timestamp": df.iloc[i]['open_time'],
                    "symbol": symbol,
                    "rule_name": rule.name,
                    "direction": rule.direction,
                    "price": df.iloc[i]['close'],
                    "ret_30d_prior": calc_prior_return(df, i, 30*8),
                    "forward_1d": calc_forward_return(df, i, 8),
                    "forward_7d": calc_forward_return(df, i, 5*8),
                    "forward_30d": calc_forward_return(df, i, 20*8),
                }
                events.append(event)

    return events


def _bist_zaman(open_time):
    """bist_klines.open_time tipi tek yerden datetime'a cevrilir."""
    if isinstance(open_time, datetime):
        return open_time
    if isinstance(open_time, (int, float)):
        return datetime.fromtimestamp(open_time)
    if isinstance(open_time, str):
        return datetime.fromisoformat(open_time)
    raise TypeError(f"bist open_time icin beklenmeyen tip: {type(open_time).__name__}")


def index_at_or_before(df, timestamp):
    """timestamp'ten SONRAKI mumu asla secmeyen indeks.

    Eski hali `(df['open_time'] - timestamp).abs().idxmin()` idi: en yakin mumu
    seciyordu, bu bazen sinyal anindan sonraki mum oluyordu -- gelecege bakma.
    Uygun mum yoksa None doner; bu mesru bir durum (veri baslangici).
    """
    if df.empty:
        return None
    uygun = df.index[df['open_time'] <= timestamp]
    if len(uygun) == 0:
        return None
    return uygun[-1]


def get_btc_price(btc_df, timestamp):
    idx = index_at_or_before(btc_df, timestamp)
    if idx is None:
        return None
    return btc_df.loc[idx, 'close']


def btc_forward_return(btc_df, timestamp, periods):
    """BTC'nin sinyal anindan itibaren `periods` mum sonraki getirisi (%).
    Gorev 5'in piyasa arindirmasi icin gerekli."""
    idx = index_at_or_before(btc_df, timestamp)
    if idx is None:
        return None
    return calc_forward_return(btc_df, btc_df.index.get_loc(idx), periods)


def usdtry_forward_return(timestamp, gun):
    """USDTTRY'nin sinyal gununden `gun` gun sonraki getirisi (%).
    Gorev 5'in kur (enflasyon) arindirmasi icin gerekli.
    Deflator o tarihleri kapsamiyorsa None doner -- metrik tarafi bunu
    sessizce sifir saymayip exception firlatiyor."""
    t0 = datetime.fromtimestamp(timestamp)
    bugun = get_deflator(t0.strftime("%Y-%m-%d"))
    sonra = get_deflator((t0 + timedelta(days=gun)).strftime("%Y-%m-%d"))
    if bugun is None or sonra is None or bugun <= 0:
        return None
    return (sonra - bugun) / bugun * 100


def calc_prior_return(df, idx, periods):
    if idx < periods:
        return None
    current = df.iloc[idx]['close']
    past = df.iloc[idx - periods]['close']
    if past <= 0:
        return None
    return (current - past) / past * 100


def calc_forward_return(df, idx, periods):
    if idx + periods >= len(df):
        return None
    current = df.iloc[idx]['close']
    future = df.iloc[idx + periods]['close']
    if current <= 0:
        return None
    return (future - current) / current * 100


def check_market_wide(btc_df, timestamp, threshold=5):
    idx = index_at_or_before(btc_df, timestamp)
    if idx is None:
        return False
    konum = btc_df.index.get_loc(idx)
    if konum < 24:
        return False
    current = btc_df.iloc[konum]['close']
    past = btc_df.iloc[konum - 24]['close']
    if past <= 0:
        return False
    change = abs(current - past) / past * 100
    return change > threshold


def yeni_run_id():
    """Her backtest kosusu kendi kimligiyle yazilir. Duzeltme oncesi 32k satir
    silinmedi; metrikler run_id ile son kosuyu okuyor."""
    return datetime.now().strftime("%Y%m%dT%H%M%S")


def save_events(events, run_id=None):
    if run_id is None:
        run_id = yeni_run_id()

    zorunlu = ("timestamp", "symbol", "rule_name", "direction", "price")
    conn = get_connection()
    c = conn.cursor()
    for e in events:
        eksik = [k for k in zorunlu if k not in e]
        if eksik:
            conn.close()
            raise KeyError(f"Olay kaydinda zorunlu alan eksik: {eksik} -> {e}")
        c.execute("""
            INSERT INTO signal_log (
                timestamp, symbol, rule_name, direction, price, btc_price,
                ret_30d_prior, market_wide, source,
                forward_1d, forward_7d, forward_30d,
                btc_forward_7d, usdtry_forward_7d, run_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'backtest', ?, ?, ?, ?, ?, ?)
        """, (
            datetime.fromtimestamp(e['timestamp']).isoformat(),
            e['symbol'],
            e['rule_name'],
            e['direction'],
            e['price'],
            e.get('btc_price'),
            e.get('ret_30d_prior'),
            e.get('market_wide', False),
            e.get('forward_1d'),
            e.get('forward_7d'),
            e.get('forward_30d'),
            e.get('btc_forward_7d'),
            e.get('usdtry_forward_7d'),
            run_id,
        ))
    conn.commit()
    conn.close()
    print(f"{len(events)} olay signal_log'a yazildi (run_id={run_id})")
    return run_id


def save_bist_events(events):
    conn = get_connection()
    c = conn.cursor()
    for e in events:
        c.execute("""
            INSERT INTO signal_log (timestamp, symbol, rule_name, direction, price, source)
            VALUES (?, ?, ?, ?, ?, 'bist')
        """, (
            e['timestamp'].isoformat() if hasattr(e['timestamp'], 'isoformat') else str(e['timestamp']),
            e['symbol'],
            e['rule_name'],
            e['direction'],
            e['price']
        ))
    conn.commit()
    conn.close()


if __name__ == "__main__":
    # GOREV 10.1: v1 akisi SADECE kripto. get_bist_rules / run_bist_event_study
    # duruyor ama buradan cagrilmiyor -- deneme sayisini sabit tutmak icin.
    # BIST'i calistirmak istersen fonksiyonlari elle cagir.
    from data.sembol_dogrula import dogrula
    from config import SYMBOLS
    from kurallar.motor import get_all_rules as _kurallar

    print("=== KRIPTO BACKTEST ===")
    print(f"Deneme sayisi (kural x tutma): {len(_kurallar()) * 3}")

    semboller, eksik = dogrula(SYMBOLS)
    run_id = yeni_run_id()

    all_events = []
    for symbol in semboller:
        events = run_event_study(symbol)
        all_events.extend(events)
        print(f"  {symbol}: {len(events)} sinyal")

    if not all_events:
        raise RuntimeError(
            "Hicbir sembolde sinyal uretilmedi. klines tablosu bos olabilir: "
            "once python scripts/tam_indir.py"
        )

    save_events(all_events, run_id)
    print(f"Toplam {len(all_events)} kripto sinyal kaydedildi (run_id={run_id}).")
