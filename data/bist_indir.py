import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import pandas as pd
from datetime import datetime, timedelta
from v2_bist import bist
from database import get_connection
from config import BIST_TOP_30


def init_bist_tables():
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS bist_klines (
            symbol TEXT,
            open_time TIMESTAMP,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume REAL,
            PRIMARY KEY (symbol, open_time)
        )
    """)
    conn.commit()
    conn.close()


def download_bist_history(symbol, period="1y"):
    try:
        df = bist.get_gecmis(symbol, period)
        if df is None or df.empty:
            print(f"  {symbol}: Veri bulunamadi")
            return None
        
        df.columns = [col.lower() for col in df.columns]
        
        if 'date' in df.columns:
            df['open_time'] = pd.to_datetime(df['date'])
        elif 'datetime' in df.columns:
            df['open_time'] = pd.to_datetime(df['datetime'])
        else:
            df['open_time'] = df.index
            
        if not isinstance(df['open_time'], pd.DatetimeIndex):
            df['open_time'] = pd.to_datetime(df['open_time'])
        
        df['symbol'] = symbol
        
        print(f"  {symbol}: {len(df)} satir indirildi")
        return df
        
    except Exception as e:
        print(f"  {symbol}: Hata - {e}")
        return None


def save_bist_klines(df):
    if df is None or df.empty:
        return
    
    conn = get_connection()
    c = conn.cursor()
    
    for _, row in df.iterrows():
        try:
            c.execute("""
                INSERT OR REPLACE INTO bist_klines 
                (symbol, open_time, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                row['symbol'],
                row['open_time'].isoformat(),
                float(row.get('open', 0)),
                float(row.get('high', 0)),
                float(row.get('low', 0)),
                float(row.get('close', 0)),
                float(row.get('volume', 0))
            ))
        except Exception as e:
            print(f"Kayit hatasi: {e}")
            continue
    
    conn.commit()
    conn.close()


def download_all_bist():
    init_bist_tables()
    
    print(f"BIST top 30 hisse indiriliyor...")
    print(f"Hisse sayisi: {len(BIST_TOP_30)}")
    print()
    
    basari = 0
    hata = 0
    
    for i, symbol in enumerate(BIST_TOP_30, 1):
        print(f"[{i}/{len(BIST_TOP_30)}] {symbol} indiriliyor...")
        
        df = download_bist_history(symbol, "1y")
        
        if df is not None:
            save_bist_klines(df)
            basari += 1
        else:
            hata += 1
        
        time.sleep(1)
    
    print()
    print(f"Tamamlandi!")
    print(f"  Basarili: {basari}")
    print(f"  Hatali: {hata}")


def get_bist_stats():
    conn = get_connection()
    c = conn.cursor()
    
    c.execute("SELECT COUNT(DISTINCT symbol) FROM bist_klines")
    hisse_sayisi = c.fetchone()[0]
    
    c.execute("SELECT symbol, COUNT(*) as satir FROM bist_klines GROUP BY symbol")
    stats = c.fetchall()
    
    conn.close()
    
    print(f"BIST Veri Istatistikleri:")
    print(f"  Hisse sayisi: {hisse_sayisi}")
    for symbol, satir in stats:
        print(f"    {symbol}: {satir} satir")


if __name__ == "__main__":
    download_all_bist()
    print()
    get_bist_stats()
