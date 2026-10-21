from telegram import Update
from telegram.ext import ContextTypes
from database import get_connection


async def son_sinyaller(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT timestamp, symbol, rule_name, direction, price, market_wide
        FROM signal_log
        ORDER BY id DESC
        LIMIT 10
    """)
    sinyaller = c.fetchall()
    conn.close()

    if not sinyaller:
        await update.message.reply_text("Henuz sinyal yok.")
        return

    mesaj = "📡 SON 10 SINYAL\n\n"
    for s in sinyaller:
        zaman, sembol, kural, yon, fiyat, market = s
        market_etiket = " [Piyasa]" if market else ""
        mesaj += f"{zaman[:16]}\n"
        mesaj += f"  {sembol} | {kural} | {yon}\n"
        mesaj += f"  Fiyat: {fiyat:,.2f} TL{market_etiket}\n\n"

    await update.message.reply_text(mesaj)
