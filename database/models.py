# -*- coding: utf-8 -*-
"""
Created on Thu Dec  1 15:45:46 2022
@author: 皓
"""
try:
    from sqlalchemy.orm import declarative_base
    from sqlalchemy.orm import DeclarativeMeta
except ImportError:
    # SQLAlchemy <= 1.3
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.ext.declarative import DeclarativeMeta
from sqlalchemy import inspect, Column, TEXT, INTEGER, BLOB, REAL
from datatype import TLStruct

Model = declarative_base(name='Model', metaclass=DeclarativeMeta)


PARSER = TLStruct()


def parse_blob(data):
    if not data:
        return None
    return PARSER.parse_blob(data)


def parse_structure(data, structure):
    if not data:
        return None
    func = getattr(PARSER, f'{structure}_structures')
    struct = func('content')
    result = struct.parse(data)
    return result.content if result else None


def get_data_blob(self):
    return parse_blob(self.data)


def get_info_blob(self):
    return parse_blob(self.info)


def get_replydata_blob(self):
    return parse_blob(self.replydata)


class TModel:

    def __repr__(self) -> str:
        state = inspect(self)
        if state.transient:
            pk = f"(transient {id(self)})"
        elif state.pending:
            pk = f"(pending {id(self)})"
        else:
            pk = ", ".join(map(str, state.identity))
        return f"<{type(self).__name__} {pk}>"


class UIDModel(Model, TModel):
    __abstract__ = True
    uid = Column(INTEGER, primary_key=True)

    def __repr__(self) -> str:
        state = inspect(self)
        if state.transient:
            pk = f"(transient {id(self)})"
        elif state.pending:
            pk = f"(pending {id(self)})"
        else:
            pk = ", ".join(map(str, state.identity))
        return f"<{type(self).__name__} {pk}>"


class AnimatedEmoji(Model):
    __tablename__ = "animated_emoji"
    document_id = Column(INTEGER, primary_key=True)
    data = Column(BLOB)

    @property
    def blob(self):
        return parse_structure(self.data, 'document')


class AttachMenuBots(Model):
    __tablename__ = "attach_menu_bots"
    data = Column(BLOB)
    hash = Column(INTEGER, primary_key=True)
    date = Column(INTEGER, primary_key=True)

    @property
    def blob(self):
        return parse_structure(self.data, 'attach_menu_bots')


class BotInfoV2(UIDModel):
    __tablename__ = "bot_info_v2"
    dialogId = Column(INTEGER)
    info = Column(BLOB)

    @property
    def blob(self):
        return parse_structure(self.data, 'bot_info')


class BotKeyboard(UIDModel):
    __tablename__ = "bot_keyboard"
    mid = Column(INTEGER)
    info = Column(BLOB)

    @property
    def blob(self):
        return parse_blob(self.info)


class Botcache(Model):
    __tablename__ = "botcache"
    id = Column(TEXT, primary_key=True)
    date = Column(INTEGER)
    data = Column(BLOB)

    @property
    def blob(self):
        return parse_blob(self.info)


class ChannelAdminsV3(Model):
    __tablename__ = "channel_admins_v3"
    did = Column(INTEGER, primary_key=True)
    uid = Column(INTEGER)
    data = Column(BLOB)

    @property
    def blob(self):
        return parse_structure(self.data, 'bot_info')


class ChannelUsersV2(Model):
    __tablename__ = "channel_users_v2"
    did = Column(INTEGER, primary_key=True)
    uid = Column(INTEGER)
    date = Column(INTEGER)
    data = Column(BLOB)

    @property
    def blob(self):
        return parse_structure(self.data, 'bot_info')


class ChatHints(Model):
    __tablename__ = "chat_hints"
    did = Column(INTEGER, primary_key=True)
    type = Column(INTEGER)
    rating = Column(REAL)
    date = Column(INTEGER)


class ChatPinnedCount(UIDModel):
    __tablename__ = "chat_pinned_count"
    count = Column(INTEGER)
    end = Column(INTEGER)


class ChatPinnedV2(UIDModel):
    __tablename__ = "chat_pinned_v2"
    mid = Column(INTEGER)
    data = Column(BLOB)

    @property
    def blob(self):
        return parse_structure(self.data, 'bot_info')


