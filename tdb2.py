#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Telegram cache4 db parser.
#
# Released under MIT License
#
# Copyright (c) 2019 Francesco "dfirfpi" Picasso, Reality Net System Solutions
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
'''Telegram sqlite3 DB parser.'''

# pylint: disable=C0103,C0115,C0116,C0302,R0902,R0914,R0913
import os
from datetime import datetime, UTC
from sqlalchemy import BLOB
import logger
from database import TelegramDB
from datatype import pythonic, get_obj_value, format_dict
from tools.lazy import lazy_property, del_lazy_attr

# ------------------------------------------------------------------------------

CSV_SEPARATOR = ','
TYPE_CHAT_CREATION_DATE = 'chat_creation_date'
TYPE_CHAT_LAST_UPDATE = 'chat_last_update'
TYPE_MSG_SERVICE = 'service'
TYPE_KEY_DATE = 'key_date'
TYPE_MSG_TO_CHANNEL = 'channel'
TYPE_MSG_TO_USER = 'chat'
TYPE_USER_STATUS_UPDATE = 'user_status_update'

# ------------------------------------------------------------------------------


def escape_csv_string(instr):
    if instr:
        instr = instr.strip('"\'')
        return '"{}"'.format(instr.replace('"', '\''))
    return ''


def to_date(epoch):
    if epoch:
        return datetime.fromtimestamp(epoch, UTC).isoformat()
    return ''

# ------------------------------------------------------------------------------


