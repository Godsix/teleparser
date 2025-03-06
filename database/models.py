# -*- coding: utf-8 -*-
"""
Created on Thu Dec  1 15:45:46 2022
@author: C. David
"""
from sqlalchemy.orm import DeclarativeMeta, declarative_base
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


def get_parser(name):
    def wrapper(self):
        data = getattr(self, name)
        return parse_blob(data)
    return wrapper


class TModel:

    def __repr__(self) -> str:
        state = inspect(self)
        if state.transient:
            pk = f"(transient {id(self)})"
        elif state.pending:
            pk = f"(pending {id(self)})"
        else:
            pk = ", ".join(str(x) for x in state.identity)
        return f"<{type(self).__name__} {pk}>"


class BaseModel(Model, TModel):
    __abstract__ = True


class AnimatedEmoji(BaseModel):
    __tablename__ = "animated_emoji"
    document_id = Column(INTEGER, primary_key=True)
    data = Column(BLOB)


class AttachMenuBots(BaseModel):
    __tablename__ = "attach_menu_bots"
    data = Column(BLOB)
    hash = Column(INTEGER, primary_key=True)
    date = Column(INTEGER, primary_key=True)


class BotInfoV2(BaseModel):
    __tablename__ = "bot_info_v2"
    uid = Column(INTEGER, primary_key=True)
    dialogId = Column(INTEGER)
    info = Column(BLOB)


class BotKeyboard(BaseModel):
    __tablename__ = "bot_keyboard"
    uid = Column(INTEGER, primary_key=True)
    mid = Column(INTEGER)
    info = Column(BLOB)


class BotKeyboardTopics(BaseModel):
    __tablename__ = "bot_keyboard_topics"
    uid = Column(INTEGER, primary_key=True)
    tid = Column(INTEGER)
    mid = Column(INTEGER)
    info = Column(BLOB)


class Botcache(BaseModel):
    __tablename__ = "botcache"
    id = Column(TEXT, primary_key=True)
    date = Column(INTEGER)
    data = Column(BLOB)


class BusinessReplies(BaseModel):
    __tablename__ = "business_replies"
    topic_id = Column(INTEGER, primary_key=True)
    name = Column(TEXT)
    order_value = Column(INTEGER)
    count = Column(INTEGER)


class ChannelAdminsV3(BaseModel):
    __tablename__ = "channel_admins_v3"
    did = Column(INTEGER, primary_key=True)
    uid = Column(INTEGER)
    data = Column(BLOB)


class ChannelUsersV2(BaseModel):
    __tablename__ = "channel_users_v2"
    did = Column(INTEGER, primary_key=True)
    uid = Column(INTEGER)
    date = Column(INTEGER)
    data = Column(BLOB)


class ChatHints(BaseModel):
    __tablename__ = "chat_hints"
    did = Column(INTEGER, primary_key=True)
    type = Column(INTEGER)
    rating = Column(REAL)
    date = Column(INTEGER)


class ChatPinnedCount(BaseModel):
    __tablename__ = "chat_pinned_count"
    uid = Column(INTEGER, primary_key=True)
    count = Column(INTEGER)
    end = Column(INTEGER)


class ChatPinnedV2(BaseModel):
    __tablename__ = "chat_pinned_v2"
    uid = Column(INTEGER, primary_key=True)
    mid = Column(INTEGER)
    data = Column(BLOB)


class ChatSettingsV2(BaseModel):
    __tablename__ = "chat_settings_v2"
    uid = Column(INTEGER, primary_key=True)
    info = Column(BLOB)
    pinned = Column(INTEGER)
    online = Column(INTEGER)
    inviter = Column(INTEGER)
    links = Column(INTEGER)
    participants_count = Column(INTEGER)


class Chats(BaseModel):
    __tablename__ = "chats"
    uid = Column(INTEGER, primary_key=True)
    name = Column(TEXT)
    data = Column(BLOB)


class Contacts(BaseModel):
    __tablename__ = "contacts"
    uid = Column(INTEGER, primary_key=True)
    mutual = Column(INTEGER)


