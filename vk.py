import time

import vkbottle
from vkbottle import Bot
from vkbottle.bot import Message
from vkbottle_types.codegen.objects import UsersUserFull

from tg import TgSenderBot


class VkListenerBot():
    # for watchdog
    error_counter = 0
    last_update_time = 0

    def __init__(self, vk_token: str, tg_sender_bot: TgSenderBot):
        self.vk: Bot = Bot(token=vk_token)
        self.tg_bot = tg_sender_bot
        #asyncio.run(self.test())

    def start_polling(self):
        #@self.vk.on.raw_event()
        #async def handler():
        #    pass
        # @self.vk.on.raw_event()
        # async def test(a):
        #     print("!")

        @self.vk.on.chat_message()
        async def message_handler(message: vkbottle.bot.Message):
            text = ""
            try:
                text = message.text
                sender_id = message.from_id
                user: UsersUserFull = (await self.vk.api.users.get(user_ids=[sender_id], fields=["screen_name"]))[0]
                sender_name: str = user.first_name + " " + user.last_name
                text = sender_name + ": " + message.text
                attachments = message.attachments
                if (len(attachments)):
                    text += " [Unknown attachment]: " + str(attachments)
            except Exception as e:
                text += " [Error while fetching more info]: " + str(e)
            print(text)
            self.tg_bot.send_text(text, TgSenderBot.TG_CHANNEL_ID, disable_notification=False, enable_html_md=False)

        while True:
            try:
                self.vk.loop_wrapper.add_task(self.watchdog_time_updater_task())
                time.sleep(4)
                self.vk.run_forever()
            except Exception as e:
                self.tg_bot.send_text("error while polling from vk bot. restarting\n"
                                      + str(e), TgSenderBot.TG_ADMIN_CHAT_ID)
                time.sleep(5)
            self.error_counter += 1

    async def watchdog_time_updater_task(self):
        self.last_update_time = time.time()
        self.tg_bot.send_text("wd_update", TgSenderBot.TG_ADMIN_CHAT_ID)
        print("wd_update")
