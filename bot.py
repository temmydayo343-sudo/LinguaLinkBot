import os
import io
import asyncio
import aiohttp
import json
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# ==================== CONFIGURATION ====================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable not set!")

# Multiple translation API options (fallback if one fails)
TRANSLATION_APIS = [
    {
        "url": "https://libretranslate.com/translate",
        "name": "LibreTranslate"
    },
    {
        "url": "https://translate.argosopentech.com/translate",
        "name": "Argos Translate"
    }
]

# Supported languages
LANGUAGES = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "ru": "Russian",
    "ja": "Japanese",
    "ko": "Korean",
    "zh": "Chinese (Simplified)",
    "ar": "Arabic",
    "hi": "Hindi",
    "nl": "Dutch",
    "pl": "Polish",
    "tr": "Turkish",
    "vi": "Vietnamese",
    "th": "Thai",
    "id": "Indonesian",
    "ms": "Malay",
    "sw": "Swahili",
    "ha": "Hausa",
    "yo": "Yoruba",
    "ig": "Igbo",
    "zu": "Zulu",
    "af": "Afrikaans",
    "el": "Greek",
    "he": "Hebrew",
    "hu": "Hungarian",
    "ro": "Romanian",
    "sk": "Slovak",
    "sv": "Swedish",
    "uk": "Ukrainian"
}

# User sessions
user_sessions = {}

