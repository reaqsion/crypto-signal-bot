from telegram import Update
from telegram.ext import ContextTypes
from data.btcturk_api import api


async def fiyat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Kullanim: /fiyat [sembol]\nOrn: /fiyat BTC")
        return

    sembol = context.args[0].upper()
    if not sembol.endswith("TRY"):
        sembol = sembol + "TRY"

    data = api.get_symbol_ticker(sembol)
    if not data:
        await update.message.reply_text(f"{sembol} icin veri alinamadi.")
        return

    fiyat = float(data.get("last", 0))
    degisim = float(data.get("dailyPercent", 0))
    hacim = float(data.get("volume", 0))

    yon = "↑" if degisim >= 0 else "↓"
    renk = "🟢" if degisim >= 0 else "🔴"

    mesaj = f"""
{renk} {sembol}

Fiyat: {fiyat:,.2f} TL
Degisim: {yon} %{degisim:.2f}
Hacim: {hacim:,.0f} TL
    """
    await update.message.reply_text(mesaj)


async def fiyatlar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from config import SYMBOLS

    tum_veriler = api.get_all_tickers()
    if not tum_veriler or "data" not in tum_veriler:
        await update.message.reply_text("Veri alinamadi.")
        return

    mesaj = "📊 TUM FIYATLAR\n\n"
    for item in tum_veriler["data"]:
        pair = item.get("pair", "")
        if pair in SYMBOLS:
            fiyat = float(item.get("last", 0))
            degisim = float(item.get("dailyPercent", 0))
            yon = "↑" if degisim >= 0 else "↓"
            renk = "🟢" if degisim >= 0 else "🔴"
            mesaj += f"{renk} {pair}: {fiyat:,.2f} TL ({yon}%{degisim:.2f})\n"

    await update.message.reply_text(mesaj)
