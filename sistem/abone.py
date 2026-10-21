"""Canli sinyalin gonderilecegi sohbetler.

/basla calistiran her sohbet buraya kaydedilir. Canli tarama job'i
uretilen mesaji buradaki her aktif chat_id'ye gonderir.

Neden ayri bir tablo: job_queue.run_repeating chat_id tasimiyordu, bu yuzden
uretilen sinyaller signal_log'a yazilip Telegram'a hic gonderilmiyordu.
"""
from datetime import datetime
from database import get_connection


def abone_ekle(chat_id, kullanici=None):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO abone (chat_id, kullanici, kayit_at, aktif)
        VALUES (?, ?, ?, 1)
        ON CONFLICT(chat_id) DO UPDATE SET aktif = 1, kullanici = excluded.kullanici
    """, (int(chat_id), kullanici, datetime.now().isoformat()))
    conn.commit()
    conn.close()


def abone_cikar(chat_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE abone SET aktif = 0 WHERE chat_id = ?", (int(chat_id),))
    conn.commit()
    conn.close()


def aktif_aboneler():
    conn = get_connection()
    c = conn.cursor()
    rows = c.execute("SELECT chat_id FROM abone WHERE aktif = 1").fetchall()
    conn.close()
    return [r[0] for r in rows]


if __name__ == "__main__":
    print("Aktif aboneler:", aktif_aboneler())
