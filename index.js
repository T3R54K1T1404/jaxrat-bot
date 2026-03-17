const { Telegraf } = require('telegraf');
const admin = require('firebase-admin');
const dotenv = require('dotenv');

dotenv.config();

// ========== INIT BOT ==========
const bot = new Telegraf(process.env.BOT_TOKEN);
const OWNER_ID = process.env.OWNER_CHAT_ID;

// ========== INIT FIREBASE ADMIN (untuk bypass 2FA dan akses langsung) ==========
// Lo butuh file serviceAccountKey.json dari Firebase Console.
// Project Settings -> Service Accounts -> Generate New Private Key
// Download, taruh di folder yang sama, rename jadi 'serviceAccountKey.json'
const serviceAccount = require('./serviceAccountKey.json');

admin.initializeApp({
  credential: admin.credential.cert(serviceAccount),
  databaseURL: process.env.FIREBASE_DB_URL
});

const db = admin.database();

// ========== FUNGSI BUAT NAMBAH USER KE FIREBASE ==========
async function addUserToFirebase(email, password, uid) {
  // Lo bisa simpen data user di Realtime DB, misal di /settings/users_db/{uid}
  const userRef = db.ref(`settings/users_db/${uid}`);
  await userRef.set({
    email: email,
    password: password, // INI GA AMAN, cuma buat tujuan lo aja. biasaya pake hash.
    created_at: admin.database.ServerValue.TIMESTAMP,
    uid: uid
  });
  return true;
}

// ========== BOT COMMANDS ==========

// Start command
bot.start((ctx) => {
  if (ctx.chat.id.toString() === OWNER_ID) {
    ctx.reply('Halo Owner! Ketik /adduser buat nambahin user.');
  } else {
    ctx.reply('Halo! Buat akses panel, silahkan melakukan pembayaran ke owner.');
  }
});

// Command buat owner nambah user
bot.command('adduser', async (ctx) => {
  if (ctx.chat.id.toString() !== OWNER_ID) {
    return ctx.reply('Lu siapa? cuma owner yang bisa.');
  }

  const args = ctx.message.text.split(' ');
  // Format: /adduser <email> <password> <uid>
  if (args.length < 4) {
    return ctx.reply('Cara pake: /adduser email@gmail.com password123 UID_FIREBASE');
  }

  const email = args[1];
  const password = args[2];
  const uid = args[3];

  try {
    await addUserToFirebase(email, password, uid);
    ctx.reply(`✅ User ${email} (UID: ${uid}) berhasil ditambah ke database.`);
  } catch (error) {
    ctx.reply(`❌ Gagal: ${error.message}`);
  }
});

// Command buat user bayar (contoh sederhana)
bot.hears('bayar', (ctx) => {
  ctx.reply('Silahkan transfer 50rb ke owner, lalu kirim bukti ke @deakfta');
});

// Command untuk cek owner (contoh)
bot.command('owner', (ctx) => {
  ctx.reply('Owner: @pangeranjendral');
});

// Jalankan bot
bot.launch().then(() => {
  console.log('Bot REU berjalan coy!');
});

// Graceful stop
process.once('SIGINT', () => bot.stop('SIGINT'));
process.once('SIGTERM', () => bot.stop('SIGTERM'));
