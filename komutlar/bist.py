from telegram import Update
from telegram.ext import ContextTypes
from v2_bist import bist


async def bist_fiyat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Kullanim: /bist [sembol]\n"
            "Orn: /bist THYAO\n"
            "Endeks: /bist XU100"
        )
        return

    sembol = context.args[0].upper()

    if sembol == "XU100" or sembol == "BIST100":
        data = bist.get_bist100()
        if data:
            son = data.get("last", "N/A")
            degisim = data.get("dailyPercent", "N/A")
            acilis = data.get("open", "N/A")
            en_yuksek = data.get("high", "N/A")
            en_dusuk = data.get("low", "N/A")

            mesaj = f"""
BIST100 Endeksi

Son: {son}
Degisim: %{degisim}
Acilis: {acilis}
En Yuksek: {en_yuksek}
En Dusuk: {en_dusuk}
            """
            await update.message.reply_text(mesaj)
        else:
            await update.message.reply_text("BIST100 verisi alinamadi.")
        return

    data = bist.get_hisse(sembol)
    if not data:
        await update.message.reply_text(f"{sembol} icin veri alinamadi.")
        return

    son = data.get("last", "N/A")
    hacim = data.get("volume", "N/A")
    acilis = data.get("open", "N/A")
    en_yuksek = data.get("high", "N/A")
    en_dusuk = data.get("low", "N/A")

    mesaj = f"""
{sembol} Hisse Senedi

Son: {son} TL
Hacim: {hacim:,.0f}
Acilis: {acilis} TL
En Yuksek: {en_yuksek} TL
En Dusuk: {en_dusuk} TL
    """
    await update.message.reply_text(mesaj)


async def bist_liste(update: Update, context: ContextTypes.DEFAULT_TYPE):
    hisseler = ["THYAO", "AKBNK", "GARAN", "ASELS", "KCHOL", "SAHOL", "TUPRS", "EREGL", "BIMAS", "KCHOL"]

    mesaj = "BIST POPULER HISSELER\n\n"
    for symbol in hisseler:
        data = bist.get_hisse(symbol)
        if data:
            son = data.get("last", "N/A")
            mesaj += f"{symbol}: {son} TL\n"

    await update.message.reply_text(mesaj)
