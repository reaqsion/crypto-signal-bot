from telegram import Update
from telegram.ext import ContextTypes
from sistem.abone import abone_ekle


async def basla(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    # Canli sinyaller bu sohbete gonderilecek. Kaydedilmezse tarama sinyal
    # uretir ama gonderecek hedef bulamaz.
    abone_ekle(update.effective_chat.id, user.username or user.first_name)
    mesaj = f"""
Merhaba {user.first_name}! Kripto Analiz Botuna hos geldin!

Ben senin icin kripto, borsa ve altin piyasalarini izleyecek bir botum.

KRIPTO (v1):
/fiyat [sembol] - Anlik fiyat (orn: /fiyat BTC)
/fiyatlar - Tum kripto fiyatlar

BORS IstANBUL (v2):
/bist [sembol] - Hisse fiyati (orn: /bist THYAO)
/bistliste - Populer hisseler

ALTIN & DOVIZ (v3):
/altin [tur] - Altin fiyati (gram/ceyrek/yarim/tam/ons)
/altindoviz - Altin ve doviz fiyatlar

DIGER:
/alarm_kur - Alarm kur
/alarm_listesi - Alarm listesi
/alarm_sil - Alarm sil
/portfoy_ekle - Portfoy ekle
/portfoy_goster - Portfoy goster
/portfoy_sil - Portfoy sil
/sinyaller - Son sinyaller
/istatistik - Bot istatistikleri

Canli sinyaller bu sohbete gonderilecek.

Ornekler:
/fiyat BTC
/bist THYAO
/altin gram
/altindoviz
    """
    await update.message.reply_text(mesaj)