class ChatSettingsV2(UIDModel):
    __tablename__ = "chat_settings_v2"
    info = Column(BLOB)
    pinned = Column(INTEGER)
    online = Column(INTEGER)
    inviter = Column(INTEGER)
    links = Column(INTEGER)

    @property
    def blob(self):
        return parse_structure(self.data, 'bot_info')


class Chats(UIDModel):
    __tablename__ = "chats"
    name = Column(TEXT)
    data = Column(BLOB)

    @property
    def blob(self):
        return parse_structure(self.data, 'chat')


class Contacts(UIDModel):
    __tablename__ = "contacts"
    mutual = Column(INTEGER)


class DialogFilter(Model):
    __tablename__ = "dialog_filter"
    id = Column(INTEGER, primary_key=True)
    ord = Column(INTEGER)
    unread_count = Column(INTEGER)
    flags = Column(INTEGER)
    title = Column(TEXT)


class DialogFilterEp(Model):
    __tablename__ = "dialog_filter_ep"
    id = Column(INTEGER, primary_key=True)
    peer = Column(INTEGER)


class DialogFilterPinV2(Model):
    __tablename__ = "dialog_filter_pin_v2"
    id = Column(INTEGER, primary_key=True)
    peer = Column(INTEGER)
    pin = Column(INTEGER)


class DialogSettings(Model):
    __tablename__ = "dialog_settings"
    did = Column(INTEGER, primary_key=True)
    flags = Column(INTEGER)


class Dialogs(Model):
    __tablename__ = "dialogs"
    did = Column(INTEGER, primary_key=True)
    date = Column(INTEGER)
    unread_count = Column(INTEGER)
    last_mid = Column(INTEGER)
    inbox_max = Column(INTEGER)
    outbox_max = Column(INTEGER)
    last_mid_i = Column(INTEGER)
    unread_count_i = Column(INTEGER)
    pts = Column(INTEGER)
    date_i = Column(INTEGER)
    pinned = Column(INTEGER)
    flags = Column(INTEGER)
    folder_id = Column(INTEGER)
    data = Column(BLOB)
    unread_reactions = Column(INTEGER)

    @property
    def blob(self):
        return parse_structure(self.data, 'bot_info')


class DownloadQueue(UIDModel):
    __tablename__ = "download_queue"
    type = Column(INTEGER)
    date = Column(INTEGER)
    data = Column(BLOB)
    parent = Column(TEXT)

    @property
    def blob(self):
        return parse_structure(self.data, 'bot_info')


class DownloadingDocuments(Model):
    __tablename__ = "downloading_documents"
    data = Column(BLOB)
    hash = Column(INTEGER, primary_key=True)
    id = Column(INTEGER)
    state = Column(INTEGER)
    date = Column(INTEGER)

    @property
    def blob(self):
        return parse_structure(self.data, 'message')


class EmojiKeywordsInfoV2(Model):
    __tablename__ = "emoji_keywords_info_v2"
    lang = Column(TEXT, primary_key=True)
    alias = Column(TEXT)
    version = Column(INTEGER)
    date = Column(INTEGER)


class EmojiKeywordsV2(Model):
    __tablename__ = "emoji_keywords_v2"
    lang = Column(TEXT, primary_key=True)
    keyword = Column(TEXT)
    emoji = Column(TEXT)


class EmojiStatuses(Model):
    __tablename__ = "emoji_statuses"
    data = Column(BLOB, primary_key=True)
    type = Column(INTEGER, primary_key=True)

    @property
    def blob(self):
        return parse_structure(self.data, 'bot_info')


class EncChats(UIDModel):
    __tablename__ = "enc_chats"
    user = Column(INTEGER)
    name = Column(TEXT)
    data = Column(BLOB)
    g = Column(BLOB)
    authkey = Column(BLOB)
    ttl = Column(INTEGER)
    layer = Column(INTEGER)
    seq_in = Column(INTEGER)
    seq_out = Column(INTEGER)
    use_count = Column(INTEGER)
    exchange_id = Column(INTEGER)
    key_date = Column(INTEGER)
    fprint = Column(INTEGER)
    fauthkey = Column(BLOB)
    khash = Column(BLOB)
    in_seq_no = Column(INTEGER)
    admin_id = Column(INTEGER)
    mtproto_seq = Column(INTEGER)

    @property
    def blob(self):
        return parse_structure(self.data, 'encrypted_chat')


