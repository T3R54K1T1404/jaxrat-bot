import telebot
import firebase_admin
from firebase_admin import credentials, db, auth
import qrcode
from io import BytesIO

# === KONFIGURASI ===
BOT_TOKEN = "8019851816:AAFytb4-6Owqdttdhja77wqabJt8p_ZUaho"
OWNER_CHAT_ID = "6754308724"  # Chat ID lo @pangeranjendral

# Initialize Firebase (pake service account)
# Lo harus download serviceAccountKey.json dari Firebase Console
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://jaxrat-6813c-default-rtdb.firebaseio.com'
})

bot = telebot.TeleBot(BOT_TOKEN)

# === DATABASE REF ===
users_db = db.reference('settings/users_db')
owner_uid_ref = db.reference('settings/owner_uid')

# === HANDLER START ===
@bot.message_handler(commands=['start'])
def start(message):
    if message.chat.id == int(OWNER_CHAT_ID):
        bot.reply_to(message, "👑 Welcome Owner!\n/panel_credentials - Lihat semua akun panel\n/add_user - Tambah user\n/revoke - Hapus user")
    else:
        bot.reply_to(message, "💰 Harga: 50rb\nScan QR untuk bayar:")
        # Generate QR code pembayaran
        qr = qrcode.make("https://t.me/deakfta")  # Ganti link pembayaran
        bio = BytesIO()
        qr.save(bio, 'PNG')
        bio.seek(0)
        bot.send_photo(message.chat.id, bio, caption="Scan untuk bayar. Kirim bukti ke @deakfta")

# === OWNER COMMANDS ===
@bot.message_handler(commands=['add_user'])
def add_user(message):
    if message.chat.id != int(OWNER_CHAT_ID):
        return
    
    # Format: /add_user email password
    try:
        _, email, password = message.text.split()
        
        # Buat user di Firebase Auth
        user = auth.create_user(email=email, password=password)
        
        # Simpan ke database
        users_db.child(user.uid).set({
            'email': email,
            'created_at': int(message.date),
            'status': 'active'
        })
        
        bot.reply_to(message, f"✅ User {email} ditambahkan! UID: {user.uid}")
    except Exception as e:
        bot.reply_to(message, f"❌ Gagal: {str(e)}\nGunakan: /add_user email password")

@bot.message_handler(commands=['panel_credentials'])
def panel_credentials(message):
    if message.chat.id != int(OWNER_CHAT_ID):
        return
    
    users = users_db.get()
    text = "📋 DAFTAR USER PANEL:\n\n"
    for uid, data in users.items():
        text += f"Email: {data['email']}\nPass: [TERSIMPAN]\nUID: {uid}\nStatus: {data['status']}\n---\n"
    bot.reply_to(message, text)

# === HANDLER UNTUK KONFIRMASI PEMBAYARAN ===
@bot.message_handler(commands=['confirm'])
def confirm_payment(message):
    if message.chat.id != int(OWNER_CHAT_ID):
        return
    
    # Format: /confirm user_id email panel@email.com password123
    try:
        _, temp_uid, email, password = message.text.split()
        
        # Buat user Firebase Auth
        user = auth.create_user(email=email, password=password)
        
        # Simpan ke database
        users_db.child(user.uid).set({
            'email': email,
            'created_at': int(message.date),
            'status': 'active'
        })
        
        # Kirim ke user via chat_id temp_uid
        bot.send_message(temp_uid, f"✅ AKUN PANEL ANDA SIAP!\nEmail: {email}\nPassword: {password}\nLogin di: https://panel-lo.vercel.app")
        
        bot.reply_to(message, f"✅ Akun {email} dikirim ke user!")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

# === SET OWNER UID FIREBASE ===
@bot.message_handler(commands=['setowneruid'])
def set_owner_uid(message):
    if message.chat.id != int(OWNER_CHAT_ID):
        return
    
    # Format: /setowneruid UIDFIREBASE
    uid = message.text.split()[1]
    owner_uid_ref.set(uid)
    bot.reply_to(message, f"✅ Owner UID diset ke: {uid}")

bot.infinity_polling()
