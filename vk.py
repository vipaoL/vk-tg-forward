import time

import vkbottle
from vkbottle import Bot, LoopWrapper
from vkbottle.bot import Message
from vkbottle_types.codegen.objects import UsersUserFull

import utils
from tg_bot import TgBot


class VkListenerBot:
    is_stopped = False

    def __init__(self, vk_token: str, vk_target_chat_id: int, tg_sender_bot: TgBot):
        self.vk: Bot = Bot(token=vk_token)
        self.vk_target_chat_id = vk_target_chat_id
        self.tg_bot = tg_sender_bot
        #asyncio.run(self.test())

    def start_polling(self):
        self.is_stopped = False
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
            print(message.chat_id, text)
            if message.chat_id == self.vk_target_chat_id:
                self.tg_bot.send_text(text, TgBot.TG_CHANNEL_ID, disable_notification=False, enable_html_md=False)
            else:
                self.tg_bot.send_text(text, TgBot.TG_ADMIN_CHAT_ID, disable_notification=False, enable_html_md=False)

        while not self.is_stopped:
            try:
                self.vk.run_forever()
            except Exception as e:
                self.tg_bot.send_text("error while polling from vk bot. restarting\n"
                                      + str(e), TgBot.TG_ADMIN_CHAT_ID)
                time.sleep(5)

    def stop(self):
        self.is_stopped = True
        self.vk.loop.stop()

    async def watchdog_time_updater_task(self):
        self.last_update_time = time.time()
        #await self.tg_bot.send_text("wd_update", TgSenderBot.TG_ADMIN_CHAT_ID)
        print("wd_update")

    def get_last_update_time(self):
        try:
            last_event_fetch_time = self.vk.polling.get_last_event_fetch_time()
        except AttributeError as e:
            print(e)
            print("!!!!!!!!!!!!![use fork of vkbottle. watchdog is not working]!!!!!!!!!!!!!!")
            last_event_fetch_time = time.time()
        return last_event_fetch_time

    def get_last_update_time_str(self) -> str:
        return utils.get_last_update_time_str(self.get_last_update_time())
