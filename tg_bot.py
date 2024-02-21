import time
from typing import Optional

import telebot


class TgBot:
    TG_CHANNEL_ID: int = None
    TG_ADMIN_CHAT_ID: int = None

    def __init__(self, tg_bot_token: str, channel_id: int, admin_chat_id: int):
        self.bot = telebot.TeleBot(tg_bot_token)
        TgBot.TG_CHANNEL_ID = channel_id
        TgBot.TG_ADMIN_CHAT_ID = admin_chat_id

    def send_text(
            self,
            text,
            to_chat_id,
            disable_notification: Optional[bool] = True,
            enable_md: Optional[bool] = True):
        if enable_md:
            parse_mode = "Markdown"
        else:
            parse_mode = None
        time.sleep(3)  # rate limit
        self.bot.send_message(to_chat_id, text, parse_mode=parse_mode, disable_notification=disable_notification)

    def edit_message(self, text: str, chat_id: int, msg_id: int, enable_md: Optional[bool] = True):
        if enable_md:
            parse_mode = "Markdown"
        else:
            parse_mode = None
        self.bot.edit_message_text(text=text, chat_id=chat_id, message_id=msg_id, parse_mode=parse_mode)

    def send_photo(self, url: str, chat_id: int):
        time.sleep(3)  # rate limit
        print("sending photo:", url)
        self.bot.send_photo(photo=url, chat_id=chat_id)