class DialogFilter(BaseModel):
    __tablename__ = "dialog_filter"
    id = Column(INTEGER, primary_key=True)
    ord = Column(INTEGER)
    unread_count = Column(INTEGER)
    flags = Column(INTEGER)
    title = Column(TEXT)
    color = Column(INTEGER)
    entities = Column(BLOB)
    noanimate = Column(INTEGER)


class DialogFilterEp(BaseModel):
    __tablename__ = "dialog_filter_ep"
    id = Column(INTEGER, primary_key=True)
    peer = Column(INTEGER)


class DialogFilterPinV2(BaseModel):
    __tablename__ = "dialog_filter_pin_v2"
    id = Column(INTEGER, primary_key=True)
    peer = Column(INTEGER)
    pin = Column(INTEGER)


class DialogPhotos(BaseModel):
    __tablename__ = "dialog_photos"
    uid = Column(INTEGER, primary_key=True)
    id = Column(INTEGER)
    num = Column(INTEGER)
    data = Column(BLOB)


class DialogPhotosCount(BaseModel):
    __tablename__ = "dialog_photos_count"
    uid = Column(INTEGER, primary_key=True)
    count = Column(INTEGER)


class DialogSettings(BaseModel):
    __tablename__ = "dialog_settings"
    did = Column(INTEGER, primary_key=True)
    flags = Column(INTEGER)


class Dialogs(BaseModel):
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
    last_mid_group = Column(INTEGER)
    ttl_period = Column(INTEGER)


class DownloadQueue(BaseModel):
    __tablename__ = "download_queue"
    uid = Column(INTEGER, primary_key=True)
    type = Column(INTEGER)
    date = Column(INTEGER)
    data = Column(BLOB)
    parent = Column(TEXT)


class DownloadingDocuments(BaseModel):
    __tablename__ = "downloading_documents"
    data = Column(BLOB)
    hash = Column(INTEGER, primary_key=True)
    id = Column(INTEGER)
    state = Column(INTEGER)
    date = Column(INTEGER)


class EmojiGroups(BaseModel):
    __tablename__ = "emoji_groups"
    type = Column(INTEGER, primary_key=True)
    data = Column(BLOB)


class EmojiKeywordsInfoV2(BaseModel):
    __tablename__ = "emoji_keywords_info_v2"
    lang = Column(TEXT, primary_key=True)
    alias = Column(TEXT)
    version = Column(INTEGER)
    date = Column(INTEGER)


class EmojiKeywordsV2(BaseModel):
    __tablename__ = "emoji_keywords_v2"
    lang = Column(TEXT, primary_key=True)
    keyword = Column(TEXT)
    emoji = Column(TEXT)


class EmojiStatuses(BaseModel):
    __tablename__ = "emoji_statuses"
    data = Column(BLOB, primary_key=True)
    type = Column(INTEGER, primary_key=True)


class EncChats(BaseModel):
    __tablename__ = "enc_chats"
    uid = Column(INTEGER, primary_key=True)
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


class EncTasksV4(BaseModel):
    __tablename__ = "enc_tasks_v4"
    mid = Column(INTEGER, primary_key=True)
    uid = Column(INTEGER)
    date = Column(INTEGER)
    media = Column(INTEGER)


class FactChecks(BaseModel):
    __tablename__ = "fact_checks"
    hash = Column(INTEGER, primary_key=True)
    data = Column(BLOB)
    expires = Column(INTEGER)


class HashtagRecentV2(BaseModel):
    __tablename__ = "hashtag_recent_v2"
    id = Column(TEXT, primary_key=True)
    date = Column(INTEGER)


class Keyvalue(BaseModel):
    __tablename__ = "keyvalue"
    id = Column(TEXT, primary_key=True)
    value = Column(TEXT)


class MediaCountsTopics(BaseModel):
    __tablename__ = "media_counts_topics"
    uid = Column(INTEGER, primary_key=True)
    topic_id = Column(INTEGER)
    type = Column(INTEGER)
    count = Column(INTEGER)
    old = Column(INTEGER)


class MediaCountsV2(BaseModel):
    __tablename__ = "media_counts_v2"
    uid = Column(INTEGER, primary_key=True)
    type = Column(INTEGER)
    count = Column(INTEGER)
    old = Column(INTEGER)


