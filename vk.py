import time
import traceback

import vkbottle
from vkbottle import Bot
from vkbottle.bot import Message
from vkbottle.tools.dev.mini_types.bot.foreign_message import ForeignMessageMin
from vkbottle_types.codegen.objects import UsersUserFull
from vkbottle_types.objects import MessagesMessageAttachmentType, MessagesMessageAttachment

import utils
from tg_bot import TgBot


class VkListenerBot:
    is_stopped = False

    def __init__(self, vk_token: str, vk_target_chat_id: int, tg_sender_bot: TgBot):
        self.vk: Bot = Bot(token=vk_token)
        self.vk_target_chat_id = vk_target_chat_id
        self.tg_bot = tg_sender_bot

    def start_polling(self):
        print("VkListenerBot: start_polling()")
        self.is_stopped = False

        async def on_shutdown_task():
            print("on_shutdown_task()")
            self.is_stopped = True

        self.vk.loop_wrapper.on_shutdown.insert(0, on_shutdown_task())

        @self.vk.on.chat_message()
        async def message_handler(message: vkbottle.bot.Message):
            text = ""
            if message.chat_id == self.vk_target_chat_id:
                to_tg_id = TgBot.TG_CHANNEL_ID
            else:
                to_tg_id = TgBot.TG_ADMIN_CHAT_ID
                text += "From chat id" + str(message.chat_id) + ": "
            await self.handle_message(text, message, to_tg_id)

        while not self.is_stopped:
            print("starting vk polling")
            try:
                self.vk.run_forever()
            except Exception as e:
                self.tg_bot.send_text("error while polling from vk bot. restarting\n"
                                      + str(e), TgBot.TG_ADMIN_CHAT_ID)
            if not self.is_stopped:
                time.sleep(5)
        print("VkListenerBot: stopped")

    async def handle_message(self, base_text: str, message: vkbottle.bot.Message, to_tg_id: int):
        base_text = base_text
        try:
            base_text += message.text
            sender_id = message.from_id
            user: UsersUserFull = (await self.vk.api.users.get(user_ids=[sender_id], fields=["screen_name"]))[0]
            sender_name: str = user.first_name + " " + user.last_name
            base_text = sender_name + ": " + base_text
            base_text += self.handle_attachments(message.attachments, to_tg_id)
            base_text += (await self.handle_forwarded(message.fwd_messages, to_tg_id))
        except Exception as ex:
            base_text += " [Error while fetching more info]: " + str(ex)
            traceback.print_tb(ex.__traceback__)
        print(message.chat_id, base_text)
        self.tg_bot.send_text(base_text, to_tg_id, disable_notification=False, enable_md=False)

    async def handle_forwarded(self, forwarded: list[ForeignMessageMin], to_tg_id: int) -> str:
        if forwarded == None or len(forwarded) < 1:
            return ""
        for fwd_message in forwarded:
            await self.handle_message("↩️ ", fwd_message, to_tg_id)

        return str(" [" + str(len(forwarded)) + " forwarded]")

    def handle_attachments(self, attachments: list[MessagesMessageAttachment], to_tg_id: int) -> str:
        text = ""
        if attachments is not None and len(attachments) > 0:
            text += "[" + str(len(attachments)) + " attachments] "
        try:
            for a in attachments:
                text += self.handle_attachment(a, to_tg_id)
        except Exception as err_iterating_attachments:
            text += " [Error while iterating attachments]"
            print(err_iterating_attachments)
        return text

    def handle_attachment(self, a: MessagesMessageAttachment, to_tg_id: int) -> str:
        if a.type == MessagesMessageAttachmentType.PHOTO:
            self.forward_photo_attachment(a, to_tg_id)
        else:
            return " [Unknown attachment]: " + str(a.type)
        return ""

    def forward_photo_attachment(self, attachment: MessagesMessageAttachmentType.PHOTO, to_tg_id: int):
        max_w = -1
        largest_photo_variant = None
        for photo in attachment.photo.sizes:
            if photo.width > max_w:
                largest_photo_variant = photo
        self.tg_bot.send_photo(largest_photo_variant.url, chat_id=to_tg_id)

    def stop(self):
        self.is_stopped = True
        self.tg_bot.send_text("Can't shut down properly. Use the fork of vkbottle", TgBot.TG_ADMIN_CHAT_ID)
        self.vk.loop.stop()

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
