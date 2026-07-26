import os
import re
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode, ChatAction
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# আমাদের বানানো মডিউলগুলো ইম্পোর্ট করা হলো
import config
import database
from keep_alive import keep_alive
from downloader import download_media

# ডাটাবেজ চালু করা
database.init_db()

# --- 🚀 স্টার্ট কমান্ড (সুপার মেনু) ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    database.save_user(user.id, user.first_name)
    
    text = (
        f"✨ <b>Welcome to Nexus Pro, {user.first_name}!</b> 🚀\n\n"
        f"I am the <b>Ultimate SuperBot</b>. I can download media, use AI, convert files, and much more!\n\n"
        f"👇 <b>Select a module from below:</b>"
    )
    
    kb = [
        [InlineKeyboardButton("📥 Downloader", callback_data="mod_dl"), InlineKeyboardButton("🤖 AI Tools", callback_data="mod_ai")],
        [InlineKeyboardButton("🛠 Utility Tools", callback_data="mod_tools"), InlineKeyboardButton("👤 My Profile", callback_data="my_profile")],
        [InlineKeyboardButton("💎 VIP Premium", callback_data="vip_menu"), InlineKeyboardButton("🎧 Support", url=config.SUPPORT_CHANNEL)]
    ]
    
    # 👑 যদি ইউজারটি আপনি (গড এডমিন) হোন, তবে স্পেশাল বাটন দেখাবে!
    if user.id == config.ADMIN_ID:
        kb.append([InlineKeyboardButton("👑 God-Level Admin Panel", callback_data="admin_panel")])
        
    if update.message:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)
    else:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

# --- 🧠 টেক্সট ও লিংক ডিটেক্টর ---
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    
    # গ্লোবাল ব্রডকাস্ট চেক (এডমিনের জন্য)
    if context.user_data.get('state') == 'WAITING_BC_MSG' and user_id == config.ADMIN_ID:
        # ব্রডকাস্ট লজিক (পরের আপডেটে এখানে ফুল ফিচার দেবো)
        await update.message.reply_text("✅ <b>Broadcast message received!</b> (Sending logic will be added in Phase 3)", parse_mode=ParseMode.HTML)
        context.user_data['state'] = None
        return

    # লিংক স্ক্যানার
    url_pattern = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
    urls = url_pattern.findall(text)
    
    if urls:
        context.user_data['last_url'] = urls[0]
        kb = [
            [InlineKeyboardButton("🎬 Download Video", callback_data="dl_video")],
            [InlineKeyboardButton("🎵 Download Audio (MP3)", callback_data="dl_audio")]
        ]
        await update.message.reply_text("🔗 <b>Link Detected!</b>\nWhat would you like to download?", reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)
    else:
        # লিংক না হলে AI চ্যাটের রিপ্লাই দেবে (AI Phase 3 তে যুক্ত হবে)
        await update.message.reply_text("🤖 <i>AI Module is currently being upgraded. Send a video link for now!</i>", parse_mode=ParseMode.HTML)

# --- 🎮 বাটন হ্যান্ডলার ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id
    
    # 📥 ডাউনলোডার লজিক
    if data in ["dl_video", "dl_audio"]:
        url = context.user_data.get('last_url')
        if not url:
            return await query.edit_message_text("❌ Link expired. Please send the link again.")
        
        media_type = 'video' if data == 'dl_video' else 'audio'
        status_msg = await query.edit_message_text("⏳ <b>Processing your request... Please wait!</b>", parse_mode=ParseMode.HTML)
        
        # ব্যাকগ্রাউন্ডে ডাউনলোড
        loop = asyncio.get_event_loop()
        file_path = await loop.run_in_executor(None, download_media, url, user_id, media_type)
        
        if file_path and os.path.exists(file_path):
            file_size = os.path.getsize(file_path) / (1024 * 1024)
            if file_size > 49:
                await status_msg.edit_text("❌ File is too large for Telegram (Limit: 50MB).")
            else:
                await status_msg.edit_text("🚀 <b>Uploading to your inbox...</b>", parse_mode=ParseMode.HTML)
                with open(file_path, 'rb') as f:
                    if media_type == 'video':
                        await context.bot.send_video(chat_id=user_id, video=f, caption="📥 <b>Downloaded via Nexus Pro</b>", parse_mode=ParseMode.HTML)
                    else:
                        await context.bot.send_audio(chat_id=user_id, audio=f, caption="🎵 <b>Downloaded via Nexus Pro</b>", parse_mode=ParseMode.HTML)
                database.update_stat('total_downloads')
                await status_msg.delete()
            os.remove(file_path)
        else:
            await status_msg.edit_text("❌ Download failed. The link might be private or blocked.")

    # 👤 প্রোফাইল লজিক
    elif data == "my_profile":
        user_data = database.get_user_data(user_id)
        is_vip = "✅ Yes" if user_data[0] else "❌ No"
        coins = user_data[1]
        txt = f"👤 <b>Your Profile:</b>\n\n🆔 ID: <code>{user_id}</code>\n💎 VIP Status: {is_vip}\n🪙 Coins: {coins}\n\n<i>Use coins to use premium AI features!</i>"
        await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="start_menu")]]), parse_mode=ParseMode.HTML)
        
    elif data == "start_menu":
        await start(update, context)
        
    # 👑 গড-লেভেল এডমিন প্যানেল
    elif data == "admin_panel":
        if user_id != config.ADMIN_ID:
            return await query.answer("❌ You are not the God Admin!", show_alert=True)
            
        txt = "👑 <b>God-Level Admin Panel</b>\n━━━━━━━━━━━━━━━━━━\nControl your entire SuperBot from here:"
        kb = [
            [InlineKeyboardButton("📣 Global Broadcast", callback_data="admin_bc"), InlineKeyboardButton("📊 Server Stats", callback_data="admin_stats")],
            [InlineKeyboardButton("💎 Add VIP to User", callback_data="admin_vip"), InlineKeyboardButton("🪙 Give Coins", callback_data="admin_coins")],
            [InlineKeyboardButton("🔙 Back to Main", callback_data="start_menu")]
        ]
        await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)
        
    elif data == "admin_bc":
        context.user_data['state'] = 'WAITING_BC_MSG'
        await query.edit_message_text("📣 <b>Broadcast Mode:</b>\nSend the message you want to broadcast to all users:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="admin_panel")]]), parse_mode=ParseMode.HTML)

    # মডিউলগুলোর প্লেসহোল্ডার
    elif data in ["mod_dl", "mod_ai", "mod_tools", "vip_menu"]:
        await query.answer("🚀 This Module will be activated in the next Update (Phase 3)!", show_alert=True)

def main():
    keep_alive()
    app = ApplicationBuilder().token(config.BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    print("🚀 Nexus Pro SuperBot is running 24/7...")
    app.run_polling()

if __name__ == '__main__':
    main()