# ==================== KEYBOARD FUNCTIONS ====================
def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("🌍 Translate Text", callback_data="translate")],
        [InlineKeyboardButton("🎤 Translate Voice", callback_data="voice")],
        [InlineKeyboardButton("📄 Translate Document", callback_data="document")],
        [InlineKeyboardButton("🔁 Auto Detect", callback_data="auto_detect")],
        [InlineKeyboardButton("📊 Language List", callback_data="languages")],
        [InlineKeyboardButton("ℹ️ Help", callback_data="help")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_language_keyboard(action: str, selected: str = None):
    """Generate language selection keyboard"""
    keyboard = []
    row = []
    count = 0
    
    # Sort languages by name
    sorted_langs = sorted(LANGUAGES.items(), key=lambda x: x[1])
    
    for code, name in sorted_langs:
        # Add checkmark if selected
        display = f"✅ {name}" if code == selected else name
        row.append(InlineKeyboardButton(display, callback_data=f"{action}_{code}"))
        count += 1
        
        if count % 2 == 0:
            keyboard.append(row)
            row = []
    
    if row:
        keyboard.append(row)
    
    # Add navigation buttons
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back")])
    
    return InlineKeyboardMarkup(keyboard)

def get_action_keyboard():
    keyboard = [
        [InlineKeyboardButton("🌍 Translate Text", callback_data="translate")],
        [InlineKeyboardButton("🎤 Translate Voice", callback_data="voice")],
        [InlineKeyboardButton("📄 Translate Document", callback_data="document")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="back")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ==================== COMMAND HANDLERS ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    
    # Initialize user session
    user_id = str(user.id)
    user_sessions[user_id] = {
        "source_lang": "auto",
        "target_lang": "en"
    }
    
    welcome_message = (
        f"🌍 Welcome {user.first_name} to **LinguaLinkBot**!\n\n"
        "🔗 I translate text, voice, and documents between 25+ languages!\n\n"
        "**What I can do:**\n"
        "• 🌍 Translate text between languages\n"
        "• 🎤 Translate voice messages to text\n"
        "• 📄 Translate document content\n"
        "• 🔁 Auto-detect source language\n"
        "• 📊 List all supported languages\n\n"
        "📤 **How to use:**\n"
        "1. Click 'Translate Text'\n"
        "2. Choose source and target languages\n"
        "3. Send your text\n"
        "4. Get your translation instantly!\n\n"
        "⬇️ Use the buttons below to get started!"
    )
    
    await update.message.reply_text(
        welcome_message,
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_text = (
        "📖 **LinguaLinkBot User Guide**\n\n"
        "**🌍 Translate Text**\n"
        "• Click 'Translate Text'\n"
        "• Choose source language (or auto-detect)\n"
        "• Choose target language\n"
        "• Send your text to translate\n\n"
        "**🎤 Translate Voice**\n"
        "• Click 'Translate Voice'\n"
        "• Choose source language (or auto-detect)\n"
        "• Choose target language\n"
        "• Send a voice message\n\n"
        "**📄 Translate Document**\n"
        "• Click 'Translate Document'\n"
        "• Choose source language (or auto-detect)\n"
        "• Choose target language\n"
        "• Send a text document (.txt, .docx)\n\n"
        "**💡 Tips**\n"
        "• Use 'Auto Detect' for unknown languages\n"
        "• Voice messages should be clear and short\n"
        "• Documents should be in plain text\n\n"
        "**Commands**\n"
        "/start - Start the bot\n"
        "/help - Show this help\n"
        "/languages - List all languages\n"
        "/cancel - Cancel current action"
    )
    
    await update.message.reply_text(
        help_text,
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )

async def languages_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /languages command"""
    lang_list = "🌍 **Supported Languages**\n\n"
    for code, name in sorted(LANGUAGES.items(), key=lambda x: x[1]):
        lang_list += f"• **{name}** (`{code}`)\n"
    
    await update.message.reply_text(
        lang_list,
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /cancel command"""
    user_id = str(update.effective_user.id)
    if user_id in user_sessions:
        user_sessions[user_id] = {
            "source_lang": "auto",
            "target_lang": "en"
        }
    
    await update.message.reply_text(
        "✅ **Action cancelled**\n\n"
        "You can start over using the buttons below.",
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )

# ==================== CALLBACK HANDLERS ====================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button presses"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = str(update.effective_user.id)
    
    if user_id not in user_sessions:
        user_sessions[user_id] = {
            "source_lang": "auto",
            "target_lang": "en"
        }
    
    if data == "translate":
        user_sessions[user_id]["action"] = "translate"
        await query.edit_message_text(
            "🌍 **Select source language:**\n\n"
            "Choose the language of the text you'll send:",
            parse_mode="Markdown",
            reply_markup=get_language_keyboard("source")
        )
    
    elif data == "voice":
        user_sessions[user_id]["action"] = "voice"
        await query.edit_message_text(
            "🎤 **Select source language:**\n\n"
            "Choose the language of the voice message:",
            parse_mode="Markdown",
            reply_markup=get_language_keyboard("source")
        )
    
    elif data == "document":
        user_sessions[user_id]["action"] = "document"
        await query.edit_message_text(
            "📄 **Select source language:**\n\n"
            "Choose the language of the document:",
            parse_mode="Markdown",
            reply_markup=get_language_keyboard("source")
        )
    
    elif data == "auto_detect":
        user_sessions[user_id]["source_lang"] = "auto"
        await query.edit_message_text(
            "🔁 **Auto-detect enabled!**\n\n"
            "Now choose the target language:",
            parse_mode="Markdown",
            reply_markup=get_language_keyboard("target")
        )
    
    elif data.startswith("source_"):
        lang_code = data.replace("source_", "")
        user_sessions[user_id]["source_lang"] = lang_code
        await query.edit_message_text(
            f"✅ Source language set to **{LANGUAGES.get(lang_code, 'Unknown')}**\n\n"
            "Now choose the target language:",
            parse_mode="Markdown",
            reply_markup=get_language_keyboard("target", lang_code)
        )
    
    elif data.startswith("target_"):
        lang_code = data.replace("target_", "")
        user_sessions[user_id]["target_lang"] = lang_code
        
        action = user_sessions[user_id].get("action", "translate")
        
        if action == "translate":
            await query.edit_message_text(
                f"✅ Translation ready!\n\n"
                f"🔹 Source: {LANGUAGES.get(user_sessions[user_id]['source_lang'], 'Auto-detect')}\n"
                f"🔹 Target: {LANGUAGES.get(lang_code, 'Unknown')}\n\n"
                "📝 **Send me the text to translate:**",
                parse_mode="Markdown",
                reply_markup=get_action_keyboard()
            )
        elif action == "voice":
            await query.edit_message_text(
                f"✅ Translation ready!\n\n"
                f"🔹 Source: {LANGUAGES.get(user_sessions[user_id]['source_lang'], 'Auto-detect')}\n"
                f"🔹 Target: {LANGUAGES.get(lang_code, 'Unknown')}\n\n"
                "🎤 **Send me a voice message to translate:**",
                parse_mode="Markdown",
                reply_markup=get_action_keyboard()
            )
        elif action == "document":
            await query.edit_message_text(
                f"✅ Translation ready!\n\n"
                f"🔹 Source: {LANGUAGES.get(user_sessions[user_id]['source_lang'], 'Auto-detect')}\n"
                f"🔹 Target: {LANGUAGES.get(lang_code, 'Unknown')}\n\n"
                "📄 **Send me a document to translate:**\n"
                "Supported: .txt, .docx",
                parse_mode="Markdown",
                reply_markup=get_action_keyboard()
            )
    
    elif data == "languages":
        lang_list = "🌍 **Supported Languages**\n\n"
        for code, name in sorted(LANGUAGES.items(), key=lambda x: x[1]):
            lang_list += f"• **{name}** (`{code}`)\n"
        
        await query.edit_message_text(
            lang_list,
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
    
    elif data == "help":
        await help_command(update, context)
    
    elif data == "back":
        await query.edit_message_text(
            "🏠 **Main Menu**\n\n"
            "What would you like to translate?",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
        user_sessions[user_id] = {
            "source_lang": "auto",
            "target_lang": "en"
        }

# ==================== TRANSLATION FUNCTIONS (FIXED) ====================
async def translate_with_api(api_url: str, text: str, source_lang: str, target_lang: str):
    """Try translation with a specific API"""
    try:
        payload = {
            "q": text,
            "source": source_lang,
            "target": target_lang,
            "format": "text"
        }
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(api_url, json=payload, headers=headers, timeout=15) as response:
                if response.status == 200:
                    data = await response.json()
                    translated = data.get("translatedText")
                    if translated:
                        return translated
                return None
    except Exception as e:
        print(f"API error ({api_url}): {e}")
        return None

async def translate_text(text: str, source_lang: str = "auto", target_lang: str = "en"):
    """Translate text using multiple API fallbacks"""
    
    # Check if text is empty or too short
    if not text or len(text.strip()) < 1:
        return None
    
    # If source is "auto", try to detect language first
    if source_lang == "auto":
        # Try to detect language (we'll use the first word as a simple heuristic)
        # For production, you'd use a proper language detection library
        pass
    
    # Try each API in order
    for api in TRANSLATION_APIS:
        try:
            result = await translate_with_api(
                api["url"],
                text,
                source_lang,
                target_lang
            )
            if result:
                print(f"✅ Translation successful using {api['name']}")
                return result
        except Exception as e:
            print(f"❌ {api['name']} failed: {e}")
            continue
    
    # If all APIs fail, use a fallback translation method
    print("⚠️ All APIs failed, using fallback")
    return await fallback_translate(text, source_lang, target_lang)

async def fallback_translate(text: str, source_lang: str, target_lang: str):
    """Simple fallback translation using a different API"""
    try:
        # Use MyMemory translation API (free, no API key)
        url = "https://api.mymemory.translated.net/get"
        params = {
            "q": text,
            "langpair": f"{source_lang}|{target_lang}"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=15) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("responseStatus") == 200:
                        return data.get("responseData", {}).get("translatedText")
                return None
    except Exception as e:
        print(f"Fallback translation error: {e}")
        return None

# ==================== MESSAGE HANDLERS ====================
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages"""
    user_id = str(update.effective_user.id)
    text = update.message.text.strip()
    
    if user_id not in user_sessions:
        user_sessions[user_id] = {
            "source_lang": "auto",
            "target_lang": "en"
        }
    
    action = user_sessions[user_id].get("action", "")
    
    if action == "translate":
        source = user_sessions[user_id].get("source_lang", "auto")
        target = user_sessions[user_id].get("target_lang", "en")
        
        source_display = "Auto-detect" if source == "auto" else LANGUAGES.get(source, "Unknown")
        target_display = LANGUAGES.get(target, "English")
        
        # Send processing message
        processing_msg = await update.message.reply_text(
            f"🔄 **Translating...**\n\n"
            f"🔹 From: {source_display}\n"
            f"🔹 To: {target_display}\n\n"
            f"⏳ Please wait...",
            parse_mode="Markdown"
        )
        
        # Translate with fallback
        translated = await translate_text(text, source, target)
        
        if translated and translated != text:
            await processing_msg.delete()
            
            # Truncate long translations for display
            display_text = text[:300] + "..." if len(text) > 300 else text
            display_translated = translated[:300] + "..." if len(translated) > 300 else translated
            
            await update.message.reply_text(
                f"✅ **Translation Complete**\n\n"
                f"📝 **Original ({source_display}):**\n"
                f"_{display_text}_\n\n"
                f"🌍 **Translated ({target_display}):**\n"
                f"_{display_translated}_",
                parse_mode="Markdown",
                reply_markup=get_main_keyboard()
            )
        else:
            await processing_msg.edit_text(
                "❌ **Translation failed**\n\n"
                "I couldn't translate this text. Please try:\n"
                "• Using a different language\n"
                "• Sending shorter text\n"
                "• Checking your internet connection\n\n"
                "If the problem persists, contact the bot owner.",
                parse_mode="Markdown",
                reply_markup=get_main_keyboard()
            )
    
    elif action in ["voice", "document"]:
        await update.message.reply_text(
            "📝 **Please send a voice message or document**\n\n"
            "I'm ready to translate!",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
    
    else:
        # Default response
        await update.message.reply_text(
            "👋 **Send me text to translate or use the buttons below!**\n\n"
            "I support 30+ languages.",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle voice messages"""
    user_id = str(update.effective_user.id)
    
    if user_id not in user_sessions:
        user_sessions[user_id] = {
            "source_lang": "auto",
            "target_lang": "en"
        }
    
    action = user_sessions[user_id].get("action", "")
    
    if action == "voice":
        source = user_sessions[user_id].get("source_lang", "auto")
        target = user_sessions[user_id].get("target_lang", "en")
        
        source_display = "Auto-detect" if source == "auto" else LANGUAGES.get(source, "Unknown")
        target_display = LANGUAGES.get(target, "English")
        
        await update.message.reply_text(
            f"🎤 **Voice received!**\n\n"
            f"🔹 From: {source_display}\n"
            f"🔹 To: {target_display}\n\n"
            "⚠️ **Voice translation requires a speech-to-text API.**\n\n"
            "For now, you can:\n"
            "1. Use Telegram's voice-to-text feature\n"
            "2. Send the transcribed text for translation\n"
            "3. Use the 'Translate Text' option instead\n\n"
            "I'll translate text messages instantly! 🌍",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
    else:
        await update.message.reply_text(
            "🎤 **Voice message received!**\n\n"
            "Use the 'Translate Voice' button to translate voice messages.",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle document messages"""
    user_id = str(update.effective_user.id)
    
    if user_id not in user_sessions:
        user_sessions[user_id] = {
            "source_lang": "auto",
            "target_lang": "en"
        }
    
    action = user_sessions[user_id].get("action", "")
    
    if action == "document":
        document = update.message.document
        
        # Check if it's a text file
        if document.mime_type and document.mime_type.startswith("text/"):
            try:
                file = await document.get_file()
                content = await file.download_as_bytearray()
                text = content.decode('utf-8')
                
                source = user_sessions[user_id].get("source_lang", "auto")
                target = user_sessions[user_id].get("target_lang", "en")
                
                source_display = "Auto-detect" if source == "auto" else LANGUAGES.get(source, "Unknown")
                target_display = LANGUAGES.get(target, "English")
                
                # Send processing message
                processing_msg = await update.message.reply_text(
                    f"🔄 **Translating document...**\n\n"
                    f"🔹 From: {source_display}\n"
                    f"🔹 To: {target_display}\n\n"
                    f"⏳ Please wait...",
                    parse_mode="Markdown"
                )
                
                # Translate document content
                translated = await translate_text(text, source, target)
                
                if translated and translated != text:
                    await processing_msg.delete()
                    
                    # Send translated text
                    display_translated = translated[:1000] + "..." if len(translated) > 1000 else translated
                    
                    await update.message.reply_text(
                        f"✅ **Document Translation Complete**\n\n"
                        f"📄 File: {document.file_name}\n"
                        f"🌍 Translated to: {target_display}\n\n"
                        f"{display_translated}",
                        parse_mode="Markdown",
                        reply_markup=get_main_keyboard()
                    )
                else:
                    await processing_msg.edit_text(
                        "❌ **Translation failed**\n\n"
                        "Please try again with a different document.",
                        parse_mode="Markdown",
                        reply_markup=get_main_keyboard()
                    )
            except Exception as e:
                print(f"Document translation error: {e}")
                await update.message.reply_text(
                    "❌ **Error reading document**\n\n"
                    "Please make sure it's a text file (.txt).",
                    parse_mode="Markdown",
                    reply_markup=get_main_keyboard()
                )
        else:
            await update.message.reply_text(
                "📄 **Unsupported document type**\n\n"
                "Please send a .txt file for translation.",
                parse_mode="Markdown",
                reply_markup=get_main_keyboard()
            )
    else:
        await update.message.reply_text(
            "📄 **Document received!**\n\n"
            "Use the 'Translate Document' button to translate documents.",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )

# ==================== MAIN FUNCTION ====================
def main():
    """Start the bot"""
    print("🚀 Starting LinguaLinkBot...")
    print(f"🌍 Supported languages: {len(LANGUAGES)}")
    print(f"🔗 Translation APIs: {len(TRANSLATION_APIS)}")
    print("🔗 Ready to translate!")
    
    # Build application
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .connect_timeout(30.0)
        .read_timeout(30.0)
        .build()
    )
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("languages", languages_command))
    application.add_handler(CommandHandler("cancel", cancel_command))
    
    # Add callback handler for buttons
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Add message handlers
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    
    # Start the bot
    print("✅ Bot is running! Press Ctrl+C to stop.")
    application.run_polling()

if __name__ == "__main__":
    main()
