import time
import traceback
from typing import Optional

import vkbottle
from vkbottle import Bot
from vkbottle.bot import Message
from vkbottle.tools.dev.mini_types.bot.foreign_message import ForeignMessageMin
from vkbottle_types.codegen.objects import UsersUserFull
from vkbottle_types.objects import MessagesMessageAttachmentType, MessagesMessageAttachment, WallWallpostAttachmentType

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
        text = base_text
        forwarded_list = None
        attachments = None
        attachments_count = 0
        try:
            text += message.text
            if text != "":
                text = " " + text
            sender_id = message.from_id
            user: UsersUserFull = (await self.vk.api.users.get(user_ids=[sender_id], fields=["screen_name"]))[0]
            sender_name: str = user.first_name + " " + user.last_name
            text = sender_name + ":" + text
            attachments = message.attachments
            attachments_count = self.count_attachments(attachments)
            text += self.count_attachments_str(attachments)
            forwarded_list = message.fwd_messages
            if forwarded_list is not None and len(forwarded_list) > 0:
                text += str(" [" + str(len(forwarded_list)) + " forwarded]:")
        except Exception as ex:
            text += " [Error while fetching more info]: " + str(ex)
            traceback.print_tb(ex.__traceback__)

        print(message.chat_id, text)
        text_is_sent_as_caption = False
        if attachments_count > 0:
            try:
                if attachments[0].type == MessagesMessageAttachmentType.PHOTO:
                    self.forward_photo_attachment(attachments[0], to_tg_id, text)
                    attachments.pop(0)
                    text_is_sent_as_caption = True
            except Exception as ex:
                print("Error while sending a photo with caption", ex)
                traceback.print_tb(ex.__traceback__)
        if not text_is_sent_as_caption:
            self.tg_bot.send_text(text, to_tg_id, disable_notification=False, enable_md=False)

        try:
            self.handle_attachments(attachments, to_tg_id)
        except Exception as ex:
            err_text = " [Error while sending attachments]: " + str(ex)
            self.tg_bot.send_text(err_text, TgBot.TG_ADMIN_CHAT_ID)
            traceback.print_tb(ex.__traceback__)

        try:
            await self.handle_forwarded(forwarded_list, to_tg_id)
        except Exception as ex:
            err_text = " [Error while sending forwarded messages]: " + str(ex)
            self.tg_bot.send_text(err_text, TgBot.TG_ADMIN_CHAT_ID)
            traceback.print_tb(ex.__traceback__)

    async def handle_forwarded(self, forwarded: list[ForeignMessageMin], to_tg_id: int):
        if forwarded is None or len(forwarded) < 1:
            return ""
        for fwd_message in forwarded:
            await self.handle_message("↩️ ", fwd_message, to_tg_id)

    def handle_attachments(self, attachments: list[MessagesMessageAttachment], to_tg_id: int):
        for a in attachments:
            self.handle_attachment(a, to_tg_id)

    def handle_attachment(self, a: MessagesMessageAttachment, to_tg_id: int):
        if a.type == MessagesMessageAttachmentType.PHOTO or a.type == WallWallpostAttachmentType.PHOTO:
            self.forward_photo_attachment(a, to_tg_id)
        elif a.type == MessagesMessageAttachmentType.WALL:
            self.forward_wall_post_attachment(a, to_tg_id)
        else:
            print("Unknown attachment:", a.type)
            self.tg_bot.send_text("[Unknown attachment]: type=" + str(a.type.value), to_tg_id, disable_notification=True)

    def forward_photo_attachment(self, attachment, to_tg_id: int, text: Optional[str] = ""):
        max_w = -1
        largest_photo_variant = None
        for photo in attachment.photo.sizes:
            w = photo.width
            if w > max_w:
                max_w = w
                largest_photo_variant = photo
        self.tg_bot.send_photo(url=largest_photo_variant.url, chat_id=to_tg_id, text=text)

    def forward_wall_post_attachment(self, attachment: MessagesMessageAttachmentType.WALL, to_tg_id: int):
        author = ""  # attachment.wall.from.first_name + attachment.wall.from.last_name
        text = "[Wall post]: " + self.count_attachments_str(attachment.wall.attachments) + " " + attachment.wall.text
        print(text)
        self.tg_bot.send_text(text, to_tg_id, enable_md=False)
        self.handle_attachments(attachment.wall.attachments, to_tg_id)

    def count_attachments(self, attachments: list[MessagesMessageAttachment]) -> int:
        if attachments is None:
            return 0
        return len(attachments)

    def count_attachments_str(self, attachments: list[MessagesMessageAttachment]) -> str:
        count = self.count_attachments(attachments)
        if count > 0:
            return " [" + str(count) + " attachments]"
        else:
            return ""

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