class TDB():

    def __init__(self, outdirectory, db: TelegramDB):
        assert outdirectory
        self._outdirectory = outdirectory
        self._db = db
        self._separator = CSV_SEPARATOR
        self._table_chats = {}
        self._table_contacts = {}
        self._table_dialogs = {}
        self._table_enc_chats = {}
        self._table_media = {}
        self._table_messages = {}
        self._table_sent_files = {}
        self._table_users = {}
        self._table_user_settings = {}
        self.separator = f"{'-' * 80}\n"

    def __parse_table_chats(self):
        entries = self._db.get_chats()
        for entry in entries:
            uid = entry.uid
            logger.info('parsing chats, entry uid: %s', uid)
            self._table_chats[uid] = TChat(entry)

    def __save_table_chats(self, outdir):
        path = os.path.join(outdir, 'table_chats.txt')
        with open(path, 'w+', encoding='utf-8') as f:
            for _uid, chat in self._table_chats.items():
                f.write(self.separator)
                f.write(chat.dump('\n\n'))

    def __parse_table_contacts(self):
        entries = self._db.get_contacts()
        for entry in entries:
            uid = entry.uid
            logger.info('parsing contacts, entry uid: %s', uid)
            self._table_contacts[uid] = entry.mutual

    def __save_table_contacts(self, outdir):
        path = os.path.join(outdir, 'table_contacts.txt')
        with open(path, 'w+', encoding='utf-8') as f:
            for uid, mutual in self._table_contacts.items():
                f.write(self.separator)
                f.write(f'uid: {uid} mutual: {mutual}\n')
                if uid in self._table_users:
                    user = self._table_users[uid]
                    f.write(f'From [users] -> {user.full_text_id}\n')
                else:
                    f.write('User uid missing in [users]\n')

    def __parse_table_dialogs(self):
        entries = self._db.get_dialogs()
        for entry in entries:
            did = entry.did
            assert did
            assert did not in self._table_dialogs
            logger.info('parsing dialogs, entry did: %s', did)
            dialog = TDialog(entry)
            self._table_dialogs[did] = dialog

    def __save_table_dialogs(self, outdir):
        path = os.path.join(outdir, 'table_dialogs.txt')
        with open(path, 'w+', encoding='utf-8') as f:
            for _did, dialog in self._table_dialogs.items():
                f.write(self.separator)
                f.write(dialog.dump())

    def __parse_table_enc_chats(self):
        entries = self._db.get_enc_chats()
        for entry in entries:
            uid = entry.uid
            assert uid
            assert uid not in self._table_enc_chats
            logger.info('parsing enc_chats, entry uid: %s', uid)
            tec = TEchat(entry)
            self._table_enc_chats[uid] = tec

    def __save_table_enc_chats(self, outdir):
        path = os.path.join(outdir, 'table_enc_chats.txt')
        with open(path, 'w+', encoding='utf-8') as f:
            for uid, tec in self._table_enc_chats.items():
                assert uid == tec.uid
                f.write(self.separator)
                f.write(tec.dump())

    def __parse_table_media(self):
        entries = self._db.get_media()
        for entry in entries:
            mid = entry.mid
            assert mid
            logger.info('parsing media_v2, entry mid: %s', mid)
            media = TMedia(entry)
            self._table_media[mid] = media

    def __save_table_media(self, outdir):
        path = os.path.join(outdir, 'table_media.txt')
        with open(path, 'w+', encoding='utf-8') as f:
            for mid, media in self._table_media.items():
                f.write(self.separator)
                f.write(media.dump())

    def __parse_table_messages(self):
        entries = self._db.get_messages()
        for entry in entries:
            mid = entry.mid
            assert mid
            # assert mid not in self._table_messages
            logger.info('parsing messages, entry mid: %s', mid)

            message = TMessage(entry)

            # The difference should be less than 5 seconds.
            date_from_blob = message.message_date_from_blob
            if date_from_blob and date_from_blob != entry.date:
                if message.date and date_from_blob > message.date:
                    assert (date_from_blob - message.message_date_from_blob) < 5
                else:
                    assert (message.message_date_from_blob - date_from_blob) < 5

            self._table_messages[mid] = message

    def __save_table_messages(self, outdir):
        path = os.path.join(outdir, 'table_messages.txt')
        with open(path, 'w+', encoding='utf-8') as f:
            for mid, tmsg in self._table_messages.items():
                f.write(self.separator)
                f.write(tmsg.dump())

    def __parse_table_sent_files(self):
        entries = self._db.get_sent_files()
        for entry in entries:
            uid = entry.uid
            assert uid
            assert uid not in self._table_sent_files
            logger.info('parsing sent_files, entry uid: %s', uid)
            # Some old telegram versions have not 'type' / 'parent'.
            sentfile = TSentFile(entry)
            self._table_sent_files[uid] = sentfile

    def __save_table_sent_files(self, outdir):
        path = os.path.join(outdir, 'table_sent_files.txt')
        with open(path, 'w+', encoding='utf-8') as f:
            for uid, sentfile in self._table_sent_files.items():
                assert uid == sentfile.uid
                f.write(self.separator)
                f.write(sentfile.dump())

    def __parse_table_users(self):
        entries = self._db.get_users()
        user_self_set = False
        for entry in entries:
            uid = entry.uid
            assert uid
            assert uid not in self._table_users
            logger.info('parsing users, entry uid: %s', uid)
            user = TUser(entry)

            if user.is_self:
                assert not user_self_set
                user_self_set = True

            self._table_users[uid] = user
        assert user_self_set

    def __save_table_users(self, outdir):
        path = os.path.join(outdir, 'table_users.txt')
        with open(path, 'w+', encoding='utf-8') as f:
            for uid, user in self._table_users.items():
                assert uid == user.uid
                f.write(self.separator)
                # It seems status is the last update timestamp of the status,
                # but only if the number is greater than 0.
                if user.status > 0:
                    status = to_date(user.status)
                else:
                    status = user.status
                f.write(user.dump())

    def __parse_table_user_settings(self):
        entries = self._db.get_user_settings()
        for entry in entries:
            uid = entry.uid
            assert uid
            assert uid not in self._table_user_settings
            logger.info('parsing user_settings, entry uid: %s', uid)
            tus = TUserSettings(entry)
            self._table_user_settings[uid] = tus

    def __save_table_user_settings(self, outdir):
        path = os.path.join(outdir, 'table_user_settings.txt')
        with open(path, 'w+', encoding='utf-8') as f:
            for _uid, tus in self._table_user_settings.items():
                f.write(self.separator)
                # if uid in self._table_users:
                #     tid = self._table_users[uid].full_text_id
                #     f.write(f'From [users] -> {tid}\n\n')
                # else:
                #     f.write('User uid missing in [users]\n\n')
                f.write(tus.dump())

    def parse(self):
        # TODO check new 9.2.0 tables
        self.__parse_table_chats()
        self.__parse_table_contacts()
        self.__parse_table_dialogs()
        self.__parse_table_enc_chats()
        self.__parse_table_media()
        self.__parse_table_messages()
        self.__parse_table_sent_files()
        self.__parse_table_users()
        self.__parse_table_user_settings()

    def save_parsed_tables(self):
        self.__save_table_chats(self._outdirectory)
        self.__save_table_contacts(self._outdirectory)
        self.__save_table_dialogs(self._outdirectory)
        self.__save_table_enc_chats(self._outdirectory)
        self.__save_table_media(self._outdirectory)
        self.__save_table_messages(self._outdirectory)
        self.__save_table_sent_files(self._outdirectory)
        self.__save_table_users(self._outdirectory)
        self.__save_table_user_settings(self._outdirectory)

    def __chats_to_timeline(self):
        for uid, chat in self._table_chats.items():
            row = TRow()
            row.source = 'chats'
            row.id = uid
            row.dialog = chat.shortest_id
            row.dialog_type = chat.chat_type
            sname = get_obj_value(chat.blob, 'sname', '')
            svalue = TRow.dict_to_string(chat.dict_id)
            row.content = f'{sname} {svalue}'
            if chat.creation_date:
                row.timestamp = to_date(chat.creation_date)
                row.type = TYPE_CHAT_CREATION_DATE
            else:
                row.type = sname

            if (flags := get_obj_value(chat.blob, 'flags')):
                df = {}
                if get_obj_value(flags, 'is_creator'):
                    df['creator'] = 'true'
                if get_obj_value(flags, 'is_left'):
                    df['left'] = 'true'
                if get_obj_value(flags, 'is_broadcast'):
                    df['broadcast'] = 'true'
                if get_obj_value(flags, 'is_megagroup'):
                    df['megagroup'] = 'true'
                if get_obj_value(flags, 'has_participants_count'):
                    df['members'] = get_obj_value(
                        chat.blob, 'participants_count')
                row.content += f' {TRow.dict_to_string(df)}'

            if chat.photo_info:
                row.media = chat.photo_info
            yield row

    def __dialogs_to_timeline(self):
        for did, dialog in self._table_dialogs.items():
            row = TRow()
            row.source = 'dialogs'
            row.id = did

            if did.bit_length() > 32:
                cid = did >> 32
            elif did < 0:
                cid = (-1 * did)
            else:
                cid = did

            # TODO refactor this! Missing negative conversion!!
            if cid in self._table_chats:
                row.dialog = self._table_chats[cid].shortest_id
                row.dialog_type = self._table_chats[cid].chat_type
            elif cid in self._table_enc_chats:
                row.dialog = self._table_enc_chats[cid].shortest_id
                row.dialog_type = 'encrypted 1-1'
            else:
                row.dialog_type = '1-1'

            row.content = 'dialog unread_count:{} inbox_max:{} outbox_max:{} ' \
                'pts:{} last_mid:{}'.format(
                    dialog.unread_count, dialog.inbox_max, dialog.outbox_max,
                    dialog.pts, dialog.last_mid)

            row.timestamp = to_date(dialog.date)
            row.type = TYPE_CHAT_LAST_UPDATE

            yield row

    def __enc_chats_to_timeline(self):
        for uid, echat in self._table_enc_chats.items():
            row = TRow()
            row.source = 'enc_chats'
            row.id = uid
            row.dialog = echat.shortest_id
            row.dialog_type = 'encrypted 1-1'

            admin_id_short = ''
            if echat.admin_id in self._table_users:
                admin_id_short = self._table_users[echat.admin_id].shortest_id

            participant_id_short = ''
            if echat.participant_id:
                if echat.participant_id in self._table_users:
                    participant_id_short = \
                        self._table_users[echat.participant_id].shortest_id

            row.from_who = admin_id_short
            row.from_id = echat.admin_id
            row.to_who = participant_id_short
            row.to_id = echat.participant_id

            sname = get_obj_value(echat.blob, 'sname', '')
            svalue = TRow.dict_to_string(echat.dict_id)

            row.content = f'{sname} {svalue}'
            if echat.creation_date:
                row.timestamp = to_date(echat.creation_date)
                row.type = TYPE_CHAT_CREATION_DATE
            yield row

            if echat.key_date:
                row.timestamp = to_date(echat.key_date)
                row.type = TYPE_KEY_DATE
                yield row

    def __message_media(self, mid, msg):
        # pylint: disable=R0201
        assert mid
        if not (media := get_obj_value(msg.blob, 'media')):
            return None
        media_field = None
        if (document := get_obj_value(media, 'document')):
            result = []
            result.append('document')
            info = {'id': get_obj_value(document, 'id'),
                    'date': to_date(get_obj_value(document, 'date')),
                    'mime': get_obj_value(document, 'mime_type'),
                    'size': get_obj_value(document, 'size'),
                    }
            result.append(' '.join(f'{k}:{v}' for k, v in info.items()))

            for entry in get_obj_value(document, 'attributes', []):
                if get_obj_value(entry, 'sname') == 'document_attribute_filename':
                    file_name = get_obj_value(entry, 'file_name')
                    result.append(f'file_name:{file_name}')
            media_field = ' '.join(result)
        elif (photo := get_obj_value(media, 'photo')):
            result = []
            result.append('photo')
            info = {'id': get_obj_value(photo, 'id'),
                    'date': to_date(get_obj_value(photo, 'date')),
                    }
            result.append(' '.join(f'{k}:{v}' for k, v in info.items()))

            if (sizes := get_obj_value(document, 'sizes')):
                for entry in sizes:
                    if not (location := get_obj_value(entry, 'location')):
                        continue
                    w = get_obj_value(location, 'w')
                    h = get_obj_value(location, 'h')
                    size = get_obj_value(location, 'size')
                    volume_id = get_obj_value(location, 'volume_id')
                    local_id = get_obj_value(location, 'local_id')
                    result.append(f'{w}x{h}({size} bytes):{volume_id}_{local_id}.jpg')
            media_field = ' '.join(result)
        elif (webpage := get_obj_value(media, 'webpage')):
            result = []
            result.append('webpage')
            info = {'id': get_obj_value(webpage, 'id'),
                    'url': get_obj_value(webpage, 'url', ''),
                    }
            result.append(' '.join(f'{k}:{v}' for k, v in info.items()))
            if (title := get_obj_value(webpage, 'title')):
                result.append(f'title:{title}')

            if (description := get_obj_value(webpage, 'description')):
                result.append(f'description:{description}')
            media_field = ' '.join(result)
        else:
            media_field = get_obj_value(media, 'sname')
        return media_field

    def __messages_to_timeline(self):
        # pylint: disable=R0912,R0915
        for mid, msg in self._table_messages.items():
            row = TRow()
            row.source = 'messages'
            row.id = mid

            if (from_id := get_obj_value(msg.blob, 'from_id.user_id')):
                row.from_id = from_id
                if from_id in self._table_users:
                    user = self._table_users[from_id]
                    row.from_who = user.shortest_id
                else:
                    row.from_who = from_id

            dialog, msg_seq = msg.dialog_and_sequence
            row.extra.update({'dialog': dialog, 'sequence': msg_seq})

            if dialog in self._table_chats:
                row.dialog = self._table_chats[dialog].shortest_id
                row.dialog_type = self._table_chats[dialog].chat_type
            elif dialog in self._table_enc_chats:
                row.dialog = self._table_enc_chats[dialog].shortest_id
                row.dialog_type = 'encrypted 1-1'
            else:
                row.dialog_type = '1-1'

            to_who, to_type = msg.to_id_and_type
            assert to_who
            row.to_id = to_who
            if TYPE_MSG_TO_USER == to_type:
                if to_who in self._table_users:
                    user = self._table_users[to_who]
                    row.to_who = user.shortest_id
            elif TYPE_MSG_TO_CHANNEL == to_type:
                assert dialog == to_who
                if to_who in self._table_chats:
                    chat = self._table_chats[to_who]
                    row.to_who = chat.shortest_id
            else:
                logger.error('message %s, unmanaged to_id!', msg.mid)
                row.to_who = to_who

            row.type = get_obj_value(msg.blob, 'sname')
            action, action_dict = msg.action_string_and_dict
            if action:
                assert not msg.message_content
                row.extra.update(action_dict)
                row.content = action
            else:
                row.content = msg.message_content.strip('"\'')

            if msg.reply_blob:
                reply_id = get_obj_value(msg.reply_blob, 'id')
                reply_date = to_date(get_obj_value(msg.reply_blob, 'date'))
                reply_content = get_obj_value(msg.reply_blob, 'message', '').strip('"\'')
                row.content += f' [IS REPLY TO MSG ID {reply_id} {reply_date}]\n{reply_content}'

            if (fwd_from := get_obj_value(msg.blob, 'fwd_from')):
                fwd_from_id = get_obj_value(fwd_from, 'from_id')
                fwd_from_date = to_date(get_obj_value(fwd_from, 'date'))
                row.content += f' [FORWARDED OF MSG BY {fwd_from_id} {fwd_from_date}]'

            if (views := get_obj_value(msg.blob, 'views')):
                row.extra.update({'views': views})

            if (media := self.__message_media(mid, msg)):
                row.media = escape_csv_string(media)

            row.timestamp = to_date(msg.message_date_from_blob)
            yield row

    def __users_to_timeline(self):
        for uid, user in self._table_users.items():
            row = TRow()
            row.source = 'users'
            row.id = uid
            row.from_who = user.shortest_id
            row.from_id = uid

            if user.status > 0:
                row.type = TYPE_USER_STATUS_UPDATE
                row.timestamp = to_date(user.status)

            row.content = TRow.dict_to_string(user.dict_id)
            ui_dict = {}
            if (flags := get_obj_value(user.blob, 'flags')):
                if get_obj_value(flags, 'has_status'):
                    ui_dict['status'] = get_obj_value(user.blob, 'status.sname')
                if get_obj_value(flags, 'is_bot'):
                    ui_dict['bot'] = 'true'
                if get_obj_value(flags, 'is_mutual_contact'):
                    ui_dict['mutual_contact'] = 'true'
                elif get_obj_value(flags, 'is_contact'):
                    ui_dict['contact'] = 'true'
            if ui_dict:
                row.content += f' {TRow.dict_to_string(ui_dict)}'

            if user.photo_info:
                row.media = user.photo_info
            yield row

    def create_timeline(self):
        path = os.path.join(self._outdirectory, 'timeline.csv')
        with open(path, 'w+', encoding='utf-8') as f:
            line = self._separator.join(TRow.FIELDS)
            f.write(f'{line}\n')
            f.writelines(
                [f'{x.to_row_string(self._separator)}\n' for x in self.__chats_to_timeline()])
            f.writelines(
                [f'{x.to_row_string(self._separator)}\n' for x in self.__dialogs_to_timeline()])
            f.writelines(
                [f'{x.to_row_string(self._separator)}\n' for x in self.__enc_chats_to_timeline()])
            f.writelines(
                [f'{x.to_row_string(self._separator)}\n' for x in self.__users_to_timeline()])
            f.writelines(
                [f'{x.to_row_string(self._separator)}\n' for x in self.__messages_to_timeline()])

