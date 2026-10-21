from telegram import Update
from telegram.ext import ContextTypes
from v3_altin import altin


async def altin_fiyat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Kullanim: /altin [tur]\n"
            "Turler: gram, ceyrek, yarim, tam, ons\n"
            "Orn: /altin gram"
        )
        return

    tur = context.args[0].lower()

    if tur == "gram":
        data = altin.get_gram_altin()
        if data:
            mesaj = f"""
GRAM ALTIN

Alis: {data['alis']:,.2f} TL
Satis: {data['satis']:,.2f} TL
Degisim: {data['degisim']}
            """
            await update.message.reply_text(mesaj)
        else:
            await update.message.reply_text("Gram altin verisi alinamadi.")

    elif tur == "ceyrek":
        data = altin.get_ceyrek_altin()
        if data:
            mesaj = f"""
CEYREK ALTIN

Alis: {data['alis']:,.2f} TL
Satis: {data['satis']:,.2f} TL
Degisim: {data['degisim']}
            """
            await update.message.reply_text(mesaj)
        else:
            await update.message.reply_text("Ceyrek altin verisi alinamadi.")

    elif tur == "yarim":
        data = altin.get_yarim_altin()
        if data:
            mesaj = f"""
YARIM ALTIN

Alis: {data['alis']:,.2f} TL
Satis: {data['satis']:,.2f} TL
Degisim: {data['degisim']}
            """
            await update.message.reply_text(mesaj)
        else:
            await update.message.reply_text("Yarim altin verisi alinamadi.")

    elif tur == "tam":
        data = altin.get_tam_altin()
        if data:
            mesaj = f"""
TAM ALTIN

Alis: {data['alis']:,.2f} TL
Satis: {data['satis']:,.2f} TL
Degisim: {data['degisim']}
            """
            await update.message.reply_text(mesaj)
        else:
            await update.message.reply_text("Tam altin verisi alinamadi.")

    elif tur == "ons":
        data = altin.get_ons_altin()
        if data:
            mesaj = f"""
ONS ALTIN (XAU/USD)

Alis: {data['alis']:.2f} USD
Satis: {data['satis']:.2f} USD
Degisim: {data['degisim']}
            """
            await update.message.reply_text(mesaj)
        else:
            await update.message.reply_text("Ons altin verisi alinamadi.")

    else:
        await update.message.reply_text("Gecersiz tur. gram/ceyrek/yarim/tam/ons kullanin.")


async def altin_tum(update: Update, context: ContextTypes.DEFAULT_TYPE):
    gram = altin.get_gram_altin()
    ceyrek = altin.get_ceyrek_altin()
    doviz = altin.get_doviz()

    mesaj = "ALTIN VE DOVIZ FİYATLARI\n\n"

    if gram:
        mesaj += f"Gram Altin: {gram['alis']:,.2f} - {gram['satis']:,.2f} TL\n"
    if ceyrek:
        mesaj += f"Ceyrek Altin: {ceyrek['alis']:,.2f} - {ceyrek['satis']:,.2f} TL\n"

    mesaj += "\nDOVIZ KURLARI\n"
    if doviz:
        for key, val in doviz.items():
            mesaj += f"{key}: {val['alis']:.4f} - {val['satis']:.4f}\n"

    await update.message.reply_text(mesaj)
