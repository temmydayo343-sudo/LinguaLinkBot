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

# Free Translation API (LibreTranslate - no API key needed)
LIBRE_TRANSLATE_URL = "https://libretranslate.com/translate"

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
    "af": "Afrikaans"
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
        "**Supported Languages:**\n"
        "English, Spanish, French, German, Italian, Portuguese,\n"
        "Russian, Japanese, Korean, Chinese, Arabic, Hindi,\n"
        "Dutch, Polish, Turkish, Vietnamese, Thai, Indonesian,\n"
        "Malay, Swahili, Hausa, Yoruba, Igbo, Zulu, Afrikaans\n\n"
        "📤 **How to use:**\n"
        "1. Click 'Translate Text'\n"
        "2. Choose source and target languages\n"
        "3. Send your text, voice, or document\n"
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

# ==================== TRANSLATION FUNCTION ====================
async def translate_text(text: str, source_lang: str = "auto", target_lang: str = "en"):
    """Translate text using LibreTranslate API"""
    try:
        # Prepare request
        payload = {
            "q": text,
            "source": source_lang,
            "target": target_lang,
            "format": "text"
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(LIBRE_TRANSLATE_URL, json=payload, headers=headers, timeout=30) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("translatedText", None)
                else:
                    print(f"Translation API error: {response.status}")
                    return None
    except asyncio.TimeoutError:
        print("Translation timeout")
        return None
    except Exception as e:
        print(f"Translation error: {e}")
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
        
        # Translate
        translated = await translate_text(text, source, target)
        
        if translated:
            await processing_msg.delete()
            
            # Truncate long translations for display
            display_text = text[:200] + "..." if len(text) > 200 else text
            display_translated = translated[:200] + "..." if len(translated) > 200 else translated
            
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
                "Please try again with different text.",
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
            "I support 25+ languages.",
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
        
        # Note: Voice translation requires speech-to-text API
        # For now, we'll provide a placeholder response
        await update.message.reply_text(
            f"🎤 **Voice received!**\n\n"
            f"🔹 From: {source_display}\n"
            f"🔹 To: {target_display}\n\n"
            "⚠️ **Note:** Voice translation requires a speech-to-text API.\n\n"
            "For now, you can:\n"
            "• Use the voice-to-text feature in Telegram\n"
            "• Send the transcribed text for translation\n"
            "• Use the 'Translate Text' option instead\n\n"
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
                
                if translated:
                    await processing_msg.delete()
                    
                    # Send translated text
                    await update.message.reply_text(
                        f"✅ **Document Translation Complete**\n\n"
                        f"📄 File: {document.file_name}\n"
                        f"🌍 Translated to: {target_display}\n\n"
                        f"{translated[:1000]}{'...' if len(translated) > 1000 else ''}",
                        parse_mode="Markdown",
                        reply_markup=get_main_keyboard()
                    )
                else:
                    await processing_msg.edit_text(
                        "❌ **Translation failed**\n\n"
                        "Please try again.",
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
