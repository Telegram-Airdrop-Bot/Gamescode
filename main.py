import os
import logging
import json
from urllib.parse import urlparse
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
    DATA_FILE = "bot_data.json"
    
    DEFAULT_CONFIG = {
        "channels": {
            "1": os.getenv("CHANNEL_1_URL", "https://t.me/+do4Tny-BtTRkMWI1"),
            "2": os.getenv("CHANNEL_2_URL", "https://t.me/+8Zv_MaEzD6JjNTk9"),
            "3": os.getenv("CHANNEL_3_URL", "https://t.me/+do4Tny-BtTRkMWI1"),
            "4": os.getenv("CHANNEL_4_URL", "https://t.me/+8Zv_MaEzD6JjNTk9"),
            "5": os.getenv("CHANNEL_5_URL", "https://t.me/+do4Tny-BtTRkMWI1")
        },
        "images": [
            os.getenv("IMAGE_1_URL", "https://i.postimg.cc/sDm5WJFb/b6c9ab57-dcf3-44bc-a69e-b83d6bbe5656.jpg"),
            os.getenv("IMAGE_2_URL", "https://i.postimg.cc/509TZw8w/photo-2025-03-28-02-00-00-2.jpg"),
            os.getenv("IMAGE_3_URL", "https://i.postimg.cc/TYQ6N4rk/photo-2025-03-25-02-48-53.jpg"),
            os.getenv("IMAGE_4_URL", "https://i.postimg.cc/509TZw8w/photo-2025-03-28-02-00-00-2.jpg"),
            os.getenv("IMAGE_5_URL", "https://i.imgur.com/RBYp6fG.jpg"),
            os.getenv("IMAGE_6_URL", "https://i.imgur.com/MYQxwrs.jpg")
        ],
        "promo_text": os.getenv("PROMO_TEXT", "🎰 Yono-777 >> BIGGEST VoucherCode Coming For All User's !! 😱😱"),
        "promo_link": os.getenv("PROMO_LINK", "https://yonopromocodes.com/"),
        "jaiho_link": os.getenv("JAIHO_LINK", "https://jaiho777agent2.com/?code=KZM38WKW22G&t=1744515002"),
        "claim_link": os.getenv("CLAIM_LINK", "https://yonopromocodes.com/claim")
    }

    @classmethod
    def validate_config(cls):
        """Validate URLs in the default configuration."""
        for key, url in cls.DEFAULT_CONFIG['channels'].items():
            if not cls.is_valid_url(url, is_channel=True):
                logger.error(f"Invalid channel URL for {key}: {url}")
                raise ValueError(f"Invalid channel URL for {key}: {url}")
        for i, url in enumerate(cls.DEFAULT_CONFIG['images'], 1):
            if not cls.is_valid_url(url):
                logger.error(f"Invalid image URL for image {i}: {url}")
                raise ValueError(f"Invalid image URL for image {i}: {url}")
        for key in ['promo_link', 'jaiho_link', 'claim_link']:
            if not cls.is_valid_url(cls.DEFAULT_CONFIG[key]):
                logger.error(f"Invalid URL for {key}: {cls.DEFAULT_CONFIG[key]}")
                raise ValueError(f"Invalid URL for {key}: {cls.DEFAULT_CONFIG[key]}")

    @staticmethod
    def is_valid_url(url: str, is_channel: bool = False) -> bool:
        """Check if a URL is valid (HTTP/HTTPS with a domain). For channels, ensure it starts with https://t.me/."""
        try:
            result = urlparse(url)
            if not all([result.scheme in ['http', 'https'], result.netloc]):
                return False
            if is_channel and not url.startswith('https://t.me/'):
                return False
            return True
        except ValueError:
            return False

    @classmethod
    def load_data(cls):
        try:
            with open(cls.DATA_FILE, 'r') as f:
                data = json.load(f)
                logger.info("Loaded data from JSON file")
                return data
        except FileNotFoundError:
            logger.warning(f"Data file {cls.DATA_FILE} not found, using default config")
            return cls.DEFAULT_CONFIG
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON from {cls.DATA_FILE}: {e}")
            return cls.DEFAULT_CONFIG
        except Exception as e:
            logger.error(f"Unexpected error loading data: {e}")
            return cls.DEFAULT_CONFIG

    @classmethod
    def save_data(cls, data):
        try:
            with open(cls.DATA_FILE, 'w') as f:
                json.dump(data, f, indent=4)
                logger.info("Saved data to JSON file")
        except Exception as e:
            logger.error(f"Error saving data to {cls.DATA_FILE}: {e}")

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
            # Check if message has photos
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
                [ 
                    InlineKeyboardButton("Coming Here", url=self.data['channels']['1'])
                ],
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
                    text='<a href="https://t.me/+P0g3FjFHmC05MDY1">Claim Fast Very Limited</a>!! 😱🤞🦁',
                    parse_mode='HTML',
                    disable_web_page_preview=True
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
                # Use up to 7 images for the gallery
                chat_id = query.message.chat_id if hasattr(query.message, "chat_id") else query.message.chat.id
                images = self.data['images'][:7]
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
        
        if not Config.is_valid_url(new_url, is_channel=True):
            await update.message.reply_text("⚠️ Invalid URL. Please provide a valid Telegram channel URL (starting with https://t.me/).")
            return EDIT_SINGLE_CHANNEL
        
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
        
        if not Config.is_valid_url(new_url):
            await update.message.reply_text("⚠️ Invalid URL. Please provide a valid HTTP/HTTPS URL.")
            return EDIT_SINGLE_IMAGE
        
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
        logger.info(f"Editing promo text with new value")
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
        if not Config.is_valid_url(new_link):
            await update.message.reply_text("⚠️ Invalid URL. Please provide a valid HTTP/HTTPS URL.")
            return EDIT_PROMO_LINK
        
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
        if not Config.is_valid_url(new_link):
            await update.message.reply_text("⚠️ Invalid URL. Please provide a valid HTTP/HTTPS URL.")
            return EDIT_JAIHO_LINK
        
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
        if not Config.is_valid_url(new_link):
            await update.message.reply_text("⚠️ Invalid URL. Please provide a valid HTTP/HTTPS URL.")
            return EDIT_CLAIM_LINK
        
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
    # Check required environment variables
    required_vars = [
        "BOT_TOKEN", "ADMIN_CHAT_ID",
        "CHANNEL_1_URL", "CHANNEL_2_URL", "CHANNEL_3_URL", "CHANNEL_4_URL", "CHANNEL_5_URL",
        "IMAGE_1_URL", "IMAGE_2_URL", "IMAGE_3_URL", "IMAGE_4_URL", "IMAGE_5_URL", "IMAGE_6_URL",
        "PROMO_LINK", "PROMO_TEXT", "JAIHO_LINK", "CLAIM_LINK"
    ]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        logger.error(f"Missing environment variables: {', '.join(missing_vars)}")
        exit(1)

    # Validate configuration
    try:
        Config.validate_config()
    except ValueError as e:
        logger.error(f"Configuration validation failed: {e}")
        exit(1)

    logger.info(f"Starting bot with ADMIN_CHAT_ID: {Config.ADMIN_CHAT_ID}")
    
    # Initialize BotHandlers
    bot_handlers = BotHandlers()

    try:
        # Build the application
        app = ApplicationBuilder().token(Config.BOT_TOKEN).build()

        # Define the ConversationHandler with bot_handlers instance methods
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

        # Add handlers to the application
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
