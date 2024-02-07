import os
import time
from threading import Thread
from typing import Optional

import telebot


class TgSenderBot(Thread):
    TG_CHANNEL_ID = None
    TG_ADMIN_CHAT_ID = None

    def __init__(self, tg_bot_token: str, channel_id: int, admin_chat_id: int):
        super().__init__()
        self.bot = telebot.TeleBot(tg_bot_token)
        TgSenderBot.TG_CHANNEL_ID = channel_id
        TgSenderBot.TG_ADMIN_CHAT_ID = admin_chat_id
        #asyncio.run(self.test())

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

    def run(self):
        @self.bot.message_handler(content_types=['text'])
        def handle_text_message(message: telebot.types.Message):
            text = str(message.text)
            if text.startswith("/"):
                text = text[1:]
                bot_tag = "@" + self.bot.get_me().username
                if text.endswith(bot_tag):
                    text = text[:-len(bot_tag)]
                self.handle_command(command=text, from_chat_id=message.chat.id, from_user=message.from_user)

        while True:
            try:
                self.bot.polling(none_stop=True, interval=0)
            except Exception as e:
                print("error while polling commands from tg bot. restarting\n", e)
                time.sleep(5)

    def handle_command(self, command: str, from_chat_id, from_user):
        print(command, from_chat_id, from_user)
        if command == "status":
            self.bot.send_message(from_chat_id, "Not implemented yet")
        else:
            if from_chat_id == os.getenv("TG_ADMIN_CHAT_ID"):
                if command == "stop":
                    self.send_text("Got \"/stop\". Stopping... " + os.getenv("TG_CHAT_ADMIN_USERNAME"),
                                   TgSenderBot.TG_ADMIN_CHAT_ID, disable_notification=False)
                    self.send_text("Stopping...", from_chat_id)
                    exit(0)
            self.send_text("unknown command: " + command, from_chat_id)