# ------------------------------------------------------------------------------


class TBase:
    BLOB_COLUMN = 'data'

    def __init__(self, entry):
        self.entry = entry

    def __getattr__(self, name):
        if not name.startswith('_') and hasattr(self.entry, name):
            attr_name = f"_lazy_{name}"
            if not hasattr(self, attr_name):
                if (ret := getattr(self.entry, name)) is None:
                    return ret
                setattr(self, attr_name, ret)
            return getattr(self, attr_name)
        cls_name = type(self.entry).__name__
        raise AttributeError(f"'{cls_name}' object has no attribute '{name}'")

    @property
    def entry(self):
        return self._entry

    @entry.setter
    def entry(self, value):
        del_lazy_attr(self)
        self._entry = value

    @lazy_property
    def blob(self):
        blob = getattr(self.entry, f'{self.BLOB_COLUMN}_blob')
        return pythonic(blob)

    @lazy_property
    def vkeys(self):
        cols = self.entry.__table__.columns
        vkeys = (k for k, v in cols.items() if not isinstance(v.type, BLOB))
        return vkeys

    def get_vdata(self, attr):
        value = getattr(self, attr)
        if attr == 'date':
            return f'{attr}: {value} [{to_date(value)}]'
        else:
            return f'{attr}: {value}'

    @lazy_property
    def vdata_list(self):
        return [self.get_vdata(x) for x in self.vkeys]

    @lazy_property
    def vdata(self):
        return ' '.join(self.vdata_list)

    @lazy_property
    def bdata(self):
        return format_dict(self.blob)

    def dump(self, newline='\n'):
        return f'{self.vdata}{newline}{self.bdata}{newline}'


