const express = require('express');
const TelegramBot = require('node-telegram-bot-api');
const axios = require('axios');
const { v4: uuidv4 } = require('uuid');

const app = express();
app.use(express.json());

// ========== KONFIGURASI ==========
const BOT_TOKEN = process.env.BOT_TOKEN || "8019851816:AAFytb4-6Owqdttdhja77wqabJt8p_ZUaho";
const FIREBASE_URL = process.env.FIREBASE_URL || "https://kwontol-default-rtdb.firebaseio.com";
const OWNER_PHONE = process.env.OWNER_PHONE || "085136030617";
const OWNER_UID = process.env.OWNER_UID || "aKWJNVaAW3Rnclir7gNgwngLl1v1";
const GROUP_LINK = process.env.GROUP_LINK || "https://t.me/+kumpulanbuyerjaxrat";

const bot = new TelegramBot(BOT_TOKEN);
let isWebhookSet = false;

// ========== FUNGSI FIREBASE ==========
async function firebaseGet(path) {
    try {
        const url = `${FIREBASE_URL}/${path}.json`;
        const res = await axios.get(url);
        return res.data;
    } catch (error) {
        console.error('Firebase Get Error:', error.message);
        return null;
    }
}

async function firebasePut(path, data) {
    try {
        const url = `${FIREBASE_URL}/${path}.json`;
        const res = await axios.put(url, data);
        return res.data;
    } catch (error) {
        console.error('Firebase Put Error:', error.message);
        return null;
    }
}

async function firebasePost(path, data) {
    try {
        const url = `${FIREBASE_URL}/${path}.json`;
        const res = await axios.post(url, data);
        return res.data;
    } catch (error) {
        console.error('Firebase Post Error:', error.message);
        return null;
    }
}

// ========== HANDLER BOT ==========
bot.onText(/\/start/, async (msg) => {
    const chatId = msg.chat.id;
    const welcomeText = `
🔥 *JaxRaT V5 - Premium RAT Service* 🔥

Selamat datang di bot resmi JaxRaT!

Apa yang bisa saya bantu?
/register - Daftar jadi user baru
/price - Lihat harga
/group - Join group buyer
/admin - Hubungi owner
    `;
    
    await bot.sendMessage(chatId, welcomeText, { parse_mode: "Markdown" });
});

bot.onText(/\/price/, async (msg) => {
    const chatId = msg.chat.id;
    const settings = await firebaseGet("settings");
    const harga = settings?.harga || 50000;
    
    const priceText = `
💰 *HARGA JAXRAT V5* 💰

Akses Panel + Bot + Aplikasi: *Rp ${harga.toLocaleString()}*

Fitur lengkap:
✅ Live location tracking
✅ SMS & Call logs
✅ WhatsApp monitor
✅ Camera hack
✅ Keylogger
✅ File manager
✅ Anti uninstall

Pembayaran via QRIS / Transfer ke ${OWNER_PHONE}

Ketik /register untuk mulai daftar
    `;
    
    await bot.sendMessage(chatId, priceText, { parse_mode: "Markdown" });
});

bot.onText(/\/group/, async (msg) => {
    const chatId = msg.chat.id;
    const settings = await firebaseGet("settings");
    const groupLink = settings?.group_link || GROUP_LINK;
    
    await bot.sendMessage(chatId, `Join grup buyer di sini:\n${groupLink}`);
});

bot.onText(/\/admin/, async (msg) => {
    const chatId = msg.chat.id;
    await bot.sendMessage(chatId, `Hubungi owner via WhatsApp: ${OWNER_PHONE}`);
});

