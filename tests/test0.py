# -*- coding: utf-8 -*-
"""
Created on Thu Dec  1 15:49:16 2022

@author: 皓
"""

# from generater import SQLiteDataBase, save_code
import re
from sqlalchemy import func
from database import TelegramDB
# import datatype.common
import binascii
from database.models import (AnimatedEmoji, AttachMenuBots, BotInfoV2,
                             BotKeyboard, Botcache, ChannelAdminsV3,
                             ChannelUsersV2, ChatHints, ChatPinnedCount,
                             ChatPinnedV2, ChatSettingsV2, Chats, Contacts,
                             DialogFilter, DialogFilterEp, DialogFilterPinV2,
                             DialogSettings, Dialogs, DownloadQueue,
                             DownloadingDocuments, EmojiKeywordsInfoV2,
                             EmojiStatuses, EncChats,
                             EncTasksV4, HashtagRecentV2, Keyvalue,
                             MediaCountsV2, MediaHolesV2, MediaV4,
                             MessagesHoles, MessagesSeq, MessagesV2,
                             Params, PendingTasks, PollsV2, PremiumPromo,
                             RandomsV2, ReactionMentions, Reactions,
                             RequestedHoles, ScheduledMessagesV2, SearchRecent,
                             SentFilesV2, SharingLocations, ShortcutWidget,
                             StickersDice, StickersFeatured, StickersV2,
                             UnreadPushMessages, UserContactsV7, UserPhonesV7,
                             UserPhotos, UserSettings, Users, UsersData,
                             Wallpapers2, WebRecentV3, WebpagePendingV2)

PATH = r'../cache4.db'


# x=binascii.unhexlify(hex(x)[2:])

# EmojiKeywordsV2

def print_run_time(fmt='{name} spend time: {time:.3f} s.', logger=print):
    from functools import wraps
    import time
    if isinstance(fmt, str):
        def decorator(func):
            name = getattr(func, '__name__', repr(func))
            param = {'name': name}

            @wraps(func)
            def wrapper(*args, **kwargs):
                start = time.time()
                ret = func(*args, **kwargs)
                end = time.time()
                _ = param.setdefault('time', end - start)
                logger(fmt.format_map(param))
                return ret
            return wrapper
        return decorator
    elif callable(fmt):
        default_fmt = '{name} spend time: {time:.3f} s.'
        name = getattr(fmt, '__name__', repr(fmt))
        param = {'name': name}

        @wraps(fmt)
        def wrapper(*args, **kwargs):
            start = time.time()
            ret = fmt(*args, **kwargs)
            end = time.time()
            _ = param.setdefault('time', end - start)
            logger(default_fmt.format_map(param))
            return ret
        return wrapper
    raise TypeError(
        'Expected first argument to be an string, or a callable.')

@print_run_time
def test1():
    db = TelegramDB(PATH)
    result = db.session.query(WebRecentV3).all()
    data_name = 'document'
    
    # print(result)

    # info = {}
    # for item in result:
    #     data = getattr(item, data_name)
    #     if not data:
    #         continue
    #     data4 = data[:4]
    #     if len(data4) < 4:
    #         continue
    #     key = int.from_bytes(data4, 'little')
    #     info.setdefault(key, None)
    # print([f'0x{x:x}' for x in info])
    # return
    
    results = []
    P = re.compile(r"u'([^']+\.mp4)'")

    for i, item in enumerate(result):
        try:
            res = P.findall(str(item.blob))
            if res:
                results.extend(res) 
            # if 'mp4' in str(item.blob):
            #     print(item)
            #     break
            # print(item.blob)
        except Exception as e:
            data = getattr(item, data_name)
            key = int.from_bytes(data[:4], 'little')
            print(f'0x{key:08x}', data)
            print(i, e)
            break
            raise e
    else:
        # print(item.blob)
        pass
    print(results)
    print('Count:', len(result))

# AnimatedEmoji 31
# AttachMenuBots 1
# BotInfoV2 25
# BotKeyboard 0
# Botcache 0
# ChannelAdminsV3 22
# ChannelUsersV2 157
# ChatHints 0
# ChatPinnedCount 25
# ChatPinnedV2 10
# ChatSettingsV2 9
# Chats 64
# Contacts 17
# DialogFilter 1
# DialogFilterEp 0
# DialogFilterPinV2 0
# DialogSettings 28
# Dialogs 22
# DownloadQueue 0
# DownloadingDocuments 88
# EmojiKeywordsInfoV2 1
# EmojiKeywordsV2 7258
# EmojiStatuses 0
# EncChats 0
# EncTasksV4 0
# HashtagRecentV2 0
# Keyvalue 0
# MediaCountsV2 616
# MediaHolesV2 267
# MediaV4 1679
# MessagesHoles 31
# MessagesSeq 0
# MessagesV2 3793
# Params 1
# PendingTasks 0
# PollsV2 4
# PremiumPromo 1
# RandomsV2 4
# ReactionMentions 2
# Reactions 1
# RequestedHoles 0
# ScheduledMessagesV2 0
# SearchRecent 3
# SentFilesV2 0
# SharingLocations 0
# ShortcutWidget 0
# StickersDice 10
# StickersFeatured 1
# StickersV2 4
# UnreadPushMessages 0
# UserContactsV7 461
# UserPhonesV7 661
# UserPhotos 41
# UserSettings 70
# Users 10734
# UsersData 0
# Wallpapers2 0
# WebRecentV3 226
# WebpagePendingV2 286


def test4():
    import database.models
    db = TelegramDB(PATH)
    # Model = database.models.Model
    for item in (x for x in dir(database.models)):
        model = getattr(database.models, item)
        # if not type(model).__name__ == 'DeclarativeMeta':
        #     continue
        if not hasattr(model, '__tablename__'):
            continue
        tablename = model.__tablename__
        columns = db.inspect.get_columns(tablename)
        if not columns:
            continue
        # print(columns)
        query = db.session.query(func.count(
            getattr(model, columns[0]['name']))).scalar()
        print(model.__name__, query)


def test2():
    db = TelegramDB(PATH)
    # print(db.user_version)
    # result = db.get_messages()
    result = db.get_user_settings()
    # data = result[1].data
    # title = result[0].blob
    # te = title.encode()
    # if te in data:
    #     print(data.find(te), len(te))
    # print(result[0].data)
    print(result[12].blob)


def get_index(a):
    key = int.from_bytes(a[:4], 'little')
    print(f'0x{key:08x}')
    0xa518110d.to_bytes(4, 'little')


def test_fail(contacts):
    db = TelegramDB(PATH)
    result = db.get_contacts()

@print_run_time
def test3():
    db = TelegramDB(PATH)
    print(db.user_version)
    # print(dir(db.inspect))
    # print(dir(db.get_model('animated_emoji')))
    # result = db.get_user_settings()
    # result = db.get_chats()

    #
    # result = db.get_dialogs()
    # result = db.get_enc_chats()
    # result = db.get_media()
    # result = db.get_messages()
    # result = db.get_sent_files_v2()
    result = db.get_users()
    print(result)
    # result = db.get_user_settings()

    for i, item in enumerate(result):
        try:
            # print(item.blob)
            blob = item.blob
        except Exception as e:
            key = int.from_bytes(item.info[:4], 'little')
            print(f'0x{key:08x}', item.info)
            print(i, e)
            break
            raise e
    print('Count:', len(result))


def main():
    test3()


# ------------------------------------------------------------------------------
if __name__ == '__main__':
    # generate_code()
    main()