class EncTasksV4(Model):
    __tablename__ = "enc_tasks_v4"
    mid = Column(INTEGER, primary_key=True)
    uid = Column(INTEGER)
    date = Column(INTEGER)
    media = Column(INTEGER)


class HashtagRecentV2(Model):
    __tablename__ = "hashtag_recent_v2"
    id = Column(TEXT, primary_key=True)
    date = Column(INTEGER)


class Keyvalue(Model):
    __tablename__ = "keyvalue"
    id = Column(TEXT, primary_key=True)
    value = Column(TEXT)


class MediaCountsV2(UIDModel):
    __tablename__ = "media_counts_v2"
    type = Column(INTEGER)
    count = Column(INTEGER)
    old = Column(INTEGER)


class MediaHolesV2(UIDModel):
    __tablename__ = "media_holes_v2"
    type = Column(INTEGER)
    start = Column(INTEGER)
    end = Column(INTEGER)


class MediaV4(Model):
    __tablename__ = "media_v4"
    mid = Column(INTEGER, primary_key=True)
    uid = Column(INTEGER)
    date = Column(INTEGER)
    type = Column(INTEGER)
    data = Column(BLOB)

    @property
    def blob(self):
        return parse_structure(self.data, 'message')


class MessagesHoles(UIDModel):
    __tablename__ = "messages_holes"
    start = Column(INTEGER)
    end = Column(INTEGER)


class MessagesSeq(Model):
    __tablename__ = "messages_seq"
    mid = Column(INTEGER, primary_key=True)
    seq_in = Column(INTEGER)
    seq_out = Column(INTEGER)


class MessagesV2(Model):
    __tablename__ = "messages_v2"
    mid = Column(INTEGER, primary_key=True)
    uid = Column(INTEGER)
    read_state = Column(INTEGER)
    send_state = Column(INTEGER)
    date = Column(INTEGER)
    data = Column(BLOB)
    out = Column(INTEGER)
    ttl = Column(INTEGER)
    media = Column(INTEGER)
    replydata = Column(BLOB)
    imp = Column(INTEGER)
    mention = Column(INTEGER)
    forwards = Column(INTEGER)
    replies_data = Column(BLOB)
    thread_reply_id = Column(INTEGER)
    is_channel = Column(INTEGER)
    reply_to_message_id = Column(INTEGER)
    custom_params = Column(BLOB)
    # group_id = Column(INTEGER)

    @property
    def blob(self):
        return parse_structure(self.data, 'message')


class Params(Model):
    __tablename__ = "params"
    id = Column(INTEGER, primary_key=True)
    seq = Column(INTEGER)
    pts = Column(INTEGER)
    date = Column(INTEGER)
    qts = Column(INTEGER)
    lsv = Column(INTEGER)
    sg = Column(INTEGER)
    pbytes = Column(BLOB)


class PendingTasks(Model):
    __tablename__ = "pending_tasks"
    id = Column(INTEGER, primary_key=True)
    data = Column(BLOB)


class PollsV2(Model):
    __tablename__ = "polls_v2"
    mid = Column(INTEGER, primary_key=True)
    uid = Column(INTEGER)
    id = Column(INTEGER)


class PremiumPromo(Model):
    __tablename__ = "premium_promo"
    data = Column(BLOB)
    date = Column(INTEGER, primary_key=True)


class RandomsV2(Model):
    __tablename__ = "randoms_v2"
    random_id = Column(INTEGER, primary_key=True)
    mid = Column(INTEGER)
    uid = Column(INTEGER)


class ReactionMentions(Model):
    __tablename__ = "reaction_mentions"
    message_id = Column(INTEGER)
    state = Column(INTEGER)
    dialog_id = Column(INTEGER, primary_key=True)


class Reactions(Model):
    __tablename__ = "reactions"
    data = Column(BLOB)
    hash = Column(INTEGER, primary_key=True)
    date = Column(INTEGER, primary_key=True)


class RequestedHoles(UIDModel):
    __tablename__ = "requested_holes"
    seq_out_start = Column(INTEGER)
    seq_out_end = Column(INTEGER)


