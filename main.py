import os
import time
from threading import Thread
from time import sleep

import telebot
from dotenv import load_dotenv

import utils
from tg_bot import TgBot
from vk import VkListenerBot

import logging

send_debug = False
is_stopped = False


# will call (@) the admin if there were no checks for new messages in last 120 seconds
class Watchdog(Thread):
    def __init__(self, pinned_msg_id: int):
        super().__init__()
        self.pinned_msg_id = pinned_msg_id

    def run(self):
        print("Watchdog: run()")
        if send_debug:
            tg_bot.send_text("| Watchdog started", TgBot.TG_ADMIN_CHAT_ID)
        while not is_stopped:
            try:
                for i in range(60):
                    if not is_stopped:
                        sleep(1)
                last_update_time = vk_bot_wrapper.get_last_update_time()

                if time.time() - last_update_time > 120:
                    tg_bot.send_text("<b>Seems like the bridge stopped working! Last checked for new messages: " +
                                     vk_bot_wrapper.get_last_update_time_str()
                                     + " " + os.getenv("TG_CHAT_ADMIN_USERNAME") + "</b>", TgBot.TG_ADMIN_CHAT_ID)
                self.update_status_in_pinned(last_update_time)
            except Exception as e:
                if send_debug: tg_bot.send_text("Err in wd " + str(e), TgBot.TG_ADMIN_CHAT_ID)

    def update_status_in_pinned(self, last_time: int):
        text = ""
        if is_stopped:
            text += "<b>Stopped.</b> "
        text += utils.get_last_update_time_str(last_time) + " - last update"
        print("edit", text, self.pinned_msg_id)
        tg_bot.edit_message(text=text,
                            chat_id=TgBot.TG_CHANNEL_ID,
                            msg_id=self.pinned_msg_id)


class TgCommandListener(Thread):
    def __init__(self, tg_bot: TgBot, vk_bot: VkListenerBot):
        super().__init__()
        self.tg_bot_wrapper = tg_bot
        self.tg_bot = tg_bot.bot
        self.vk_bot = vk_bot

    def run(self):
        print("TgCommandListener: run()")
        @self.tg_bot.message_handler(content_types=['text'])
        def handle_text_message(message: telebot.types.Message):
            text = str(message.text)
            if text.startswith("/"):
                text = text[1:]
                bot_tag = "@" + self.tg_bot.get_me().username
                if text.endswith(bot_tag):
                    text = text[:-len(bot_tag)]
                self.handle_command(command=text, from_chat_id=message.chat.id, from_user=message.from_user)

        while not is_stopped:
            try:
                self.tg_bot.polling(none_stop=True, interval=0)
            except Exception as e:
                print("error while polling commands from tg bot. restarting\n", e)
                time.sleep(5)

    def handle_command(self, command: str, from_chat_id, from_user):
        print(command, from_chat_id, from_user)
        if command == "status":
            self.tg_bot.send_message(from_chat_id, "Last update: " + self.vk_bot.get_last_update_time_str())
        elif command == "stop":
            if from_chat_id == TgBot.TG_ADMIN_CHAT_ID:
                self.tg_bot_wrapper.send_text(
                    "| Got \"/stop\". Stopping... " + os.getenv("TG_CHAT_ADMIN_USERNAME"),
                    TgBot.TG_ADMIN_CHAT_ID,
                    disable_notification=False)

                if from_chat_id != TgBot.TG_ADMIN_CHAT_ID:
                    self.tg_bot_wrapper.send_text("Stopping...", from_chat_id)
                global is_stopped
                is_stopped = True
                vk_bot_wrapper.stop()
                tg_bot.bot.stop_polling()
        else:
            self.tg_bot_wrapper.send_text("unknown command: " + command, from_chat_id)


logging.disable(logging.DEBUG)

load_dotenv()

tg_bot = TgBot(os.getenv("TG_BOT_TOKEN"),
               int(os.getenv("TG_CHANNEL_ID")),
               int(os.getenv("TG_ADMIN_CHAT_ID")))
tg_bot.send_text("<b>| Starting...</b>", TgBot.TG_ADMIN_CHAT_ID)

watchdog = Watchdog(int(os.getenv("TG_CHANNEL_PINNED_MSG_ID")))
watchdog.start()
if send_debug: tg_bot.send_text("| Watchdog started", TgBot.TG_ADMIN_CHAT_ID)

vk_bot_wrapper = VkListenerBot(vk_token=os.getenv("VK_BOT_TOKEN"),
                               vk_target_chat_id=int(os.getenv("VK_TARGET_CHAT_ID")),
                               tg_sender_bot=tg_bot)

command_listener = TgCommandListener(tg_bot, vk_bot_wrapper)
command_listener.start()
if send_debug: tg_bot.send_text("| Command listener started", TgBot.TG_ADMIN_CHAT_ID)

if send_debug: tg_bot.send_text("| Starting longpolling...", TgBot.TG_ADMIN_CHAT_ID)
vk_bot_wrapper.start_polling()

is_stopped = True
tg_bot.send_text("<b>| Bot is stopped</b>", TgBot.TG_ADMIN_CHAT_ID)
tg_bot.bot.stop_bot()