class TRow:
    FIELDS = ('timestamp', 'source', 'id', 'type', 'from', 'from_id', 'to',
              'to_id', 'dialog', 'dialog_type', 'content', 'media', 'extra')

    def __init__(self):
        self._timestamp = ''
        self._source = ''
        self._id = ''
        self._type = ''
        self._from_who = ''
        self._from_id = ''
        self._to_who = ''
        self._to_id = ''
        self._dialog = ''
        self._dialog_type = ''
        self._content = ''
        self._media = ''
        self._extra = {}

    @classmethod
    def dict_to_string(cls, obj: dict):
        return ' '.join(f"{k}:{v}" for k, v in obj.items())

    def to_row_string(self, separator):
        # pylint: disable=W1308
        data = [self._timestamp, self._source, self._id, self._type,
                self._from_who, self._from_id, self._to_who, self._to_id,
                self._dialog, self._dialog_type,
                escape_csv_string(self._content), self._media,
                escape_csv_string(TRow.dict_to_string(self._extra))]
        return str(separator).join(str(x) for x in data)

    @property
    def timestamp(self):
        return self._timestamp

    @timestamp.setter
    def timestamp(self, value):
        self._timestamp = value

    @property
    def source(self):
        return self._source

    @source.setter
    def source(self, value):
        self._source = value

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, value):
        self._id = value

    @property
    def type(self):
        return self._type

    @type.setter
    def type(self, value):
        self._type = value

    @property
    def from_who(self):
        return self._from_who

    @from_who.setter
    def from_who(self, value):
        self._from_who = value

    @property
    def from_id(self):
        return self._from_id

    @from_id.setter
    def from_id(self, value):
        self._from_id = value

    @property
    def to_who(self):
        return self._to_who

    @to_who.setter
    def to_who(self, value):
        self._to_who = value

    @property
    def to_id(self):
        return self._to_id

    @to_id.setter
    def to_id(self, value):
        self._to_id = value

    @property
    def dialog(self):
        return self._dialog

    @dialog.setter
    def dialog(self, value):
        self._dialog = value

    @property
    def dialog_type(self):
        return self._dialog_type

    @dialog_type.setter
    def dialog_type(self, value):
        self._dialog_type = value

    @property
    def content(self):
        return self._content

    @content.setter
    def content(self, value):
        self._content = value

    @property
    def media(self):
        return self._media

    @media.setter
    def media(self, value):
        self._media = value

    @property
    def extra(self):
        return self._extra

    @extra.setter
    def extra(self, value):
        pass

