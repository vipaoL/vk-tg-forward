import time
import traceback
from typing import Optional
from urllib.request import urlopen

import vkbottle
from vkbottle import Bot
from vkbottle.bot import Message
from vkbottle.tools.mini_types.bot.foreign_message import ForeignMessageMin
from vkbottle_types.codegen.objects import UsersUserFull, BaseSticker, BaseImage
from vkbottle_types.objects import MessagesMessageAttachmentType, MessagesMessageAttachment, WallWallpostAttachmentType, \
    MessagesMessageAction, MessagesMessageActionStatus

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
            sender_name: str = await self.fetch_user_name(sender_id)
            text = sender_name + ":" + text
            attachments = message.attachments
            attachments_count = self.count_attachments(attachments)
            text += self.count_attachments_str(attachments)
            forwarded_list = message.fwd_messages
            if forwarded_list is not None and len(forwarded_list) > 0:
                text += str(" [" + str(len(forwarded_list)) + " ↩️]:")

            try:
                if message.is_cropped:
                    text += "\n[⚠ ВК обрезал сообщение для бота. Возможно, у него больше вложений]"
            except:
                pass

            try:
                action = message.action
                text += await self.handle_action(action, sender_id)
            except Exception as e:
                print(e)
                traceback.print_tb(e.__traceback__)
        except Exception as ex:
            text += " [Ошибка получения дополнительной информации]: " + str(ex)
            print(ex)
            traceback.print_tb(ex.__traceback__)

        print(message.chat_id, text)
        text_is_sent_as_caption = False
        if attachments_count > 0:
            try:
                self.handle_attachment(attachments[0], to_tg_id, text)
                text_is_sent_as_caption = True
            except Exception as ex:
                print("Error while sending attachment with a caption", ex)
                print(ex)
                traceback.print_tb(ex.__traceback__)
            attachments.pop(0)
        if not text_is_sent_as_caption:
            self.tg_bot.send_text(text, to_tg_id, disable_notification=False, enable_md=False)

        try:
            self.handle_attachments(attachments, to_tg_id)
        except Exception as ex:
            err_text = " [Ошибка отправки вложений]: " + str(ex)
            self.tg_bot.send_text(err_text, TgBot.TG_ADMIN_CHAT_ID)
            print(ex)
            traceback.print_tb(ex.__traceback__)

        try:
            await self.handle_forwarded(forwarded_list, to_tg_id)
        except Exception as ex:
            err_text = " [Ошибка отправки пересланных]: " + str(ex)
            self.tg_bot.send_text(err_text, TgBot.TG_ADMIN_CHAT_ID)
            print(ex)
            traceback.print_tb(ex.__traceback__)

    async def fetch_user_name(self, id: int) -> str:
        user: UsersUserFull = (await self.vk.api.users.get(user_ids=[id], fields=["screen_name"]))[0]
        return user.first_name + " " + user.last_name

    async def handle_action(self, action: MessagesMessageAction, sender_id: int):
        if action is None:
            return ""
        ret = " "
        try:
            action_type = action.type
            if action_type == MessagesMessageActionStatus.CHAT_INVITE_USER:
                if action.member_id == sender_id:
                    ret += "присоединился к беседе"
                else:
                    ret += "пригласил "
                    ret += await self.fetch_user_name(action.member_id)
            elif action_type == MessagesMessageActionStatus.CHAT_KICK_USER:
                if action.member_id == sender_id:
                    ret += "покинул беседу"
                else:
                    ret += "исключил "
                    ret += await self.fetch_user_name(action.member_id)
            else:
                ret += "[ "
                ret += str(action_type)
                if action.member_id != sender_id:
                    ret += ": " + str(action.member_id)
                if action.message is not None:
                    ret += ", " + str(action.message)
                ret += " ]"
        except Exception as ex:
            ret += " [Ошибка разбора действия]: " + str(ex)
            print(ex)
            traceback.print_tb(ex.__traceback__)
        return ret

    async def handle_forwarded(self, forwarded: list[ForeignMessageMin], to_tg_id: int):
        if forwarded is None or len(forwarded) < 1:
            return ""
        for fwd_message in forwarded:
            await self.handle_message("[Переслано]: ", fwd_message, to_tg_id)

    def handle_attachments(self, attachments: list[MessagesMessageAttachment], to_tg_id: int):
        for a in attachments:
            self.handle_attachment(a, to_tg_id)

    def handle_attachment(self, a: MessagesMessageAttachment, to_tg_id: int, text: Optional[str] = ""):
        print(a)
        if a.type == MessagesMessageAttachmentType.PHOTO or a.type == WallWallpostAttachmentType.PHOTO:
            self.forward_photo_attachment(a, to_tg_id, text)
        elif a.type == MessagesMessageAttachmentType.WALL:
            self.forward_wall_post_attachment(a, to_tg_id, text)
        elif a.type == MessagesMessageAttachmentType.DOC:
            self.forward_doc_attachment(a, to_tg_id, text)
        elif a.type == MessagesMessageAttachmentType.AUDIO:
            self.forward_audio_attachment(a, to_tg_id, text)
        elif a.type == MessagesMessageAttachmentType.AUDIO_MESSAGE:
            self.forward_audio_message_attachment(a, to_tg_id, text)
        elif a.type == MessagesMessageAttachmentType.GRAFFITI:
            self.forward_graffiti_attachment(a, to_tg_id, text)
        elif a.type == MessagesMessageAttachmentType.LINK:
            self.forward_link_attachment(a, to_tg_id, text)
        elif a.type == MessagesMessageAttachmentType.STICKER:
            self.forward_sticker_attachment(a, to_tg_id, text)
        else:
            print("📎 Неизвестное вложение:", a.type)
            self.tg_bot.send_text(text + "\n[📎 Неизвестное вложение]: type=" + str(a.type.value), to_tg_id, disable_notification=True)

    def forward_photo_attachment(self, attachment, to_tg_id: int, text: Optional[str] = ""):
        self.tg_bot.send_photo(url=find_largest_photo(attachment.photo.sizes).url, chat_id=to_tg_id, text=text)

    def forward_doc_attachment(self, attachment: MessagesMessageAttachmentType.DOC, to_tg_id: int,
                               text: Optional[str] = ""):
        url = attachment.doc.url
        with urlopen(url) as f:
            self.tg_bot.send_doc(url=url, chat_id=to_tg_id, text=text, file=f, file_name=attachment.doc.title)

    def forward_audio_message_attachment(self, attachment: MessagesMessageAttachmentType.AUDIO_MESSAGE, to_tg_id: int,
                               text: Optional[str] = ""):
        self.tg_bot.send_doc(url=attachment.audio_message.link_ogg, chat_id=to_tg_id, text=text)

    def forward_audio_attachment(self, attachment: MessagesMessageAttachmentType.AUDIO, to_tg_id: int,
                               text: Optional[str] = ""):
        artist = attachment.audio.artist
        title = attachment.audio.title
        url = "https://vk.com/audio" + str(attachment.audio.owner_id) + "_" + str(attachment.audio.id)
        file_url = attachment.audio.url
        text = text.replace("[", "\[") + "\n\[Аудио] [" + artist + " – " + title + "](" + url + ")"
        if True or url is None or url == "": # TODO
            self.tg_bot.send_text(text, to_tg_id, enable_md=True)
        else:
            self.tg_bot.send_doc(url=file_url, chat_id=to_tg_id, text=text, enable_md=True)

    def forward_graffiti_attachment(self, attachment: MessagesMessageAttachmentType.DOC, to_tg_id: int,
                               text: Optional[str] = ""):
        self.tg_bot.send_photo(url=attachment.graffiti.url, chat_id=to_tg_id, text=text + " [Граффити]")

    def forward_link_attachment(self, attachment: MessagesMessageAttachmentType.LINK, to_tg_id: int,
                               text: Optional[str] = ""):
        title = attachment.link.title
        url = attachment.link.url
        self.tg_bot.send_text(text.replace("[", "\[")
                              + "\n\[Ссылка] [" + title + "](" + url + ")", to_tg_id, enable_md=True)

    def forward_sticker_attachment(self, attachment: MessagesMessageAttachmentType.STICKER, to_tg_id: int,
                                   text: Optional[str] = ""):
        self.tg_bot.send_photo(url=find_largest_photo(attachment.sticker.images).url, chat_id=to_tg_id, text=text)

    def forward_wall_post_attachment(self, attachment: MessagesMessageAttachmentType.WALL, to_tg_id: int,
                                     text: Optional[str] = ""):
        author = ""  # attachment.wall.from.first_name + attachment.wall.from.last_name
        text += "\n[Запись на стене]: " + self.count_attachments_str(attachment.wall.attachments) + " " + attachment.wall.text
        print(text)

        attachments = attachment.wall.attachments
        text_is_sent_as_caption = False
        if self.count_attachments(attachments) > 0:
            try:
                self.handle_attachment(attachments[0], to_tg_id, text)
                attachments.pop(0)
                text_is_sent_as_caption = True
            except Exception as ex:
                print("Error while sending attachment with a caption", ex)
                traceback.print_tb(ex.__traceback__)
        if not text_is_sent_as_caption:
            self.tg_bot.send_text(text, to_tg_id, enable_md=False)
        self.handle_attachments(attachments, to_tg_id)

    def count_attachments(self, attachments: list[MessagesMessageAttachment]) -> int:
        if attachments is None:
            return 0
        return len(attachments)

    def count_attachments_str(self, attachments: list[MessagesMessageAttachment]) -> str:
        count = self.count_attachments(attachments)
        if count > 0:
            return " [" + str(count) + " 📎]"
        else:
            return ""

    def stop(self):
        self.is_stopped = True
        self.tg_bot.send_text("Can't shut down properly. Use the fork of vkbottle", TgBot.TG_ADMIN_CHAT_ID)
        self.vk.loop.stop()

    def get_last_update_time(self):
        try:
            return self.vk.polling.get_last_long_request_time()
        except AttributeError as e:
            print(e)
            print("!!!!!!!!!!!!![watchdog is not working! please apply patch to vkbottle]!!!!!!!!!!!!!!")
            print("git apply --whitespace=fix 0001-BotPolling-add-a-property-for-last-longpoll-request.patch --directory=.venv/lib/python3.11/site-packages/")
            return 0

    def get_last_update_time_str(self) -> str:
        t = self.get_last_update_time()
        if t == 0:
            return "???"
        else:
            return utils.get_time_str(t)


def find_largest_photo(sizes_list: list[BaseImage]) -> BaseImage:
    max_w = -1
    largest_photo_variant = None
    for photo in sizes_list:
        w = photo.width
        if w > max_w:
            max_w = w
            largest_photo_variant = photo
    return largest_photo_variant
