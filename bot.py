import logging
from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, ContextTypes
from config import (
    TELEGRAM_BOT_TOKEN, SYMBOLS,
    CANLI_TARAMA_DAKIKA, SNAPSHOT_ARALIK_SAAT,
)
from database import init_db
from komutlar.basla import basla
from komutlar.fiyat import fiyat, fiyatlar
from komutlar.alarm import alarm_kur, alarm_listesi, alarm_sil
from komutlar.portfoy import portfoy_ekle, portfoy_goster, portfoy_sil
from komutlar.sinyal import son_sinyaller
from komutlar.istatistik import bot_istatistik
from komutlar.bist import bist_fiyat, bist_liste
from komutlar.altin import altin_fiyat, altin_tum
from sistem.kontrol_job import run_control_jobs
from sistem.canli_tarama import tara
from sistem.gunluk_snapshot import snapshot_al, SnapshotHatasi
from data.sembol_dogrula import dogrula, SembolHatasi
from sistem.abone import aktif_aboneler

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def post_init(application: Application):
    commands = [
        BotCommand("basla", "Botu baslat"),
        BotCommand("fiyat", "Kripto fiyat (orn: /fiyat BTC)"),
        BotCommand("fiyatlar", "Tum kripto fiyatlar"),
        BotCommand("bist", "BIST hisse (orn: /bist THYAO)"),
        BotCommand("bistliste", "Populer BIST hisseleri"),
        BotCommand("altin", "Altin fiyati (orn: /altin gram)"),
        BotCommand("altindoviz", "Altin ve doviz fiyatlar"),
        BotCommand("alarm_kur", "Alarm kur"),
        BotCommand("alarm_listesi", "Alarm listesi"),
        BotCommand("alarm_sil", "Alarm sil"),
        BotCommand("portfoy_ekle", "Portfoy ekle"),
        BotCommand("portfoy_goster", "Portfoy goster"),
        BotCommand("portfoy_sil", "Portfoy sil"),
        BotCommand("sinyaller", "Son sinyaller"),
        BotCommand("istatistik", "Bot istatistikleri"),
    ]
    await application.bot.set_my_commands(commands)


async def alarm_kontrol_callback(context: ContextTypes.DEFAULT_TYPE):
    try:
        mesajlar = run_control_jobs()
        
        for mesaj_bilgisi in mesajlar:
            await context.bot.send_message(
                chat_id=mesaj_bilgisi["user_id"],
                text=mesaj_bilgisi["mesaj"]
            )
            logger.info(f"Alarm bildirimi gonderildi: {mesaj_bilgisi['user_id']}")
            
    except Exception as e:
        logger.error(f"Alarm kontrol hatasi: {e}")


async def canli_tarama_callback(context: ContextTypes.DEFAULT_TYPE):
    """Canli sinyal taramasi. Backtest ile ayni kural ve ayni durum makinesi."""
    try:
        mesajlar = tara()
        if not mesajlar:
            return

        aboneler = aktif_aboneler()
        if not aboneler:
            logger.warning(
                f"{len(mesajlar)} sinyal uretildi ama kayitli abone yok -- "
                "gonderilemedi. Telegram'da /basla yaz. (Sinyaller signal_log'a "
                "yazildi, olcum icin kaybolmadi.)"
            )
            return

        for chat_id in aboneler:
            for mesaj in mesajlar:
                try:
                    await context.bot.send_message(chat_id=chat_id, text=mesaj)
                except Exception as e:
                    logger.error(f"Sinyal {chat_id} sohbetine gonderilemedi: {e}")
        logger.info(f"{len(mesajlar)} sinyal, {len(aboneler)} aboneye gonderildi.")
    except Exception as e:
        logger.error(f"Canli tarama hatasi: {e}", exc_info=True)


async def snapshot_callback(context: ContextTypes.DEFAULT_TYPE):
    """Gunluk borsa anlik goruntusu. Kacirilan her gun geri kazanilamaz."""
    try:
        snapshot_al()
    except SnapshotHatasi as e:
        logger.error(f"Snapshot alinamadi: {e}")


def main():
    init_db()

    # GOREV 8.2: config.SYMBOLS sabit bir liste; borsa degisiyor (MATIC -> POL).
    # Acilista dogrula, olmayanlari uyari basarak cikar.
    try:
        gecerli, eksik = dogrula(SYMBOLS)
        if eksik:
            logger.warning(f"Borsada olmayan semboller listeden cikarildi: {eksik}")
        logger.info(f"Gecerli sembol sayisi: {len(gecerli)}")
    except SembolHatasi as e:
        logger.error(f"Sembol dogrulama basarisiz: {e}")
        raise

    app = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    app.add_handler(CommandHandler("basla", basla))
    app.add_handler(CommandHandler("start", basla))
    app.add_handler(CommandHandler("fiyat", fiyat))
    app.add_handler(CommandHandler("fiyatlar", fiyatlar))
    app.add_handler(CommandHandler("bist", bist_fiyat))
    app.add_handler(CommandHandler("bistliste", bist_liste))
    app.add_handler(CommandHandler("altin", altin_fiyat))
    app.add_handler(CommandHandler("altindoviz", altin_tum))
    app.add_handler(CommandHandler("alarm_kur", alarm_kur))
    app.add_handler(CommandHandler("alarm_listesi", alarm_listesi))
    app.add_handler(CommandHandler("alarm_sil", alarm_sil))
    app.add_handler(CommandHandler("portfoy_ekle", portfoy_ekle))
    app.add_handler(CommandHandler("portfoy_goster", portfoy_goster))
    app.add_handler(CommandHandler("portfoy_sil", portfoy_sil))
    app.add_handler(CommandHandler("sinyaller", son_sinyaller))
    app.add_handler(CommandHandler("istatistik", bot_istatistik))

    job_queue = app.job_queue
    job_queue.run_repeating(
        alarm_kontrol_callback,
        interval=60,
        first=10
    )
    logger.info("Alarm kontrol job baslatildi (60 sn aralikla)")

    job_queue.run_repeating(
        canli_tarama_callback,
        interval=CANLI_TARAMA_DAKIKA * 60,
        first=30,
    )
    logger.info(f"Canli tarama job baslatildi ({CANLI_TARAMA_DAKIKA} dk aralikla)")

    job_queue.run_repeating(
        snapshot_callback,
        interval=SNAPSHOT_ARALIK_SAAT * 3600,
        first=5,
    )
    logger.info(f"Gunluk snapshot job baslatildi ({SNAPSHOT_ARALIK_SAAT} saat aralikla)")

    logger.info("Bot baslatiliyor...")
    app.run_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES
    )


if __name__ == '__main__':
    main()