# ------------------------------------------------------------------------------


class TChat(TBase):
    __slots__ = ['uid', 'name', 'data']

    @lazy_property
    def dict_id(self):
        dictid = {}
        dictid['title'] = get_obj_value(self.blob, 'title')
        if get_obj_value(self.blob, 'flags.has_username'):
            dictid['username'] = get_obj_value(self.blob, 'username')
        return dictid

    @lazy_property
    def chat_type(self):
        ct = ''
        if not get_obj_value(self.blob, 'flags'):
            return ct
        is_broadcast = get_obj_value(self.blob, 'flags.is_broadcast')
        is_megagroup = get_obj_value(self.blob, 'flags.is_megagroup')
        if is_broadcast:
            assert not is_megagroup
            ct = '1-N'
        elif is_megagroup:
            assert not is_broadcast
            ct = 'N-N'
        else:
            ct = '?-?'
        if get_obj_value(self.blob, 'flags.has_username'):
            ct += ' pub'
        else:
            ct += ' prv'
        if get_obj_value(self.blob, 'flags.is_left'):
            ct += ' left'
        return ct

    @lazy_property
    def shortest_id(self):
        sid = ''
        if (sid := get_obj_value(self.blob, 'username', '')):
            pass
        elif (sid := get_obj_value(self.blob, 'title', '')):
            pass
        else:
            sid = self.uid
        return sid

    @lazy_property
    def creation_date(self):
        return get_obj_value(self.blob, 'date')

    @lazy_property
    def photo_info(self):
        info = []
        if (photo := get_obj_value(self.blob, 'photo')):
            info.append(get_obj_value(photo, 'sname'))
            if (photo_small := get_obj_value(photo, 'photo_small')):
                info.append('small:')
                volume_id = get_obj_value(photo_small, 'volume_id')
                local_id = get_obj_value(photo_small, 'local_id')
                info.append(f'{volume_id}_{local_id}.jpg')
            if (photo_big := get_obj_value(photo, 'photo_big')):
                info.append('big:')
                volume_id = get_obj_value(photo_big, 'volume_id')
                local_id = get_obj_value(photo_big, 'local_id')
                info.append(f'{volume_id}_{local_id}.jpg')
        return ' '.join(info)

