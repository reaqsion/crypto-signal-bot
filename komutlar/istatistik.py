from telegram import Update
from telegram.ext import ContextTypes
from database import get_connection
from config import ROUND_TRIP_COST


async def bot_istatistik(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = get_connection()
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM signal_log")
    toplam_sinyal = c.fetchone()[0]

    c.execute("SELECT COUNT(DISTINCT symbol) FROM signal_log")
    sembol_sayisi = c.fetchone()[0]

    c.execute("SELECT COUNT(DISTINCT rule_name) FROM signal_log")
    kural_sayisi = c.fetchone()[0]

    c.execute("""
        SELECT COUNT(*) FROM signal_log
        WHERE timestamp > datetime('now', '-7 days')
    """)
    son_7gun = c.fetchone()[0]

    c.execute("""
        SELECT COUNT(*) FROM signal_log
        WHERE timestamp > datetime('now', '-30 days')
    """)
    son_30gun = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM alarms WHERE active = 1")
    aktif_alarm = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM portfoy")
    portfoy_pozisyon = c.fetchone()[0]

    conn.close()

    mesaj = f"""
📊 BOT ISTATISTIKLERI

Toplam Sinyal: {toplam_sinyal}
Izlenen Sembol: {sembol_sayisi}
Aktif Kural: {kural_sayisi}

Son 7 Gun: {son_7gun} sinyal
Son 30 Gun: {son_30gun} sinyal

Aktif Alarm: {aktif_alarm}
Portfoy Pozisyonu: {portfoy_pozisyon}

Maliyet Orani: %{ROUND_TRIP_COST * 100:.2f} (gidis-donus)
    """
    await update.message.reply_text(mesaj)
