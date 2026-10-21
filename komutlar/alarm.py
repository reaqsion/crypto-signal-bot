from telegram import Update
from telegram.ext import ContextTypes
from datetime import datetime
from database import get_connection
from data.btcturk_api import api


async def alarm_kur(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 3:
        await update.message.reply_text(
            "Kullanim: /alarm_kur [sembol] [yukari/asagi] [fiyat]\n"
            "Orn: /alarm_kur BTC yukari 3500000"
        )
        return

    sembol = context.args[0].upper()
    if not sembol.endswith("TRY"):
        sembol = sembol + "TRY"

    yon = context.args[1].lower()
    if yon not in ["yukari", "asagi"]:
        await update.message.reply_text("Yon 'yukari' veya 'asagi' olmali.")
        return

    try:
        hedef_fiyat = float(context.args[2].replace(",", ""))
    except ValueError:
        await update.message.reply_text("Gecersiz fiyat degeri.")
        return

    user_id = update.effective_user.id
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO alarms (user_id, symbol, direction, target_price, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, sembol, yon, hedef_fiyat, datetime.now().isoformat()))
    conn.commit()
    conn.close()

    await update.message.reply_text(
        f"Alarm kuruldu!\n"
        f"sembol: {sembol}\n"
        f"Yon: {yon}\n"
        f"Hedef: {hedef_fiyat:,.2f} TL"
    )


async def alarm_listesi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT id, symbol, direction, target_price, active
        FROM alarms
        WHERE user_id = ? AND active = 1
    """, (user_id,))
    alarmlar = c.fetchall()
    conn.close()

    if not alarmlar:
        await update.message.reply_text("Aktif alarm yok.")
        return

    mesaj = "🔔 ALARM LISTESI\n\n"
    for alarm in alarmlar:
        mesaj += f"ID: {alarm[0]} | {alarm[1]} | {alarm[2]} | {alarm[3]:,.2f} TL\n"

    await update.message.reply_text(mesaj)


async def alarm_sil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Kullanim: /alarm_sil [id]")
        return

    try:
        alarm_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Gecersiz ID.")
        return

    user_id = update.effective_user.id
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        UPDATE alarms SET active = 0
        WHERE id = ? AND user_id = ?
    """, (alarm_id, user_id))
    conn.commit()
    conn.close()

    await update.message.reply_text(f"Alarm {alarm_id} silindi.")