# ------------------------------------------------------------------------------


class TDialog(TBase):
    __slots__ = ['did', 'date', 'unread_count', 'last_mid', 'inbox_max',
                 'outbox_max', 'last_mid_i', 'unread_count_i', 'pts', 'date_i',
                 'pinned', 'flags', 'folder_id', 'data', 'unread_reactions',
                 'last_mid_group', 'ttl_period']

    @lazy_property
    def vdata(self):
        newline = '\n'
        result = []
        vdata = self.vdata_list
        result.append(f'{", ".join(vdata[:(e := 2)])}{newline}')
        for _ in range(9):
            data = vdata[(s := e):(e := s + 5)]
            if not data:
                break
            result.append(f'{" ".join(data)}{newline}')
        result.append(newline)
        return ''.join(result)

    @lazy_property
    def bdata(self):
        return ''

    def dump(self, newline='\n'):
        return f'{self.vdata}{newline}{self.bdata}{newline}'


# ------------------------------------------------------------------------------


class TEchat(TBase):
    __slots__ = ['uid', 'user', 'name', 'data', 'g', 'authkey', 'ttl', 'layer',
                 'seq_in', 'seq_out', 'use_count', 'exchange_id', 'key_date',
                 'fprint', 'fauthkey', 'khash', 'in_seq_no', 'admin_id',
                 'mtproto_seq']

    def __init__(self, entry):
        super().__init__(entry)
        if (admin_id := get_obj_value(self.blob, 'admin_id')):
            assert self.admin_id == admin_id
        if (participant_id := get_obj_value(self.blob, 'participant_id')):
            if not self.user == self.admin_id:
                assert self.user == participant_id

    @property
    def dict_id(self):
        dictid = {'name': self.name, 'ttl': self.ttl,
                  'seq_in': self.seq_in, 'seq_out': self.seq_out}
        return dictid

    @property
    def shortest_id(self):
        return self.name or self.uid

    @property
    def creation_date(self):
        return get_obj_value(self.blob, 'date')

    @property
    def participant_id(self):
        # Normally the db user entry is equal to blob participant_id, but there
        # are cases where user=admin_id=admin_id_blob
        if participant_id := get_obj_value(self.blob, 'participant_id'):
            return participant_id
        if self.admin_id != self.user:
            return self.user
        logger.warning('encrypted chat %s has not a valid participant_id!',
                       self.uid)
        return None

    @lazy_property
    def vdata(self):
        newline = '\n'
        result = []
        vdata = self.vdata_list
        result.append(f'{", ".join(vdata[:(e := 3)])}{newline}')
        for _ in range(9):
            data = vdata[(s := e):(e := s + 5)]
            if not data:
                break
            result.append(f'{" ".join(data)}{newline}')
        result.append(newline)
        return ''.join(result)

    def dump(self, newline='\n'):
        return f'{self.vdata}{newline}{self.bdata}{newline}'

