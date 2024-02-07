import os
import time
from threading import Thread
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
            enable_html_md: Optional[bool] = True):
        if enable_html_md:
            parse_mode = "HTML"
        else:
            parse_mode = None
        self.bot.send_message(to_chat_id, text, parse_mode=parse_mode, disable_notification=disable_notification)