class MediaHolesTopics(BaseModel):
    __tablename__ = "media_holes_topics"
    uid = Column(INTEGER, primary_key=True)
    topic_id = Column(INTEGER)
    type = Column(INTEGER)
    start = Column(INTEGER)
    end = Column(INTEGER)


class MediaHolesV2(BaseModel):
    __tablename__ = "media_holes_v2"
    uid = Column(INTEGER, primary_key=True)
    type = Column(INTEGER)
    start = Column(INTEGER)
    end = Column(INTEGER)


class MediaTopics(BaseModel):
    __tablename__ = "media_topics"
    mid = Column(INTEGER, primary_key=True)
    uid = Column(INTEGER)
    topic_id = Column(INTEGER)
    date = Column(INTEGER)
    type = Column(INTEGER)
    data = Column(BLOB)


class MediaV4(BaseModel):
    __tablename__ = "media_v4"
    mid = Column(INTEGER, primary_key=True)
    uid = Column(INTEGER)
    date = Column(INTEGER)
    type = Column(INTEGER)
    data = Column(BLOB)


class MessagesHoles(BaseModel):
    __tablename__ = "messages_holes"
    uid = Column(INTEGER, primary_key=True)
    start = Column(INTEGER)
    end = Column(INTEGER)


class MessagesHolesTopics(BaseModel):
    __tablename__ = "messages_holes_topics"
    uid = Column(INTEGER, primary_key=True)
    topic_id = Column(INTEGER)
    start = Column(INTEGER)
    end = Column(INTEGER)


class MessagesSeq(BaseModel):
    __tablename__ = "messages_seq"
    mid = Column(INTEGER, primary_key=True)
    seq_in = Column(INTEGER)
    seq_out = Column(INTEGER)


class MessagesTopics(BaseModel):
    __tablename__ = "messages_topics"
    mid = Column(INTEGER, primary_key=True)
    uid = Column(INTEGER)
    topic_id = Column(INTEGER)
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
    reply_to_story_id = Column(INTEGER)


class MessagesV2(BaseModel):
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
    group_id = Column(INTEGER)
    reply_to_story_id = Column(INTEGER)


class Params(BaseModel):
    __tablename__ = "params"
    id = Column(INTEGER, primary_key=True)
    seq = Column(INTEGER)
    pts = Column(INTEGER)
    date = Column(INTEGER)
    qts = Column(INTEGER)
    lsv = Column(INTEGER)
    sg = Column(INTEGER)
    pbytes = Column(BLOB)


class PendingTasks(BaseModel):
    __tablename__ = "pending_tasks"
    id = Column(INTEGER, primary_key=True)
    data = Column(BLOB)


class PollsV2(BaseModel):
    __tablename__ = "polls_v2"
    mid = Column(INTEGER, primary_key=True)
    uid = Column(INTEGER)
    id = Column(INTEGER)


class PopularBots(BaseModel):
    __tablename__ = "popular_bots"
    uid = Column(INTEGER, primary_key=True)
    time = Column(INTEGER)
    offset = Column(TEXT)
    pos = Column(INTEGER)


class PremiumPromo(BaseModel):
    __tablename__ = "premium_promo"
    data = Column(BLOB)
    date = Column(INTEGER, primary_key=True)


class ProfileStories(BaseModel):
    __tablename__ = "profile_stories"
    dialog_id = Column(INTEGER, primary_key=True)
    story_id = Column(INTEGER)
    data = Column(BLOB)
    type = Column(INTEGER)
    seen = Column(INTEGER)
    pin = Column(INTEGER)


class QuickRepliesMessages(BaseModel):
    __tablename__ = "quick_replies_messages"
    mid = Column(INTEGER, primary_key=True)
    topic_id = Column(INTEGER)
    send_state = Column(INTEGER)
    date = Column(INTEGER)
    data = Column(BLOB)
    ttl = Column(INTEGER)
    replydata = Column(BLOB)
    reply_to_message_id = Column(INTEGER)


class RandomsV2(BaseModel):
    __tablename__ = "randoms_v2"
    random_id = Column(INTEGER, primary_key=True)
    mid = Column(INTEGER)
    uid = Column(INTEGER)


