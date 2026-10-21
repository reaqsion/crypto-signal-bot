import sqlite3
from config import DB_PATH


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS klines (
            symbol TEXT,
            resolution TEXT,
            open_time INTEGER,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume REAL,
            UNIQUE(symbol, resolution, open_time)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS signal_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            symbol TEXT,
            rule_name TEXT,
            direction TEXT,
            price REAL,
            btc_price REAL,
            ret_30d_prior REAL,
            market_wide BOOLEAN,
            source TEXT DEFAULT 'backtest',
            forward_1d REAL,
            forward_7d REAL,
            forward_30d REAL,
            btc_forward_7d REAL,
            usdtry_forward_7d REAL,
            run_id TEXT,
            suppressed INTEGER DEFAULT 0
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS signal_controls (
            signal_id INTEGER PRIMARY KEY,
            price_1d REAL,
            price_7d REAL,
            price_30d REAL,
            btc_price_1d REAL,
            btc_price_7d REAL,
            btc_price_30d REAL,
            usdtry_price_1d REAL,
            usdtry_price_7d REAL,
            usdtry_price_30d REAL,
            checked_at TEXT,
            FOREIGN KEY(signal_id) REFERENCES signal_log(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS alarms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            symbol TEXT,
            direction TEXT,
            target_price REAL,
            active BOOLEAN DEFAULT 1,
            created_at TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS signal_state (
            symbol TEXT,
            rule_name TEXT,
            status TEXT DEFAULT 'ARMED',
            last_fired TEXT,
            UNIQUE(symbol, rule_name)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS daily_snapshot (
            date TEXT,
            symbol TEXT,
            data TEXT,
            UNIQUE(date, symbol)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS abone (
            chat_id INTEGER PRIMARY KEY,
            kullanici TEXT,
            kayit_at TEXT,
            aktif INTEGER DEFAULT 1
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS tarama_durumu (
            symbol TEXT,
            resolution TEXT,
            son_islenen_open_time INTEGER,
            guncellendi_at TEXT,
            UNIQUE(symbol, resolution)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS deflator (
            date TEXT PRIMARY KEY,
            usdtry_close REAL
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS portfoy (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            symbol TEXT,
            miktar REAL,
            alis_fiyati REAL,
            ekleme_tarihi TEXT
        )
    """)

    conn.commit()
    conn.close()

    # Mevcut veritabanlari icin sema guncellemeleri. Yeni kurulumda hepsi
    # zaten CREATE TABLE'da var; migrasyon kayit tutup atliyor.
    from migrasyon import migrasyonlari_uygula
    migrasyonlari_uygula(sessiz=True)


if __name__ == "__main__":
    init_db()
    print("Veritabanı oluşturuldu.")
