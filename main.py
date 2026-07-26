import sqlite3
import logging
import asyncio
import time
import os
import re
import requests
import random
import string
import urllib.parse
import yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.constants import ParseMode, ChatAction
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# 🌐 Keep Alive for 24/7 Hosting
from keep_alive import keep_alive

# --- ⚙️ CONFIGURATION ---
BOT_TOKEN = "8965741278:AAGP596JO1bxSt3xDZJbMQVIuogc6MejJI8"
SUPPORT_ID = "@Grp_Sale_999"
ADMIN_ID = 6836865426  # ⚠️ এখানে আপনার নিজের টেলিগ্রাম আইডি (সংখ্যা) বসান

ADMIN_USERNAME = "saddamadmin"
ADMIN_PASSWORD = "saddamadmin1234"

# Payment Details
PAYMENT_NUMBER = "01985664862"
BINANCE_ID = "1003992525"

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
DB_NAME = "nexus_superbot.db"

# --- 💾 DATABASE SETUP ---
def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY, first_name TEXT, joined_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_vip INTEGER DEFAULT 0, coins INTEGER DEFAULT 50
        )''')
        conn.execute("CREATE TABLE IF NOT EXISTS stats (key TEXT PRIMARY KEY, value INTEGER DEFAULT 0)")
        for k in ['downloads', 'ai_chats', 'tools_used']:
            conn.execute("INSERT OR IGNORE INTO stats (key, value) VALUES (?, 0)", (k,))
        conn.commit()

init_db()

def save_user(user_id, first_name):
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("INSERT OR IGNORE INTO users (user_id, first_name) VALUES (?, ?)", (user_id, first_name))
        conn.commit()

def update_stat(key):
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute(f"UPDATE stats SET value = value + 1 WHERE key = '{key}'")
        conn.commit()

def get_user(user_id):
    with sqlite3.connect(DB_NAME) as conn:
        return conn.execute("SELECT is_vip, coins FROM users WHERE user_id = ?", (user_id,)).fetchone()

# --- 🚀 START MENU ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    save_user(user.id, user.first_name)
    context.user_data['state'] = None
    
    text = (
        f"✨ <b>Welcome to Nexus Pro, {user.first_name}!</b> 🚀\n\n"
        f"I am the <b>Ultimate SuperBot</b>. I can download any media, assist you with AI, convert files, and much more! Everything in one place.\n\n"
        f"👇 <b>Select a module from below to get started:</b>"
    )
    
    kb = [
        [InlineKeyboardButton("📥 Universal Downloader", callback_data="mod_dl")],
        [InlineKeyboardButton("🤖 Smart AI Tools", callback_data="mod_ai"), InlineKeyboardButton("🛠 Utility Tools", callback_data="mod_tools")],
        [InlineKeyboardButton("👤 My Profile", callback_data="my_profile"), InlineKeyboardButton("💎 VIP Premium", callback_data="vip_menu")],
        [InlineKeyboardButton("🎧 24/7 Support", url=f"https://t.me/{SUPPORT_ID.replace('@', '')}")]
    ]
    
    if user.id == ADMIN_ID:
        kb.append([InlineKeyboardButton("👑 God-Level Admin Panel", callback_data="admin_panel")])
        
    if update.message:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)
    else:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

# --- 🎮 BUTTON HANDLERS ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id
    
    # 🔙 Back to Main Menu
    if data == "start_menu":
        context.user_data['state'] = None
        await start(update, context)

    # 📥 1. Downloader Module
    elif data == "mod_dl":
        context.user_data['state'] = 'WAITING_DL_LINK'
        txt = (
            "📥 <b>Universal Downloader</b>\n━━━━━━━━━━━━━━━━━━\n"
            "💡 <b>How to use:</b>\n"
            "Just send me any video link from <b>Facebook, TikTok, Instagram, or YouTube</b>.\n"
            "I will automatically download it without watermark!\n\n"
            "👉 <i>Paste your link below now:</i>"
        )
        await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Main Menu", callback_data="start_menu")]]), parse_mode=ParseMode.HTML)

    # 🤖 2. AI Tools Module
    elif data == "mod_ai":
        txt = "🤖 <b>Smart AI Tools</b>\n━━━━━━━━━━━━━━━━━━\nSelect an AI feature to use:"
        kb = [
            [InlineKeyboardButton("💬 Chat with AI", callback_data="ai_chat"), InlineKeyboardButton("🗣 Text to Voice", callback_data="ai_tts")],
            [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="start_menu")]
        ]
        await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

    elif data == "ai_chat":
        context.user_data['state'] = 'WAITING_AI_CHAT'
        txt = "💬 <b>AI Chat Mode</b>\n\n💡 <b>How to use:</b>\nSend me any question, math problem, or story topic. I will reply like a human!\n\n👉 <i>Type your message below:</i>"
        await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="mod_ai")]]), parse_mode=ParseMode.HTML)

    elif data == "ai_tts":
        context.user_data['state'] = 'WAITING_AI_TTS'
        txt = "🗣 <b>Text to Voice (Audio)</b>\n\n💡 <b>How to use:</b>\nSend me any English text, and I will convert it into a beautiful voice message!\n\n👉 <i>Type your text below:</i>"
        await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="mod_ai")]]), parse_mode=ParseMode.HTML)

    # 🛠 3. Utility Tools Module
    elif data == "mod_tools":
        txt = "🛠 <b>Utility & Everyday Tools</b>\n━━━━━━━━━━━━━━━━━━\nSelect a tool to use:"
        kb = [
            [InlineKeyboardButton("🔗 URL Shortener", callback_data="tool_short_url"), InlineKeyboardButton("🔳 QR Code Generator", callback_data="tool_qr")],
            [InlineKeyboardButton("🔐 Password Generator", callback_data="tool_pass")],
            [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="start_menu")]
        ]
        await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

    elif data == "tool_short_url":
        context.user_data['state'] = 'WAITING_SHORT_URL'
        txt = "🔗 <b>URL Shortener</b>\n\n💡 <b>How to use:</b>\nSend me a very long web link, and I will make it short and clean for you!\n\n👉 <i>Paste your long link below:</i>"
        await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="mod_tools")]]), parse_mode=ParseMode.HTML)

    elif data == "tool_qr":
        context.user_data['state'] = 'WAITING_QR_TEXT'
        txt = "🔳 <b>QR Code Generator</b>\n\n💡 <b>How to use:</b>\nSend me any link, name, or text. I will instantly create a high-quality QR Code image for it!\n\n👉 <i>Send your text/link below:</i>"
        await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="mod_tools")]]), parse_mode=ParseMode.HTML)

    elif data == "tool_pass":
        # Generate Password instantly
        chars = string.ascii_letters + string.digits + "!@#$%^&*"
        password = ''.join(random.choice(chars) for _ in range(12))
        txt = f"🔐 <b>Secure Password Generated:</b>\n\n<code>{password}</code>\n\n<i>(Tap on the password to copy it)</i>"
        await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Generate Another", callback_data="tool_pass")], [InlineKeyboardButton("🔙 Back", callback_data="mod_tools")]]), parse_mode=ParseMode.HTML)

    # 👤 4. My Profile
    elif data == "my_profile":
        user_data = get_user(user_id)
        is_vip = "✅ VIP Active" if user_data[0] else "❌ Normal User"
        coins = user_data[1]
        txt = f"👤 <b>Your Profile:</b>\n━━━━━━━━━━━━━━━━━━\n📝 Name: {query.from_user.first_name}\n🆔 Telegram ID: <code>{user_id}</code>\n\n💎 Status: <b>{is_vip}</b>\n🪙 Balance: <b>{coins} Coins</b>\n\n<i>Note: Become a VIP to enjoy unlimited features and 0 ads!</i>"
        await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💎 Upgrade to VIP", callback_data="vip_menu")], [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="start_menu")]]), parse_mode=ParseMode.HTML)

    # 💎 5. VIP Premium Menu
    elif data == "vip_menu":
        txt = (
            "💎 <b>Upgrade to VIP Premium</b> 💎\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "Unlock the full power of Nexus Pro!\n"
            "✅ Unlimited Video Downloads\n"
            "✅ Unlimited AI Chats & Voice\n"
            "✅ 24/7 Priority Support\n\n"
            "💰 <b>Subscription Price: 150 BDT / $1.5 USD (Lifetime)</b>\n\n"
            "🏦 <b>Payment Methods:</b>\n"
            f"🔹 Bkash / Nagad / Rocket (Personal): <code>{PAYMENT_NUMBER}</code>\n"
            f"🔹 Binance Pay ID: <code>{BINANCE_ID}</code>\n\n"
            f"📩 <b>How to buy?</b>\n"
            f"Send the money to the number above, take a screenshot, and send it to our admin: {SUPPORT_ID}."
        )
        await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🎧 Contact Admin to Buy", url=f"https://t.me/{SUPPORT_ID.replace('@', '')}")], [InlineKeyboardButton("🔙 Back", callback_data="start_menu")]]), parse_mode=ParseMode.HTML)

    # 👑 6. God-Level Admin Panel
    elif data == "admin_panel":
        if user_id != ADMIN_ID: return await query.answer("❌ Access Denied!", show_alert=True)
        
        with sqlite3.connect(DB_NAME) as conn:
            users_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            dl_count = conn.execute("SELECT value FROM stats WHERE key='downloads'").fetchone()[0]
            
        txt = f"👑 <b>God-Level Dashboard</b>\n━━━━━━━━━━━━━━━━━━\n👥 Total Users: {users_count}\n📥 Total Downloads: {dl_count}\n━━━━━━━━━━━━━━━━━━"
        kb = [
            [InlineKeyboardButton("📣 Global Broadcast", callback_data="admin_bc"), InlineKeyboardButton("💎 Make VIP", callback_data="admin_add_vip")],
            [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="start_menu")]
        ]
        await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

    elif data == "admin_bc":
        context.user_data['state'] = 'WAITING_BC_MSG'
        await query.edit_message_text("📣 <b>Global Broadcast:</b>\nSend the message (Text/Photo/Video) you want to send to all users:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="admin_panel")]]), parse_mode=ParseMode.HTML)

    elif data == "admin_add_vip":
        context.user_data['state'] = 'WAITING_VIP_ID'
        await query.edit_message_text("💎 <b>Add VIP User:</b>\nEnter the Telegram User ID of the person you want to make VIP:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="admin_panel")]]), parse_mode=ParseMode.HTML)


# --- 🧠 MESSAGE PROCESSOR (The Core Logic) ---
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    state = context.user_data.get('state')

    # 👑 Admin Logics
    if state == 'WAITING_BC_MSG' and user_id == ADMIN_ID:
        with sqlite3.connect(DB_NAME) as conn: users = [u[0] for u in conn.execute("SELECT user_id FROM users").fetchall()]
        msg = await update.message.reply_text(f"⏳ Sending broadcast to {len(users)} users...")
        success = 0
        for uid in users:
            try:
                await context.bot.copy_message(chat_id=uid, from_chat_id=user_id, message_id=update.message.message_id)
                success += 1
                await asyncio.sleep(0.05)
            except: pass
        await msg.edit_text(f"✅ Broadcast complete! Sent to {success} users.")
        context.user_data['state'] = None
        return

    elif state == 'WAITING_VIP_ID' and user_id == ADMIN_ID:
        if text.isdigit():
            target_id = int(text)
            with sqlite3.connect(DB_NAME) as conn:
                conn.execute("UPDATE users SET is_vip = 1 WHERE user_id = ?", (target_id,))
                conn.commit()
            await update.message.reply_text(f"✅ User <code>{target_id}</code> is now a VIP!", parse_mode=ParseMode.HTML)
            try: await context.bot.send_message(chat_id=target_id, text="🎉 <b>Congratulations!</b> The Admin has upgraded your account to <b>VIP Premium</b>! Enjoy unlimited features.", parse_mode=ParseMode.HTML)
            except: pass
        else:
            await update.message.reply_text("❌ Invalid ID. Send a valid number.")
        context.user_data['state'] = None
        return

    # 🤖 AI Chat Logic
    if state == 'WAITING_AI_CHAT':
        await context.bot.send_chat_action(chat_id=user_id, action=ChatAction.TYPING)
        try:
            url = f"https://api.popcat.xyz/chatbot?msg={urllib.parse.quote(text)}&owner=Nexus&botname=AI"
            reply = requests.get(url).json().get('response', "I am resting now. Try again later.")
            await update.message.reply_text(f"🤖 <b>AI:</b> {reply}", parse_mode=ParseMode.HTML)
            update_stat('ai_chats')
        except:
            await update.message.reply_text("❌ API Error. Try again later.")
        return

    # 🗣 AI Text to Voice Logic
    elif state == 'WAITING_AI_TTS':
        await context.bot.send_chat_action(chat_id=user_id, action=ChatAction.RECORD_VOICE)
        try:
            tts_url = f"https://api.popcat.xyz/google_voice?text={urllib.parse.quote(text)}"
            await update.message.reply_voice(voice=tts_url, caption="🗣 <b>Generated by Nexus AI</b>", parse_mode=ParseMode.HTML)
            update_stat('tools_used')
        except:
            await update.message.reply_text("❌ Failed to generate voice. Make sure it's English text.")
        return

    # 🔗 URL Shortener Logic
    elif state == 'WAITING_SHORT_URL':
        if not text.startswith("http"):
            return await update.message.reply_text("❌ Please send a valid link starting with http/https.")
        await context.bot.send_chat_action(chat_id=user_id, action=ChatAction.TYPING)
        try:
            short_url = requests.get(f"https://tinyurl.com/api-create.php?url={text}").text
            await update.message.reply_text(f"✅ <b>Here is your Short Link:</b>\n\n👉 {short_url}", parse_mode=ParseMode.HTML, disable_web_page_preview=True)
            update_stat('tools_used')
        except:
            await update.message.reply_text("❌ API Error.")
        return

    # 🔳 QR Code Logic
    elif state == 'WAITING_QR_TEXT':
        await context.bot.send_chat_action(chat_id=user_id, action=ChatAction.UPLOAD_PHOTO)
        try:
            qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=500x500&data={urllib.parse.quote(text)}"
            await update.message.reply_photo(photo=qr_url, caption="✅ <b>Here is your QR Code!</b>\n<i>Generated by Nexus Pro</i>", parse_mode=ParseMode.HTML)
            update_stat('tools_used')
        except:
            await update.message.reply_text("❌ Failed to generate QR code.")
        return

    # 📥 Downloader Logic (If state is WAITING_DL_LINK or just a link)
    if state == 'WAITING_DL_LINK' or re.match(r'http[s]?://', text):
        if not text.startswith("http"):
            return await update.message.reply_text("❌ Please send a valid video link.")
            
        status = await update.message.reply_text("⏳ <b>Processing video... Please wait!</b>", parse_mode=ParseMode.HTML)
        await context.bot.send_chat_action(chat_id=user_id, action=ChatAction.RECORD_VIDEO)
        
        # Download in background
        filename = f"dl_{user_id}_{int(time.time())}.mp4"
        ydl_opts = {'format': 'best', 'outtmpl': filename, 'quiet': True, 'noplaylist': True}
        
        try:
            loop = asyncio.get_event_loop()
            def run_yt():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([text])
            await loop.run_in_executor(None, run_yt)
            
            if os.path.exists(filename):
                if os.path.getsize(filename) > 50 * 1024 * 1024:
                    await status.edit_text("❌ <b>File is too large (50MB+)!</b> Cannot send via Telegram bot.", parse_mode=ParseMode.HTML)
                else:
                    await status.edit_text("🚀 <b>Uploading video to your inbox...</b>", parse_mode=ParseMode.HTML)
                    with open(filename, 'rb') as vid:
                        await context.bot.send_video(chat_id=user_id, video=vid, caption="📥 <b>Downloaded via Nexus Pro</b>", parse_mode=ParseMode.HTML)
                    update_stat('downloads')
                    await status.delete()
                os.remove(filename)
            else:
                await status.edit_text("❌ <b>Download Failed!</b> The link might be private or blocked.", parse_mode=ParseMode.HTML)
        except Exception as e:
            await status.edit_text("❌ <b>Download Failed!</b> Ensure the link is correct and public.", parse_mode=ParseMode.HTML)
        return

    # If no state is set and it's not a link
    await update.message.reply_text("🤖 I didn't understand that. Please select an option from the /start menu.", parse_mode=ParseMode.HTML)

# --- 🎯 MAIN EXECUTION ---
def main():
    keep_alive()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    print("🚀 Nexus Pro OmniBot is running 24/7...")
    app.run_polling()

if __name__ == '__main__':
    main()
