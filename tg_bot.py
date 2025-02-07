import time
from typing import Optional

import telebot

MAX_RETRY_COUNT = 3


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

        retries_left = MAX_RETRY_COUNT
        while retries_left > 0:
            retries_left -= 1
            time.sleep(3)  # rate limit
            try:
                self.bot.send_message(to_chat_id, text, parse_mode=parse_mode, disable_notification=disable_notification)
                break
            except Exception as e:
                if retries_left <= 0:
                    raise e

    def edit_message(self, text: str, chat_id: int, msg_id: int, enable_md: Optional[bool] = True):
        if enable_md:
            parse_mode = "Markdown"
        else:
            parse_mode = None
        self.bot.edit_message_text(text=text, chat_id=chat_id, message_id=msg_id, parse_mode=parse_mode)

    def send_photo(self, url: str, chat_id: int, text: Optional[str] = ""):
        time.sleep(3)  # rate limit
        print("sending photo:", url)

        retries_left = MAX_RETRY_COUNT
        while retries_left > 0:
            retries_left -= 1
            try:
                self.bot.send_photo(photo=url, chat_id=chat_id, caption=text)
                break
            except Exception as e:
                e.args = (str(type(e).__name__) + ", url=" + url, *e.args)
                if retries_left <= 0:
                    self.send_text("[Ошибка отправки вложения: " + url + " ]", to_chat_id=chat_id, enable_md=False)
                    raise e

    def send_doc(self, url: str, chat_id: int, text: Optional[str] = "",
                 file: Optional = None, file_name: Optional[str] = None, enable_md: Optional[bool] = False):
        time.sleep(3)  # rate limit
        print("sending doc:", url)

        if enable_md:
            parse_mode = "Markdown"
        else:
            parse_mode = None

        retries_left = MAX_RETRY_COUNT
        while retries_left > 0:
            retries_left -= 1
            try:
                if file is not None:
                    self.bot.send_document(chat_id=chat_id, document=file, visible_file_name=file_name, caption=text, parse_mode=parse_mode)
                else:
                    self.bot.send_document(chat_id=chat_id, document=url, caption=text, parse_mode=parse_mode)
                break
            except Exception as e:
                e.args = (str(type(e).__name__) + ", url=" + url, *e.args)
                if retries_left <= 0:
                    self.send_text("[Ошибка отправки вложения: " + url + " ]", to_chat_id=chat_id, enable_md=enable_md)
                    raise e