bot.onText(/\/register/, async (msg) => {
    const chatId = msg.chat.id;
    const userId = msg.from.id.toString();
    const username = msg.from.username || "no_username";
    
    // Cek apakah udah terdaftar
    const users = await firebaseGet("users");
    let alreadyRegistered = false;
    
    if (users) {
        for (const uid in users) {
            if (users[uid].telegram_id === userId) {
                alreadyRegistered = true;
                break;
            }
        }
    }
    
    if (alreadyRegistered) {
        await bot.sendMessage(chatId, "Kamu udah terdaftar! Kalo mau aktivasi, hubungi admin.");
        return;
    }
    
    // Simpan ke pending
    const pending = (await firebaseGet("pending_users")) || {};
    pending[userId] = {
        telegram_id: userId,
        username: username,
        chat_id: chatId,
        status: "pending",
        registered_at: Date.now() / 1000
    };
    await firebasePut("pending_users", pending);
    
    // Kirim notifikasi ke owner
    let ownerChatId = null;
    if (users) {
        for (const uid in users) {
            if (uid === OWNER_UID && users[uid].chat_id) {
                ownerChatId = users[uid].chat_id;
                break;
            }
        }
    }
    
    if (ownerChatId) {
        await bot.sendMessage(
            ownerChatId,
            `🔔 *User Baru Daftar!*\n\nUsername: @${username}\nTelegram ID: ${userId}\nChat ID: ${chatId}\n\nKetik /approve_${userId} untuk setujui`,
            { parse_mode: "Markdown" }
        );
    }
    
    await bot.sendMessage(chatId, "✅ Pendaftaran diterima! Tunggu admin approve ya. Kamu bakal dapet notifikasi kalo udah aktif.");
});

bot.onText(/\/approve_(.+)/, async (msg, match) => {
    const chatId = msg.chat.id;
    const userId = msg.from.id.toString();
    const targetId = match[1];
    
    // Cek apakah ini owner
    const users = await firebaseGet("users");
    let isOwner = false;
    
    if (users) {
        for (const uid in users) {
            if (uid === OWNER_UID && users[uid].telegram_id === userId) {
                isOwner = true;
                break;
            }
        }
    }
    
    if (!isOwner) {
        await bot.sendMessage(chatId, "❌ Lu bukan owner, gabisa approve!");
        return;
    }
    
    const pending = await firebaseGet("pending_users");
    if (!pending || !pending[targetId]) {
        await bot.sendMessage(chatId, "User gak ada di pending list.");
        return;
    }
    
    const userData = pending[targetId];
    
    // Generate UID baru untuk user
    const newUid = uuidv4().replace(/-/g, '').substring(0, 28);
    
    // Pindahin ke users
    const updatedUsers = users || {};
    updatedUsers[newUid] = {
        telegram_id: userData.telegram_id,
        username: userData.username,
        chat_id: userData.chat_id,
        status: "active",
        approved_at: Date.now() / 1000,
        expired_at: (Date.now() / 1000) + (30 * 24 * 60 * 60) // 30 hari
    };
    await firebasePut("users", updatedUsers);
    
    // Hapus dari pending
    delete pending[targetId];
    await firebasePut("pending_users", pending);
    
    // Kasih notifikasi ke user
    await bot.sendMessage(
        userData.chat_id,
        `✅ *Selamat! Akun kamu udah aktif!*\n\nUser ID kamu: \`${newUid}\`\n\nSekarang kamu bisa akses panel di:\nhttps://panel-jaxrat.vercel.app/login\n\nLogin pake email dan password yang bakal dikirim owner via WA.`,
        { parse_mode: "Markdown" }
    );
    
    // Kasih tau owner
    await bot.sendMessage(chatId, `✅ User @${userData.username} udah diaktifin dengan UID: \`${newUid}\``);
});

// ========== SETUP WEBHOOK ==========
async function setupWebhook() {
    if (isWebhookSet) return;
    
    try {
        // Dapatkan URL dari Vercel
        const vercelUrl = process.env.VERCEL_URL 
            ? `https://${process.env.VERCEL_URL}`
            : "https://panel-jaxrat.vercel.app";
            
        const webhookUrl = `${vercelUrl}/api/webhook`;
        
        await bot.setWebHook(webhookUrl);
        console.log(`Webhook set to: ${webhookUrl}`);
        isWebhookSet = true;
    } catch (error) {
        console.error('Failed to set webhook:', error);
    }
}

// ========== EXPRESS ROUTES ==========
app.post('/api/webhook', (req, res) => {
    bot.processUpdate(req.body);
    res.sendStatus(200);
});

app.get('/api/health', (req, res) => {
    res.json({ status: 'OK', message: 'JaxRaT Bot is running!' });
});

app.get('/', (req, res) => {
    res.json({ 
        name: 'JaxRaT Bot',
        version: '1.0.0',
        status: 'active',
        endpoints: {
            webhook: '/api/webhook',
            health: '/api/health'
        }
    });
});

// ========== MAIN ==========
if (process.env.NODE_ENV !== 'production') {
    // Untuk development, pake polling
    bot.startPolling();
    console.log('Bot started in polling mode');
}

setupWebhook();

module.exports = app;
