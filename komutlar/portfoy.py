from telegram import Update
from telegram.ext import ContextTypes
from datetime import datetime
from database import get_connection
from data.btcturk_api import api


async def portfoy_ekle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 3:
        await update.message.reply_text(
            "Kullanim: /portfoy_ekle [sembol] [miktar] [alis_fiyati]\n"
            "Orn: /portfoy_ekle BTC 0.001 3200000"
        )
        return

    sembol = context.args[0].upper()
    if not sembol.endswith("TRY"):
        sembol = sembol + "TRY"

    try:
        miktar = float(context.args[1])
        alis_fiyati = float(context.args[2])
    except ValueError:
        await update.message.reply_text("Gecersiz deger.")
        return

    user_id = update.effective_user.id
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO portfoy (user_id, symbol, miktar, alis_fiyati, ekleme_tarihi)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, sembol, miktar, alis_fiyati, datetime.now().isoformat()))
    conn.commit()
    conn.close()

    toplam = miktar * alis_fiyati
    await update.message.reply_text(
        f"Portfoye eklendi!\n"
        f"sembol: {sembol}\n"
        f"Miktar: {miktar}\n"
        f"Alis: {alis_fiyati:,.2f} TL\n"
        f"Toplam: {toplam:,.2f} TL"
    )


async def portfoy_goster(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT symbol, miktar, alis_fiyati
        FROM portfoy
        WHERE user_id = ?
    """, (user_id,))
    pozisyonlar = c.fetchall()
    conn.close()

    if not pozisyonlar:
        await update.message.reply_text("Portfoy bos.")
        return

    mesaj = "💰 PORTFOY\n\n"
    toplam_deger = 0
    toplam_maliyet = 0

    for poz in pozisyonlar:
        sembol, miktar, alis = poz
        data = api.get_symbol_ticker(sembol)
        guncel_fiyat = float(data.get("last", 0)) if data else 0

        deger = miktar * guncel_fiyat
        maliyet = miktar * alis
        kar_zarar = deger - maliyet
        yuzde = (kar_zarar / maliyet * 100) if maliyet > 0 else 0

        toplam_deger += deger
        toplam_maliyet += maliyet

        durum = "🟢" if kar_zarar >= 0 else "🔴"
        mesaj += f"{durum} {sembol}\n"
        mesaj += f"  Miktar: {miktar}\n"
        mesaj += f"  Guncel: {guncel_fiyat:,.2f} TL\n"
        mesaj += f"  Deger: {deger:,.2f} TL\n"
        mesaj += f"  K/Z: {kar_zarar:,.2f} TL (%{yuzde:.2f})\n\n"

    toplam_kz = toplam_deger - toplam_maliyet
    toplam_yuzde = (toplam_kz / toplam_maliyet * 100) if toplam_maliyet > 0 else 0

    mesaj += f"--- TOPLAM ---\n"
    mesaj += f"Deger: {toplam_deger:,.2f} TL\n"
    mesaj += f"K/Z: {toplam_kz:,.2f} TL (%{toplam_yuzde:.2f})"

    await update.message.reply_text(mesaj)


async def portfoy_sil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Kullanim: /portfoy_sil [sembol]")
        return

    sembol = context.args[0].upper()
    if not sembol.endswith("TRY"):
        sembol = sembol + "TRY"

    user_id = update.effective_user.id
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        DELETE FROM portfoy
        WHERE user_id = ? AND symbol = ?
    """, (user_id, sembol))
    conn.commit()
    conn.close()

    await update.message.reply_text(f"{sembol} portfoyden silindi.")
