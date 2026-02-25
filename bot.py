import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import yt_dlp

# Cargar configuración
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ALLOWED_USER_ID = int(os.getenv("ALLOWED_USER_ID", "0"))

# Carpeta donde se guardarán los audios
DOWNLOAD_FOLDER = Path("downloads")
DOWNLOAD_FOLDER.mkdir(exist_ok=True)

# Opciones de descarga para yt-dlp (solo audio, mejor calidad)
YDL_OPTS = {
    'format': 'bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
    'outtmpl': str(DOWNLOAD_FOLDER / '%(title)s.%(ext)s'),
    'quiet': True,
    'no_warnings': True,
}

# Función para verificar si el usuario está autorizado
def is_authorized(user_id: int) -> bool:
    if ALLOWED_USER_ID == 0:
        return True
    return user_id == ALLOWED_USER_ID

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        await update.message.reply_text("⛔ No tienes permiso para usar este bot.")
        return
    
    if ALLOWED_USER_ID == 0:
        await update.message.reply_text(
            f"🔧 **MODO CONFIGURACIÓN**\n\n"
            f"Tu ID de usuario es: `{user_id}`\n\n"
            f"⚠️ **IMPORTANTE:** Copia este número y pégalo en el archivo `.env` "
            f"como `ALLOWED_USER_ID={user_id}`. Luego reinicia el bot.\n\n"
            f"Después de configurarlo, solo tú podrás usar este bot."
        )
    else:
        await update.message.reply_text(
            "🎵 **Bot Descargador de Audio**\n\n"
            "Envíame un enlace de YouTube y lo convertiré a MP3 para ti.\n\n"
            "✅ **Solo videos individuales, NO listas de reproducción.**"
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not is_authorized(user_id):
        await update.message.reply_text("⛔ No tienes permiso para usar este bot.")
        return
    
    url = update.message.text
    
    # Detectar listas de reproducción
    if "list=" in url or "playlist" in url.lower():
        await update.message.reply_text(
            "❌ **Error: No se permiten listas de reproducción**\n\n"
            "Envía el enlace de un SOLO video."
        )
        return
    
    progress_msg = await update.message.reply_text("⏳ Descargando y convirtiendo a MP3...")
    
    try:
        loop = asyncio.get_event_loop()
        with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
            info = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=True))
            
            if 'entries' in info:
                await progress_msg.edit_text("❌ No se permiten listas de reproducción.")
                return
            
            filename = ydl.prepare_filename(info)
            mp3_filename = Path(str(filename).rsplit('.', 1)[0] + '.mp3')
            
            if mp3_filename.exists():
                with open(mp3_filename, 'rb') as audio_file:
                    await update.message.reply_audio(
                        audio=audio_file,
                        title=info.get('title', 'Audio'),
                        performer=info.get('uploader', 'Desconocido'),
                        duration=info.get('duration', 0)
                    )
                
                mp3_filename.unlink()
                await progress_msg.delete()
            else:
                await progress_msg.edit_text("❌ Error: No se encontró el archivo convertido.")
                
    except Exception as e:
        await progress_msg.edit_text(f"❌ Error: {str(e)[:100]}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        await update.message.reply_text("⛔ No tienes permiso para usar este bot.")
        return
    
    help_text = (
        "🎵 **Bot Descargador de Audio**\n\n"
        "📌 **Cómo usar:**\n"
        "1. Envíame un enlace de YouTube\n"
        "2. Espera mientras proceso\n"
        "3. Recibirás el MP3\n\n"
        "⚠️ **Solo videos individuales**\n\n"
        "📌 **Comandos:**\n"
        "/start - Iniciar\n"
        "/help - Ayuda"
    )
    await update.message.reply_text(help_text)

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("🤖 Bot iniciado. Presiona Ctrl+C para detener.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()