# ------------------------------------------------------------------------------


class TMedia(TBase):
    __slots__ = ['mid', 'uid', 'date', 'type', 'data']


# ------------------------------------------------------------------------------


class TMessage(TBase):
    __slots__ = ['mid', 'uid', 'read_state', 'send_state', 'date', 'data',
                 'out', 'ttl', 'media', 'replydata', 'imp', 'mention',
                 'forwards', 'replies_data', 'thread_reply_id', 'is_channel',
                 'reply_to_message_id', 'custom_params', 'group_id',
                 'reply_to_story_id']

    @lazy_property
    def reply_blob(self):
        blob = getattr(self.entry, 'replydata_blob')
        return pythonic(blob)

    @property
    def to_id_and_type(self):
        to_id = get_obj_value(self.blob, 'peer_id')
        sname = get_obj_value(to_id, 'sname')
        if sname == 'peer_channel':
            return (get_obj_value(to_id, 'channel_id'), TYPE_MSG_TO_CHANNEL)
        if sname == 'peer_user':
            return (get_obj_value(to_id, 'user_id'), TYPE_MSG_TO_USER)
        return (None, None)

    @property
    def message_content(self):
        if (message := get_obj_value(self.blob, 'message')):
            return escape_csv_string(message)
        return ''

    @property
    def message_date_from_blob(self):
        return get_obj_value(self.blob, 'date')

    @property
    def dialog_and_sequence(self):
        dialog = None
        msg_seq = None
        if self.mid.bit_length() > 32:
            dialog = (self.mid >> 32) & 0xFFFFFFFF
            msg_seq = self.mid & 0xFFFFFFFF
            assert self.uid < 0
            assert dialog == (-1 * self.uid)
        else:
            assert self.uid
            if self.uid.bit_length() > 32:
                dialog = (self.uid >> 32) & 0xFFFFFFFF
            elif self.uid < 0:
                dialog = (-1 * self.uid)
            else:
                dialog = self.uid
            if self.mid > 0:
                msg_seq = self.mid
            else:
                msg_seq = (self.mid * -1) - + 210000
        return dialog, msg_seq

    @property
    def action_string_and_dict(self):
        if (action := get_obj_value(self.blob, 'action')):
            return get_obj_value(action, 'sname'), action
        return None, None

    @lazy_property
    def breply(self):
        return format_dict(self.reply_blob)

    def dump(self, newline='\n'):
        if self.reply_blob:
            return (f'{self.vdata}{newline}'
                    f'{self.bdata}{newline}'
                    f'----- IS REPLY  TO ---{newline}'
                    f'{self.breply}{newline}')
        return f'{self.vdata}{newline}{self.bdata}{newline}'