class ReactionMentions(BaseModel):
    __tablename__ = "reaction_mentions"
    message_id = Column(INTEGER)
    state = Column(INTEGER)
    dialog_id = Column(INTEGER, primary_key=True)


class ReactionMentionsTopics(BaseModel):
    __tablename__ = "reaction_mentions_topics"
    message_id = Column(INTEGER, primary_key=True)
    state = Column(INTEGER)
    dialog_id = Column(INTEGER)
    topic_id = Column(INTEGER)


class Reactions(BaseModel):
    __tablename__ = "reactions"
    data = Column(BLOB)
    hash = Column(INTEGER, primary_key=True)
    date = Column(INTEGER, primary_key=True)


class RequestedHoles(BaseModel):
    __tablename__ = "requested_holes"
    uid = Column(INTEGER, primary_key=True)
    seq_out_start = Column(INTEGER)
    seq_out_end = Column(INTEGER)


class SavedDialogs(BaseModel):
    __tablename__ = "saved_dialogs"
    did = Column(INTEGER, primary_key=True)
    date = Column(INTEGER)
    last_mid = Column(INTEGER)
    pinned = Column(INTEGER)
    flags = Column(INTEGER)
    folder_id = Column(INTEGER)
    last_mid_group = Column(INTEGER)
    count = Column(INTEGER)


class SavedReactionTags(BaseModel):
    __tablename__ = "saved_reaction_tags"
    topic_id = Column(INTEGER, primary_key=True)
    data = Column(BLOB)


class ScheduledMessagesV2(BaseModel):
    __tablename__ = "scheduled_messages_v2"
    mid = Column(INTEGER, primary_key=True)
    uid = Column(INTEGER)
    send_state = Column(INTEGER)
    date = Column(INTEGER)
    data = Column(BLOB)
    ttl = Column(INTEGER)
    replydata = Column(BLOB)
    reply_to_message_id = Column(INTEGER)


class SearchRecent(BaseModel):
    __tablename__ = "search_recent"
    did = Column(INTEGER, primary_key=True)
    date = Column(INTEGER)


class SentFilesV2(BaseModel):
    __tablename__ = "sent_files_v2"
    uid = Column(TEXT, primary_key=True)
    type = Column(INTEGER)
    data = Column(BLOB)
    parent = Column(TEXT)


class SharingLocations(BaseModel):
    __tablename__ = "sharing_locations"
    uid = Column(INTEGER, primary_key=True)
    mid = Column(INTEGER)
    date = Column(INTEGER)
    period = Column(INTEGER)
    message = Column(BLOB)
    proximity = Column(INTEGER)


class ShortcutWidget(BaseModel):
    __tablename__ = "shortcut_widget"
    id = Column(INTEGER, primary_key=True)
    did = Column(INTEGER)
    ord = Column(INTEGER)


class StarGifts2(BaseModel):
    __tablename__ = "star_gifts2"
    id = Column(INTEGER, primary_key=True)
    data = Column(BLOB)
    hash = Column(INTEGER)
    time = Column(INTEGER)
    pos = Column(INTEGER)


class StickersDice(BaseModel):
    __tablename__ = "stickers_dice"
    emoji = Column(TEXT, primary_key=True)
    data = Column(BLOB)
    date = Column(INTEGER)


class StickersFeatured(BaseModel):
    __tablename__ = "stickers_featured"
    id = Column(INTEGER, primary_key=True)
    data = Column(BLOB)
    unread = Column(BLOB)
    date = Column(INTEGER)
    hash = Column(INTEGER)
    premium = Column(INTEGER)
    emoji = Column(INTEGER)


class StickersV2(BaseModel):
    __tablename__ = "stickers_v2"
    id = Column(INTEGER, primary_key=True)
    data = Column(BLOB)
    date = Column(INTEGER)
    hash = Column(INTEGER)


class Stickersets(BaseModel):
    __tablename__ = "stickersets"
    id = Column(INTEGER, primary_key=True)
    data = Column(BLOB)
    hash = Column(INTEGER, primary_key=True)


