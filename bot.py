import os
import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import yt_dlp

# ============================================
# CONFIGURACIÓN MEJORADA CON DEPURACIÓN
# ============================================

# Cargar variables de entorno (para local)
load_dotenv()

# Obtener token de MULTIPLES fuentes (para asegurar)
BOT_TOKEN = None

# Fuente 1: Variable de entorno directa
BOT_TOKEN = os.environ.get("BOT_TOKEN")

# Fuente 2: Desde archivo .env (si existe)
if not BOT_TOKEN:
    try:
        from dotenv import load_dotenv
        load_dotenv()
        BOT_TOKEN = os.getenv("BOT_TOKEN")
    except:
        pass

# BOT_TOKEN = os.environ.get("BOT_TOKEN")

# VERIFICAR TOKEN
print("=" * 50)
print("🔍 DEBUG - Verificando configuración:")
print(f"📌 BOT_TOKEN encontrado: {'✅ SI' if BOT_TOKEN else '❌ NO'}")
if BOT_TOKEN:
    print(f"📌 BOT_TOKEN (primeros 10 chars): {BOT_TOKEN[:10]}...")
print(f"📌 ALLOWED_USER_ID: {os.environ.get('ALLOWED_USER_ID', 'NO CONFIGURADO')}")
print("=" * 50)

if not BOT_TOKEN:
    print("❌ ERROR CRÍTICO: No se pudo encontrar BOT_TOKEN")
    print("📌 Variables de entorno disponibles:")
    for key in os.environ.keys():
        print(f"   - {key}")
    sys.exit(1)

# Obtener ALLOWED_USER_ID
ALLOWED_USER_ID = os.environ.get("ALLOWED_USER_ID")
if ALLOWED_USER_ID:
    ALLOWED_USER_ID = int(ALLOWED_USER_ID)
else:
    ALLOWED_USER_ID = 0
    print("⚠️  ALLOWED_USER_ID no configurado, modo abierto (cualquiera puede usar el bot)")

# Carpeta de descargas
DOWNLOAD_FOLDER = Path("downloads")
DOWNLOAD_FOLDER.mkdir(exist_ok=True)

# Opciones de yt-dlp
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

def is_authorized(user_id: int) -> bool:
    if ALLOWED_USER_ID == 0:
        return True
    return user_id == ALLOWED_USER_ID

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    print(f"📨 /start desde usuario {user_id}")
    
    if not is_authorized(user_id):
        await update.message.reply_text("⛔ No tienes permiso para usar este bot.")
        return
    
    await update.message.reply_text(
        "🎵 **Bot Descargador de Audio**\n\n"
        "Envíame un enlace de YouTube y lo convertiré a MP3.\n\n"
        "✅ Solo videos individuales, NO listas."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    url = update.message.text
    
    print(f"📨 Mensaje de {user_id}: {url[:50]}...")
    
    if not is_authorized(user_id):
        await update.message.reply_text("⛔ No tienes permiso.")
        return
    
    if "list=" in url or "playlist" in url.lower():
        await update.message.reply_text("❌ No se permiten listas de reproducción.")
        return
    
    progress_msg = await update.message.reply_text("⏳ Descargando y convirtiendo...")
    
    try:
        loop = asyncio.get_event_loop()
        with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
            info = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=True))
            
            if 'entries' in info:
                await progress_msg.edit_text("❌ Es una playlist. No permitido.")
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
                await progress_msg.edit_text("❌ Error: No se encontró el archivo.")
                
    except Exception as e:
        await progress_msg.edit_text(f"❌ Error: {str(e)[:100]}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        await update.message.reply_text("⛔ No tienes permiso.")
        return
    
    await update.message.reply_text(
        "🎵 **Bot Descargador**\n\n"
        "Envía un enlace de YouTube y recibe el MP3."
    )

def main():
    print("🚀 Iniciando bot...")
    print(f"📌 Token configurado: {'✅' if BOT_TOKEN else '❌'}")
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("🤖 Bot iniciado correctamente. Escuchando mensajes...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()