class ScheduledMessagesV2(Model):
    __tablename__ = "scheduled_messages_v2"
    mid = Column(INTEGER, primary_key=True)
    uid = Column(INTEGER)
    send_state = Column(INTEGER)
    date = Column(INTEGER)
    data = Column(BLOB)
    ttl = Column(INTEGER)
    replydata = Column(BLOB)
    reply_to_message_id = Column(INTEGER)


class SearchRecent(Model):
    __tablename__ = "search_recent"
    did = Column(INTEGER, primary_key=True)
    date = Column(INTEGER)


class SentFilesV2(UIDModel):
    __tablename__ = "sent_files_v2"
    type = Column(INTEGER)
    data = Column(BLOB)
    parent = Column(TEXT)

    @property
    def blob(self):
        return parse_structure(self.data, 'message')


class SharingLocations(UIDModel):
    __tablename__ = "sharing_locations"
    mid = Column(INTEGER)
    date = Column(INTEGER)
    period = Column(INTEGER)
    message = Column(BLOB)
    proximity = Column(INTEGER)


class ShortcutWidget(Model):
    __tablename__ = "shortcut_widget"
    id = Column(INTEGER, primary_key=True)
    did = Column(INTEGER)
    ord = Column(INTEGER)


class StickersDice(Model):
    __tablename__ = "stickers_dice"
    emoji = Column(TEXT, primary_key=True)
    data = Column(BLOB)
    date = Column(INTEGER)


class StickersFeatured(Model):
    __tablename__ = "stickers_featured"
    id = Column(INTEGER, primary_key=True)
    data = Column(BLOB)
    unread = Column(BLOB)
    date = Column(INTEGER)
    hash = Column(INTEGER)
    premium = Column(INTEGER)
    emoji = Column(INTEGER)


class StickersV2(Model):
    __tablename__ = "stickers_v2"
    id = Column(INTEGER, primary_key=True)
    data = Column(BLOB)
    date = Column(INTEGER)
    hash = Column(INTEGER)


class UnreadPushMessages(UIDModel):
    __tablename__ = "unread_push_messages"
    mid = Column(INTEGER)
    random = Column(INTEGER)
    date = Column(INTEGER)
    data = Column(BLOB)
    fm = Column(TEXT)
    name = Column(TEXT)
    uname = Column(TEXT)
    flags = Column(INTEGER)


class UserContactsV7(Model):
    __tablename__ = "user_contacts_v7"
    key = Column(TEXT, primary_key=True)
    uid = Column(INTEGER)
    fname = Column(TEXT)
    sname = Column(TEXT)
    imported = Column(INTEGER)


class UserPhonesV7(Model):
    __tablename__ = "user_phones_v7"
    key = Column(TEXT, primary_key=True)
    phone = Column(TEXT)
    sphone = Column(TEXT)
    deleted = Column(INTEGER)


class UserPhotos(UIDModel):
    __tablename__ = "user_photos"
    id = Column(INTEGER)
    data = Column(BLOB)

    @property
    def blob(self):
        return parse_structure(self.data, 'photo')


class UserSettings(UIDModel):
    __tablename__ = "user_settings"
    info = Column(BLOB)
    pinned = Column(INTEGER)

    @property
    def blob(self):
        return parse_structure(self.info, 'user_full')


class Users(UIDModel):
    __tablename__ = "users"
    name = Column(TEXT)
    status = Column(INTEGER)
    data = Column(BLOB)

    @property
    def blob(self):
        return parse_structure(self.data, 'user')


class UsersData(UIDModel):
    __tablename__ = "users_data"
    about = Column(TEXT)


class Wallpapers2(UIDModel):
    __tablename__ = "wallpapers2"
    data = Column(BLOB)
    num = Column(INTEGER)


class WebRecentV3(Model):
    __tablename__ = "web_recent_v3"
    id = Column(TEXT, primary_key=True)
    type = Column(INTEGER)
    image_url = Column(TEXT)
    thumb_url = Column(TEXT)
    local_url = Column(TEXT)
    width = Column(INTEGER)
    height = Column(INTEGER)
    size = Column(INTEGER)
    date = Column(INTEGER)
    document = Column(BLOB)

    @property
    def blob(self):
        return parse_structure(self.document, 'document')


class WebpagePendingV2(Model):
    __tablename__ = "webpage_pending_v2"
    id = Column(INTEGER, primary_key=True)
    mid = Column(INTEGER)
    uid = Column(INTEGER)
