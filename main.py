import os
import time
from threading import Thread
from time import sleep

from dotenv import load_dotenv

from tg import TgSenderBot
from vk import VkListenerBot

send_debug = True


# will call (@) the admin if there were no checks for new messages in last 120 seconds
class Watchdog(Thread):
    def run(self):
        if send_debug:
            tg_bot.send_text("| Watchdog started", TgSenderBot.TG_ADMIN_CHAT_ID)
        while True:
            sleep(60)
            if time.time() - VkListenerBot.last_update_time > 120:
                tg_bot.send_text("<b>Seems like the bridge stopped working! Last checked for new messages: " +
                                 str(time.strftime("%a, %d %b %Y %H:%M:%S",
                                                   time.localtime(VkListenerBot.last_update_time)))
                                 + " " + os.getenv("TG_CHAT_ADMIN_USERNAME") + "</b>", TgSenderBot.TG_ADMIN_CHAT_ID)

            if VkListenerBot.error_counter >= 3:
                tg_bot.send_text("<b>Seems like the bridge stopped working! Error count: " +
                                 str(VkListenerBot.error_counter) + ". " + os.getenv(
                    "TG_CHAT_ADMIN_USERNAME") + "</b>", TgSenderBot.TG_ADMIN_CHAT_ID, disable_notification=False)
                VkListenerBot.error_counter = 0
            elif VkListenerBot.error_counter > 0:
                VkListenerBot.error_counter -= 1


load_dotenv()

tg_bot = TgSenderBot(os.getenv("TG_BOT_TOKEN"),
                     int(os.getenv("TG_CHANNEL_ID")),
                     int(os.getenv("TG_ADMIN_CHAT_ID")))
if send_debug: tg_bot.send_text("<b>| Starting...</b>", TgSenderBot.TG_ADMIN_CHAT_ID)
tg_bot.start()
print("command listener started")

watchdog = Watchdog()
#watchdog.start()  # doesn't work yet
#if send_debug: print("Watchdog started")

vk_bot_wrapper = VkListenerBot(vk_token=os.getenv("VK_BOT_TOKEN"), tg_sender_bot=tg_bot)
if send_debug: tg_bot.send_text("<b>| Starting longpolling...</b>", TgSenderBot.TG_ADMIN_CHAT_ID)
vk_bot_wrapper.start_polling()

tg_bot.send_text("<b>| Bot is stopped</b>", TgSenderBot.TG_ADMIN_CHAT_ID)