# ------------------------------------------------------------------------------


class TSentFile(TBase):
    __slots__ = ['uid', 'type', 'data', 'parent']


# ------------------------------------------------------------------------------


class TUser(TBase):
    __slots__ = ['uid', 'name', 'status', 'data']

    def __init__(self, model):
        super().__init__(model)
        assert self.uid == get_obj_value(self.blob, 'id')

    # The following are useful fiels extracted from the blob.

    @lazy_property
    def first_name(self):
        return get_obj_value(self.blob, 'first_name', '')

    @lazy_property
    def last_name(self):
        return get_obj_value(self.blob, 'last_name', '')

    @lazy_property
    def username(self):
        return get_obj_value(self.blob, 'username', '')

    @lazy_property
    def phone(self):
        return get_obj_value(self.blob, 'phone', '')

    @lazy_property
    def full_text_id(self):
        return (f'uid: {self.uid} nick: {self.username} '
                f'fullname: {self.first_name} {self.last_name} '
                f'phone: {self.phone}')

    @lazy_property
    def dict_id(self):
        keys = ['username', 'first_name', 'last_name', 'phone']
        return {x: y for x in keys if (y := getattr(self, x))}

    @lazy_property
    def shortest_id(self):
        if self.username:
            sis = self.username
        elif self.first_name or self.last_name:
            if self.first_name and self.last_name:
                sis = f'{self.first_name} {self.last_name}'
            elif self.first_name:
                sis = self.first_name
            else:
                sis = self.last_name
        else:
            sis = self.uid

        if self.is_self:
            return f'{sis} (owner)'
        return sis

    @lazy_property
    def photo_info(self):
        info = []
        if (photo := get_obj_value(self.blob, 'photo')):
            info.append(get_obj_value(photo, 'sname'))
            if (photo_small := get_obj_value(photo, 'photo_small')):
                info.append('small:')
                volume_id = get_obj_value(photo_small, 'volume_id')
                local_id = get_obj_value(photo_small, 'local_id')
                info.append(f'{volume_id}_{local_id}.jpg')
            if (photo_big := get_obj_value(photo, 'photo_big')):
                info.append('big:')
                volume_id = get_obj_value(photo_big, 'volume_id')
                local_id = get_obj_value(photo_big, 'local_id')
                info.append(f'{volume_id}_{local_id}.jpg')
        return ' '.join(info)

    @lazy_property
    def is_self(self):
        return get_obj_value(self.blob, 'flags.is_self', False)

# ------------------------------------------------------------------------------


class TUserSettings(TBase):
    __slots__ = ['uid', 'info', 'pinned']
    BLOB_COLUMN = 'info'


# ------------------------------------------------------------------------------