class Stickersets2(BaseModel):
    __tablename__ = "stickersets2"
    id = Column(INTEGER, primary_key=True)
    data = Column(BLOB)
    hash = Column(INTEGER, primary_key=True)
    date = Column(INTEGER)
    short_name = Column(TEXT)


class Stories(BaseModel):
    __tablename__ = "stories"
    dialog_id = Column(INTEGER, primary_key=True)
    story_id = Column(INTEGER)
    data = Column(BLOB)
    custom_params = Column(BLOB)


class StoriesCounter(BaseModel):
    __tablename__ = "stories_counter"
    dialog_id = Column(INTEGER, primary_key=True)
    count = Column(INTEGER)
    max_read = Column(INTEGER)


class StoryDrafts(BaseModel):
    __tablename__ = "story_drafts"
    id = Column(INTEGER, primary_key=True)
    date = Column(INTEGER)
    data = Column(BLOB)
    type = Column(INTEGER)


class StoryPushes(BaseModel):
    __tablename__ = "story_pushes"
    uid = Column(INTEGER, primary_key=True)
    sid = Column(INTEGER)
    date = Column(INTEGER)
    localName = Column(TEXT)
    flags = Column(INTEGER)
    expire_date = Column(INTEGER)


class TagMessageId(BaseModel):
    __tablename__ = "tag_message_id"
    mid = Column(INTEGER, primary_key=True)
    topic_id = Column(INTEGER, primary_key=True)
    tag = Column(INTEGER)
    text = Column(TEXT)


class Topics(BaseModel):
    __tablename__ = "topics"
    did = Column(INTEGER, primary_key=True)
    topic_id = Column(INTEGER)
    data = Column(BLOB)
    top_message = Column(INTEGER)
    topic_message = Column(BLOB)
    unread_count = Column(INTEGER)
    max_read_id = Column(INTEGER)
    unread_mentions = Column(INTEGER)
    unread_reactions = Column(INTEGER)
    read_outbox = Column(INTEGER)
    pinned = Column(INTEGER)
    total_messages_count = Column(INTEGER)
    hidden = Column(INTEGER)
    edit_date = Column(INTEGER)


class UnreadPushMessages(BaseModel):
    __tablename__ = "unread_push_messages"
    uid = Column(INTEGER, primary_key=True)
    mid = Column(INTEGER)
    random = Column(INTEGER)
    date = Column(INTEGER)
    data = Column(BLOB)
    fm = Column(TEXT)
    name = Column(TEXT)
    uname = Column(TEXT)
    flags = Column(INTEGER)
    topicId = Column(INTEGER)
    is_reaction = Column(INTEGER)


class UserContactsV7(BaseModel):
    __tablename__ = "user_contacts_v7"
    key = Column(TEXT, primary_key=True)
    uid = Column(INTEGER)
    fname = Column(TEXT)
    sname = Column(TEXT)
    imported = Column(INTEGER)


class UserPhonesV7(BaseModel):
    __tablename__ = "user_phones_v7"
    key = Column(TEXT, primary_key=True)
    phone = Column(TEXT)
    sphone = Column(TEXT)
    deleted = Column(INTEGER)


class UserSettings(BaseModel):
    __tablename__ = "user_settings"
    uid = Column(INTEGER, primary_key=True)
    info = Column(BLOB)
    pinned = Column(INTEGER)


class Users(BaseModel):
    __tablename__ = "users"
    uid = Column(INTEGER, primary_key=True)
    name = Column(TEXT)
    status = Column(INTEGER)
    data = Column(BLOB)


class UsersData(BaseModel):
    __tablename__ = "users_data"
    uid = Column(INTEGER, primary_key=True)
    about = Column(TEXT)


class Wallpapers2(BaseModel):
    __tablename__ = "wallpapers2"
    uid = Column(INTEGER, primary_key=True)
    data = Column(BLOB)
    num = Column(INTEGER)


class WebRecentV3(BaseModel):
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


class WebpagePendingV2(BaseModel):
    __tablename__ = "webpage_pending_v2"
    id = Column(INTEGER, primary_key=True)
    mid = Column(INTEGER)
    uid = Column(INTEGER)
