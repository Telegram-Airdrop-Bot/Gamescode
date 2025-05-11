import os
import logging
import sqlite3
import json
from dotenv import load_dotenv
from telegram import (
    InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton,
    Update, InputMediaPhoto
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    ContextTypes, MessageHandler, filters,
    ConversationHandler
)
from telegram.error import TelegramError

# Load environment variables
load_dotenv()

# Configuration and data storage
class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
    DB_FILE = "bot_data.db"
    
    DEFAULT_CONFIG = {
        "channels": {
            "1": os.getenv("CHANNEL_1_URL", ),
            "2": os.getenv("CHANNEL_2_URL", ),
            "3": os.getenv("CHANNEL_3_URL", ),
            "4": os.getenv("CHANNEL_4_URL", ),
            "5": os.getenv("CHANNEL_5_URL", )
        },
        "images": [
            os.getenv("IMAGE_1_URL", ""),
            os.getenv("IMAGE_2_URL", ""),
            os.getenv("IMAGE_3_URL", ""),
            os.getenv("IMAGE_4_URL", ""),
            os.getenv("IMAGE_5_URL", ""),
            os.getenv("IMAGE_6_URL", "")
        ],
        "promo_text": os.getenv("PROMO_TEXT", ""),
        "promo_link": os.getenv("PROMO_LINK", ""),
        "jaiho_link": os.getenv("JAIHO_LINK", ""),
        "claim_link": os.getenv("CLAIM_LINK", "")
    }

    @classmethod
    def init_db(cls):
        """Initialize the SQLite database and create tables if they don't exist."""
        try:
            with sqlite3.connect(cls.DB_FILE) as conn:
                cursor = conn.cursor()
                # Create channels table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS channels (
                        id TEXT PRIMARY KEY,
                        url TEXT NOT NULL
                    )
                ''')
                # Create images table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS images (
                        id INTEGER PRIMARY KEY,
                        url TEXT NOT NULL
                    )
                ''')
                # Create texts table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS texts (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL
                    )
                ''')
                conn.commit()
                
                # Check if tables are empty and populate with default data
                cursor.execute("SELECT COUNT(*) FROM channels")
                if cursor.fetchone()[0] == 0:
                    for id, url in cls.DEFAULT_CONFIG["channels"].items():
                        cursor.execute("INSERT INTO channels (id, url) VALUES (?, ?)", (id, url))
                
                cursor.execute("SELECT COUNT(*) FROM images")
                if cursor.fetchone()[0] == 0:
                    for idx, url in enumerate(cls.DEFAULT_CONFIG["images"], 1):
                        cursor.execute("INSERT INTO images (id, url) VALUES (?, ?)", (idx, url))
                
                cursor.execute("SELECT COUNT(*) FROM texts")
                if cursor.fetchone()[0] == 0:
                    text_fields = [
                        ("promo_text", cls.DEFAULT_CONFIG["promo_text"]),
                        ("promo_link", cls.DEFAULT_CONFIG["promo_link"]),
                        ("jaiho_link", cls.DEFAULT_CONFIG["jaiho_link"]),
                        ("claim_link", cls.DEFAULT_CONFIG["claim_link"])
                    ]
                    cursor.executemany("INSERT INTO texts (key, value) VALUES (?, ?)", text_fields)
                
                conn.commit()
                logger.info("Database initialized successfully")
        except sqlite3.Error as e:
            logger.error(f"Error initializing database: {e}")
            raise

    @classmethod
    def load_data(cls):
        """Load data from SQLite database."""
        try:
            with sqlite3.connect(cls.DB_FILE) as conn:
                cursor = conn.cursor()
                
                # Load channels
                cursor.execute("SELECT id, url FROM channels")
                channels = {row[0]: row[1] for row in cursor.fetchall()}
                
                # Load images
                cursor.execute("SELECT url FROM images ORDER BY id")
                images = [row[0] for row in cursor.fetchall()]
                
                # Load texts
                cursor.execute("SELECT key, value FROM texts")
                texts = {row[0]: row[1] for row in cursor.fetchall()}
                
                data = {
                    "channels": channels,
                    "images": images,
                    "promo_text": texts.get("promo_text", cls.DEFAULT_CONFIG["promo_text"]),
                    "promo_link": texts.get("promo_link", cls.DEFAULT_CONFIG["promo_link"]),
                    "jaiho_link": texts.get("jaiho_link", cls.DEFAULT_CONFIG["jaiho_link"]),
                    "claim_link": texts.get("claim_link", cls.DEFAULT_CONFIG["claim_link"])
                }
                
                logger.info(f"Loaded data from database: {data}")
                return data
        except sqlite3.Error as e:
            logger.error(f"Error loading data from database: {e}")
            return cls.DEFAULT_CONFIG

    @classmethod
    def save_data(cls, data):
        """Save data to SQLite database."""
        try:
            with sqlite3.connect(cls.DB_FILE) as conn:
                cursor = conn.cursor()
                
                # Save channels
                for id, url in data["channels"].items():
                    cursor.execute("INSERT OR REPLACE INTO channels (id, url) VALUES (?, ?)", (id, url))
                
                # Save images
                cursor.execute("DELETE FROM images")  # Clear existing images
                for idx, url in enumerate(data["images"], 1):
                    cursor.execute("INSERT INTO images (id, url) VALUES (?, ?)", (idx, url))
                
                # Save texts
                text_fields = [
                    ("promo_text", data["promo_text"]),
                    ("promo_link", data["promo_link"]),
                    ("jaiho_link", data["jaiho_link"]),
                    ("claim_link", data["claim_link"])
                ]
                cursor.executemany("INSERT OR REPLACE INTO texts (key, value) VALUES (?, ?)", text_fields)
                
                conn.commit()
                logger.info(f"Saved data to database: {data}")
        except sqlite3.Error as e:
            logger.error(f"Error saving data to database: {e}")

# Admin conversation states
(
    ADMIN_START,
    EDIT_CHOOSE_OPTION,
    EDIT_CHANNELS,
    EDIT_IMAGES,
    EDIT_TEXTS,
    EDIT_SINGLE_CHANNEL,
    EDIT_SINGLE_IMAGE,
    EDIT_PROMO_TEXT,
    EDIT_PROMO_LINK,
    EDIT_JAIHO_LINK,
    EDIT_CLAIM_LINK
) = range(11)

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class BotHandlers:
    def __init__(self):
        Config.init_db()  # Initialize the database
        self.data = Config.load_data()

    def save_config(self):
        Config.save_data(self.data)

    def is_admin(self, update: Update):
        user_id = str(update.effective_user.id)
        logger.info(f"Checking admin access: User ID = {user_id}, ADMIN_CHAT_ID = {Config.ADMIN_CHAT_ID}")
        return user_id == Config.ADMIN_CHAT_ID

    async def handle_start_with_images(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        message = update.message
        
        try:
            if message.photo:
                photos = message.photo
                if len(photos) == 3:
                    file_ids = [photo.file_id for photo in photos]
                    media_group = [
                        InputMediaPhoto(media=file_ids[0]),
                        InputMediaPhoto(media=file_ids[1]),
                        InputMediaPhoto(media=file_ids[2])
                    ]
                    await context.bot.send_media_group(chat_id=chat_id, media=media_group)
                    
                    if message.caption:
                        await context.bot.send_message(
                            chat_id=chat_id,
                            text=message.caption
                        )
                    
                    await self.send_promo_message(update, context)
                    return
            
            await self.start(update, context)
            
        except TelegramError as e:
            logger.error(f"Error in handle_start_with_images: {e}")
            await context.bot.send_message(
                chat_id=chat_id,
                text="⚠️ An error occurred. Please try again later."
            )

    async def send_promo_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        try:
            text = (
                f"{self.data['promo_text']}\n"
                "👇👇👇👇👇👇👇👇👇👇👇\n\n"
                "👉 6 Free Spin Milegi (💰 ₹5 Bet )\n\n"
                f"✅ App Link >> {self.data['promo_link']}\n\n"
                "❤️ Jaldi-Jaldi Claim Karo !! 👇👇"
            )

            inline_keyboard = [
                [InlineKeyboardButton("Coming Here", url=self.data['channels']['1'])],
                [
                    InlineKeyboardButton("🎯 Join ✅", url=self.data['channels']['2']),
                    InlineKeyboardButton("🎯 Join ✅", url=self.data['channels']['3'])
                ],
                [
                    InlineKeyboardButton("🎯 Join ✅", url=self.data['channels']['4']),
                    InlineKeyboardButton("🎯 Join ✅", url=self.data['channels']['5'])
                ],
                [InlineKeyboardButton("✅ Claim", callback_data="claim")]
            ]
            reply_markup = InlineKeyboardMarkup(inline_keyboard)

            await context.bot.send_photo(
                chat_id=chat_id,
                photo=self.data['images'][0],
                caption=text,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )

            custom_keyboard = [
                [KeyboardButton("Yono 777"), KeyboardButton("BIG PromoCode")],
                [KeyboardButton("Jaiho Arcade"), KeyboardButton("Lucky Gullak")]
            ]
            reply_markup_custom = ReplyKeyboardMarkup(custom_keyboard, resize_keyboard=True)
            await context.bot.send_message(
                chat_id=chat_id,
                text="Select an option below:",
                reply_markup=reply_markup_custom
            )

        except TelegramError as e:
            logger.error(f"Error in send_promo_message: {e}")
            await context.bot.send_message(
                chat_id=chat_id,
                text="⚠️ An error occurred. Please try again later."
            )

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.send_promo_message(update, context)

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        try:
            if query.data == "claim":
                chat_id = query.message.chat_id if hasattr(query.message, "chat_id") else query.message.chat.id
                images = self.data['images'][:7]  # Use up to 7 images
                media_group = [InputMediaPhoto(media=img) for img in images]
                if media_group:
                    await context.bot.send_media_group(chat_id=chat_id, media=media_group)

                text = (
                    f"{self.data['promo_text']}\n"
                    "👇👇👇👇👇👇👇👇👇👇👇\n\n"
                    "👉 6 Free Spin Milegi (( ₹5 Bet ))\n\n"
                    f"✅ App Link >> {self.data['promo_link']}\n\n"
                    "❤️ Jaldi-Jaldi Claim Karo !! 👇👇"
                )
                inline_keyboard = [
                    [
                        InlineKeyboardButton("🎯 Join ✅", url=self.data['channels']['2']),
                        InlineKeyboardButton("🎯 Join ✅", url=self.data['channels']['3'])
                    ],
                    [
                        InlineKeyboardButton("🎯 Join ✅", url=self.data['channels']['4']),
                        InlineKeyboardButton("🎯 Join ✅", url=self.data['channels']['5'])
                    ],
                    [InlineKeyboardButton("Continue", url=self.data['channels']['1'])]
                ]
                reply_markup = InlineKeyboardMarkup(inline_keyboard)
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    reply_markup=reply_markup
                )
                await context.bot.send_message(
                    chat_id=chat_id,
                    text='<a href="https://t.me/+P0g3FjFHmC05MDY1">Claim Fast Very Limited</a>!! 😱🤞🦁',
                    parse_mode='HTML',
                    disable_web_page_preview=True
                )

        except TelegramError as e:
            logger.error(f"Error in button_callback: {e}")
            await query.message.reply_text("⚠️ An error occurred. Please try again.")

    async def handle_url_click(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        user = update.effective_user.to_dict()
        
        if Config.ADMIN_CHAT_ID:
            try:
                await context.bot.send_message(
                    chat_id=int(Config.ADMIN_CHAT_ID),
                    text=(
                        f"🚨 New user interaction!\n"
                        f"User: {user.get('first_name', 'Unknown')}\n"
                        f"Username: @{user.get('username', 'N/A')}\n"
                        f"User ID: {user.get('id', 'N/A')}"
                    )
                )
            except Exception as e:
                logger.error(f"Error notifying admin: {e}")

    async def custom_keyboard_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        button_image_map = {
            "Yono 777": 0,
            "BIG PromoCode": 1,
            "Jaiho Arcade": 2,
            "Lucky Gullak": 3
        }
        
        try:
            chat_id = update.effective_chat.id
            button_text = update.message.text
            
            if button_text not in button_image_map:
                await update.message.reply_text("⚠️ Invalid selection. Please choose a valid option.")
                return
            
            image_index = button_image_map[button_text]
            
            text = (
                f"{self.data['promo_text']}\n"
                "👇👇👇👇👇👇👇👇👇👇👇\n\n"
                "👉 6 Free Spin Milegi (💰 ₹5 Bet )\n\n"
                f"✅ App Link >> {self.data['promo_link']}\n\n"
                "❤️ Jaldi-Jaldi Claim Karo !! 👇👇"
            )
            inline_keyboard = [
                [
                    InlineKeyboardButton("🎯 Join ✅", url=self.data['channels']['2']),
                    InlineKeyboardButton("🎯 Join ✅", url=self.data['channels']['3'])
                ],
                [
                    InlineKeyboardButton("🎯 Join ✅", url=self.data['channels']['4']),
                    InlineKeyboardButton("🎯 Join ✅", url=self.data['channels']['5'])
                ],
                [InlineKeyboardButton("✅ Claim", callback_data="claim")]
            ]
            reply_markup = InlineKeyboardMarkup(inline_keyboard)
            
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=self.data['images'][image_index],
                caption=text,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
        except TelegramError as e:
            logger.error(f"Error in custom_keyboard_handler: {e}")
            await update.message.reply_text("⚠️ An error occurred. Please try again.")

    async def admin_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.info(f"Admin command received from user: {update.effective_user.id}")
        if not self.is_admin(update):
            await update.message.reply_text("⛔ Unauthorized access!")
            return ConversationHandler.END

        try:
            keyboard = [
                [InlineKeyboardButton("📢 Edit Channels", callback_data='edit_channels')],
                [InlineKeyboardButton("🖼️ Edit Images", callback_data='edit_images')],
                [InlineKeyboardButton("📝 Edit Texts", callback_data='edit_texts')],
                [InlineKeyboardButton("❌ Cancel", callback_data='cancel')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "🛠️ Admin Panel - Choose what to edit:",
                reply_markup=reply_markup
            )
            return EDIT_CHOOSE_OPTION
        except TelegramError as e:
            logger.error(f"Telegram error in admin_start: {e}")
            await update.message.reply_text("⚠️ An error occurred. Please try again.")
            return ConversationHandler.END

    async def admin_choose_option(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        logger.info(f"Admin chose option: {query.data}")
        
        try:
            if query.data == 'edit_channels':
                keyboard = [
                    [InlineKeyboardButton(f"Channel 1: {self.data['channels']['1'][:20]}...", callback_data='edit_channel_1')],
                    [InlineKeyboardButton(f"Channel 2: {self.data['channels']['2'][:20]}...", callback_data='edit_channel_2')],
                    [InlineKeyboardButton(f"Channel 3: {self.data['channels']['3'][:20]}...", callback_data='edit_channel_3')],
                    [InlineKeyboardButton(f"Channel 4: {self.data['channels']['4'][:20]}...", callback_data='edit_channel_4')],
                    [InlineKeyboardButton(f"Channel 5: {self.data['channels']['5'][:20]}...", callback_data='edit_channel_5')],
                    [InlineKeyboardButton("🔙 Back", callback_data='back')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    "📢 Select channel to edit:",
                    reply_markup=reply_markup
                )
                return EDIT_CHANNELS
            
            elif query.data == 'edit_images':
                keyboard = []
                for i, img in enumerate(self.data['images'], 1):
                    keyboard.append([InlineKeyboardButton(f"Image {i}: {img[:20]}...", callback_data=f'edit_image_{i}')])
                keyboard.append([InlineKeyboardButton("🔙 Back", callback_data='back')])
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    "🖼️ Select image to edit:",
                    reply_markup=reply_markup
                )
                return EDIT_IMAGES
            
            elif query.data == 'edit_texts':
                keyboard = [
                    [InlineKeyboardButton(f"Promo Text: {self.data['promo_text'][:20]}...", callback_data='edit_promo_text')],
                    [InlineKeyboardButton(f"Promo Link: {self.data['promo_link'][:20]}...", callback_data='edit_promo_link')],
                    [InlineKeyboardButton(f"JaiHo Link: {self.data['jaiho_link'][:20]}...", callback_data='edit_jaiho_link')],
                    [InlineKeyboardButton(f"Claim Link: {self.data['claim_link'][:20]}...", callback_data='edit_claim_link')],
                    [InlineKeyboardButton("🔙 Back", callback_data='back')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    "📝 Select text to edit:",
                    reply_markup=reply_markup
                )
                return EDIT_TEXTS
            
            elif query.data == 'cancel':
                await query.edit_message_text("Admin panel closed.")
                return ConversationHandler.END
        except TelegramError as e:
            logger.error(f"Telegram error in admin_choose_option: {e}")
            await query.message.reply_text("⚠️ An error occurred. Please try again.")
            return ConversationHandler.END

    async def edit_channels(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        try:
            if query.data.startswith('edit_channel_'):
                channel_num = query.data.split('_')[-1]
                context.user_data['editing_channel'] = channel_num
                await query.edit_message_text(f"Enter new URL for Channel {channel_num}:")
                return EDIT_SINGLE_CHANNEL
            elif query.data == 'back':
                return await self.admin_start(update, context)
        except TelegramError as e:
            logger.error(f"Telegram error in edit_channels: {e}")
            await query.message.reply_text("⚠️ An error occurred. Please try again.")
            return ConversationHandler.END

    async def edit_single_channel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.info(f"Editing channel {context.user_data['editing_channel']} with new URL: {update.message.text}")
        new_url = update.message.text
        channel_num = context.user_data['editing_channel']
        
        try:
            self.data['channels'][channel_num] = new_url
            self.save_config()
            
            await update.message.reply_text(f"✅ Channel {channel_num} updated successfully!")
            return await self.admin_start(update, context)
        except Exception as e:
            logger.error(f"Error in edit_single_channel: {e}")
            await update.message.reply_text("⚠️ An error occurred. Please try again.")
            return ConversationHandler.END

    async def edit_images(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        try:
            if query.data.startswith('edit_image_'):
                img_num = int(query.data.split('_')[-1]) - 1
                context.user_data['editing_image'] = img_num
                await query.edit_message_text(f"Enter new URL for Image {img_num + 1}:")
                return EDIT_SINGLE_IMAGE
            elif query.data == 'back':
                return await self.admin_start(update, context)
        except TelegramError as e:
            logger.error(f"Telegram error in edit_images: {e}")
            await query.message.reply_text("⚠️ An error occurred. Please try again.")
            return ConversationHandler.END

    async def edit_single_image(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.info(f"Editing image {context.user_data['editing_image'] + 1} with new URL: {update.message.text}")
        new_url = update.message.text
        img_num = context.user_data['editing_image']
        
        try:
            self.data['images'][img_num] = new_url
            self.save_config()
            
            await update.message.reply_text(f"✅ Image {img_num + 1} updated successfully!")
            return await self.admin_start(update, context)
        except Exception as e:
            logger.error(f"Error in edit_single_image: {e}")
            await update.message.reply_text("⚠️ An error occurred. Please try again.")
            return ConversationHandler.END

    async def edit_texts(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        try:
            if query.data == 'edit_promo_text':
                await query.edit_message_text(f"Current promo text:\n{self.data['promo_text']}\n\nEnter new promo text:")
                return EDIT_PROMO_TEXT
            elif query.data == 'edit_promo_link':
                await query.edit_message_text(f"Current promo link:\n{self.data['promo_link']}\n\nEnter new promo link:")
                return EDIT_PROMO_LINK
            elif query.data == 'edit_jaiho_link':
                await query.edit_message_text(f"Current JaiHo link:\n{self.data['jaiho_link']}\n\nEnter new JaiHo link:")
                return EDIT_JAIHO_LINK
            elif query.data == 'edit_claim_link':
                await query.edit_message_text(f"Current claim link:\n{self.data['claim_link']}\n\nEnter new claim link:")
                return EDIT_CLAIM_LINK
            elif query.data == 'back':
                return await self.admin_start(update, context)
        except TelegramError as e:
            logger.error(f"Telegram error in edit_texts: {e}")
            await query.message.reply_text("⚠️ An error occurred. Please try again.")
            return ConversationHandler.END

    async def edit_promo_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.info(f"Editing promo text with new value: {update.message.text}")
        new_text = update.message.text
        try:
            self.data['promo_text'] = new_text
            self.save_config()
            await update.message.reply_text("✅ Promo text updated successfully!")
            return await self.admin_start(update, context)
        except Exception as e:
            logger.error(f"Error in edit_promo_text: {e}")
            await update.message.reply_text("⚠️ An error occurred. Please try again.")
            return ConversationHandler.END

    async def edit_promo_link(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.info(f"Editing promo link with new value: {update.message.text}")
        new_link = update.message.text
        try:
            self.data['promo_link'] = new_link
            self.save_config()
            await update.message.reply_text("✅ Promo link updated successfully!")
            return await self.admin_start(update, context)
        except Exception as e:
            logger.error(f"Error in edit_promo_link: {e}")
            await update.message.reply_text("⚠️ An error occurred. Please try again.")
            return ConversationHandler.END

    async def edit_jaiho_link(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.info(f"Editing JaiHo link with new value: {update.message.text}")
        new_link = update.message.text
        try:
            self.data['jaiho_link'] = new_link
            self.save_config()
            await update.message.reply_text("✅ JaiHo link updated successfully!")
            return await self.admin_start(update, context)
        except Exception as e:
            logger.error(f"Error in edit_jaiho_link: {e}")
            await update.message.reply_text("⚠️ An error occurred. Please try again.")
            return ConversationHandler.END

    async def edit_claim_link(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.info(f"Editing claim link with new value: {update.message.text}")
        new_link = update.message.text
        try:
            self.data['claim_link'] = new_link
            self.save_config()
            await update.message.reply_text("✅ Claim link updated successfully!")
            return await self.admin_start(update, context)
        except Exception as e:
            logger.error(f"Error in edit_claim_link: {e}")
            await update.message.reply_text("⚠️ An error occurred. Please try again.")
            return ConversationHandler.END

    async def cancel_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            await update.message.reply_text("Admin panel closed.")
            return ConversationHandler.END
        except TelegramError as e:
            logger.error(f"Error in cancel_admin: {e}")
            await update.message.reply_text("⚠️ An error occurred. Please try again.")
            return ConversationHandler.END

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.error(f"Update {update} caused error {context.error}")
        try:
            if update.message:
                await update.message.reply_text("⚠️ An error occurred. Please try again or use /cancel to exit.")
            elif update.callback_query:
                await update.callback_query.message.reply_text("⚠️ An error occurred. Please try again or use /cancel to exit.")
        except TelegramError as e:
            logger.error(f"Error in error_handler: {e}")
        return ConversationHandler.END

def main():
    if not Config.BOT_TOKEN:
        logger.error("Error: BOT_TOKEN not found in environment variables")
        exit(1)
    if not Config.ADMIN_CHAT_ID:
        logger.error("Error: ADMIN_CHAT_ID not found in environment variables")
        exit(1)

    logger.info(f"BOT_TOKEN: {Config.BOT_TOKEN}")
    logger.info(f"ADMIN_CHAT_ID: {Config.ADMIN_CHAT_ID}")

    bot_handlers = BotHandlers()

    try:
        app = ApplicationBuilder().token(Config.BOT_TOKEN).build()

        admin_conv_handler = ConversationHandler(
            entry_points=[CommandHandler('admin', bot_handlers.admin_start)],
            states={
                ADMIN_START: [CallbackQueryHandler(bot_handlers.admin_choose_option)],
                EDIT_CHOOSE_OPTION: [CallbackQueryHandler(bot_handlers.admin_choose_option)],
                EDIT_CHANNELS: [CallbackQueryHandler(bot_handlers.edit_channels)],
                EDIT_IMAGES: [CallbackQueryHandler(bot_handlers.edit_images)],
                EDIT_TEXTS: [CallbackQueryHandler(bot_handlers.edit_texts)],
                EDIT_SINGLE_CHANNEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot_handlers.edit_single_channel)],
                EDIT_SINGLE_IMAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot_handlers.edit_single_image)],
                EDIT_PROMO_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot_handlers.edit_promo_text)],
                EDIT_PROMO_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot_handlers.edit_promo_link)],
                EDIT_JAIHO_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot_handlers.edit_jaiho_link)],
                EDIT_CLAIM_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot_handlers.edit_claim_link)],
            },
            fallbacks=[
                CommandHandler('cancel', bot_handlers.cancel_admin),
                MessageHandler(filters.COMMAND, bot_handlers.cancel_admin)
            ],
            per_message=False
        )

        app.add_handler(CommandHandler("start", bot_handlers.handle_start_with_images))
        app.add_handler(CallbackQueryHandler(bot_handlers.button_callback))
        app.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            bot_handlers.custom_keyboard_handler
        ))
        app.add_handler(MessageHandler(
            filters.ALL & ~filters.COMMAND,
            bot_handlers.handle_url_click
        ))
        app.add_handler(admin_conv_handler)
        app.add_error_handler(bot_handlers.error_handler)

        logger.info("Bot is starting...")
        app.run_polling()

    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        exit(1)

if __name__ == "__main__":
    main()
