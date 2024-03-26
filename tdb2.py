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

import datetime
import os
import logger
from database import TelegramDB
from datatype.utils import search_attribute

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
        return datetime.datetime.utcfromtimestamp(epoch).isoformat()
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

    def __parse_table_chats(self):
        entries = self._db.get_chats()
        for entry in entries:
            uid = entry.uid
            assert uid
            assert uid not in self._table_chats
            logger.info('parsing chats, entry uid: %s', uid)
            self._table_chats[uid] = TChat(entry)

    def __save_table_chats(self, outdir):
        with open(os.path.join(outdir, 'table_chats.txt'), mode='w',
                  encoding='utf-8') as fo:
            separator = f"{'-' * 80}\n"
            for uid, chat in self._table_chats.items():
                fo.write(separator)
                fo.write(f'uid: {uid} name: {chat.name}\n\n')
                fo.write(f'{chat.blob}\n\n')

    def __parse_table_contacts(self):
        entries = self._db.get_contacts()
        for entry in entries:
            uid = entry.uid
            assert uid
            assert uid not in self._table_contacts
            logger.info('parsing contacts, entry uid: %s', uid)
            self._table_contacts[uid] = entry.mutual

    def __save_table_contacts(self, outdir):
        with open(os.path.join(outdir, 'table_contacts.txt'),
                  mode='w', encoding='utf-8') as fo:
            separator = f"{'-' * 80}\n"
            for uid, mutual in self._table_contacts.items():
                fo.write(separator)
                fo.write(f'uid: {uid} mutual: {mutual}\n')
                if uid in self._table_users:
                    user = self._table_users[uid]
                    fo.write(f'From [users] -> {user.full_text_id}\n')
                else:
                    fo.write('User uid missing in [users]\n')

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
        with open(os.path.join(outdir, 'table_dialogs.txt'),
                  mode='w', encoding='utf-8') as fo:
            separator = f"{'-' * 80}\n"
            for did, dialog in self._table_dialogs.items():
                fo.write(separator)
                date_string = to_date(dialog.date)
                fo.write(
                    f'did: {did}, date: {dialog.date} [{date_string}]\n'
                    f'unread_count: {dialog.unread_count}, last_mid: {dialog.last_mid}, inbox_max: {dialog.inbox_max}, '
                    f'outbox_max: {dialog.outbox_max}, last_mid_i: {dialog.last_mid_i}\n'
                    f'unread_count_i: {dialog.unread_count_i}, pts: {dialog.pts}, date_i: {dialog.date_i}, pinned: {dialog.pinned}, '
                    f'flags: {dialog.flags}\n\n')

    def __parse_table_enc_chats(self):
        entries = self._db.get_enc_chats()
        for entry in entries:
            uid = entry.uid
            assert uid
            assert uid not in self._table_enc_chats
            logger.info('parsing enc_chats, entry uid: %s', uid)
            # [20200408] Check if we have a blob of bytes.
            if isinstance(entry['data'], bytes):
                blob = self._blob_parser.parse_blob(entry['data'])
            else:
                blob = None
                logger.error('enc_chats uid:%s blob is not made by bytes, '
                             'skipping it', uid)

            admin_id = getattr(blob, 'admin_id', None)
            if admin_id:
                assert entry.admin_id == admin_id
            participant_id = getattr(blob, 'participant_id', None)
            if participant_id:
                if not entry.user == entry.admin_id:
                    assert entry.user == participant_id

            tec = TEchat(entry)
            self._table_enc_chats[uid] = tec

    def __save_table_enc_chats(self, outdir):
        with open(os.path.join(outdir, 'table_enc_chats.txt'),
                  mode='w', encoding='utf-8') as fo:
            separator = f"{'-' * 80}\n"
            for uid, tec in self._table_enc_chats.items():
                assert uid == tec.uid
                fo.write(separator)
                fo.write(
                    'uid: {} user: {} name: {}\n\ng: {}\nauthkey: {}\n'
                    'ttl: {} layer: {} seq_in: {} seq_out: {} use_count: {}\n'
                    'exchange_id: {} key_date: {} fprint: {}\n'
                    'fauthkey: {}\nkhash: {}\nin_seq_no: {} admin_id: {} '
                    'mtproto_seq: {}\n'.format(
                        tec.uid, tec.user, tec.name, tec.g, tec.authkey,
                        tec.ttl, tec.layer, tec.seq_in, tec.seq_out,
                        tec.use_count, tec.exchange_id, tec.key_date,
                        tec.fprint, tec.fauthkey, tec.khash, tec.in_seq_no,
                        tec.admin_id, tec.mtproto_seq))
                fo.write('\n{}\n\n'.format(tec.blob))

    def __parse_table_media(self):
        entries = self._db.get_media()
        for entry in entries:
            mid = entry.mid
            assert mid
            logger.info('parsing media_v2, entry mid: %s', mid)
            media = TMedia(entry)
            self._table_media[mid] = media

    def __save_table_media(self, outdir):
        with open(os.path.join(outdir, 'table_media.txt'),
                  mode='w', encoding='utf-8') as fo:
            separator = f"{'-' * 80}\n"
            for mid, media in self._table_media.items():
                fo.write(separator)
                date_string = to_date(media.date)
                fo.write(
                    'mid: {} uid: {} date: {} [{}] type: {}\n'.format(
                        mid, media.uid, media.date, date_string,
                        media.type))
                if media.uid in self._table_users:
                    fo.write(
                        'From [users] -> {}\n\n'.format(
                            self._table_users[media.uid].full_text_id))
                else:
                    fo.write('User uid missing in [users]\n\n')
                fo.write('{}\n\n'.format(media.blob))

    def __parse_table_messages(self):
        entries = self._db.get_messages()
        for entry in entries:
            mid = entry.mid
            assert mid
            # assert mid not in self._table_messages
            logger.info('parsing messages, entry mid: %s', mid)
            replyblob = entry.replydata_blob

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
        with open(os.path.join(outdir, 'table_messages.txt'),
                  mode='w', encoding='utf-8') as fo:
            separator = f"{'-' * 80}\n"
            for mid, tmsg in self._table_messages.items():
                fo.write(separator)
                fo.write(
                    'mid: {} uid: {} read_state: {} send_state: {} '
                    'date: {} out: {} ttl: {} media: {} imp: {} '
                    'mention: {}\n'.format(
                        mid, tmsg.uid, tmsg.read_state, tmsg.send_state,
                        tmsg.date, tmsg.out, tmsg.ttl, tmsg.media,
                        tmsg.imp, tmsg.mention))
                if tmsg.uid in self._table_users:
                    fo.write(
                        'From [users] -> {}\n\n'.format(
                            self._table_users[tmsg.uid].full_text_id))
                else:
                    fo.write('User uid missing in [users]\n\n')
                fo.write('{}\n'.format(tmsg.blob))
                if tmsg.blob_reply:
                    fo.write(
                        '\n----- IS REPLY  TO ---\n\n{}\n'.format(
                            tmsg.blob_reply))
                fo.write('\n')

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
        with open(os.path.join(outdir, 'table_sent_files.txt'),
                  mode='w', encoding='utf-8') as fo:
            separator = f"{'-' * 80}\n"
            for uid, sentfile in self._table_sent_files.items():
                assert uid == sentfile.uid
                fo.write(separator)
                fo.write(f'uid: {uid} type: {sentfile.type} parent: {sentfile.parent}\n\n')
                fo.write(f'{sentfile.blob}\n\n')

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
        with open(os.path.join(outdir, 'table_users.txt'),
                  mode='w', encoding='utf-8') as fo:
            separator = f"{'-' * 80}\n"
            for uid, user in self._table_users.items():
                assert uid == user.uid
                fo.write(separator)
                # It seems status is the last update timestamp of the status,
                # but only if the number is greater than 0.
                if user.status > 0:
                    status = to_date(user.status)
                else:
                    status = user.status
                fo.write(f'uid: {user.uid} name: {user.name} status: {status}\n')
                fo.write(f'{user.full_text_id}\n\n')
                fo.write(f'{user.blob}\n\n')

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
        with open(os.path.join(outdir, 'table_user_settings.txt'),
                  mode='w', encoding='utf-8') as fo:
            separator = f"{'-' * 80}\n"
            for uid, tus in self._table_user_settings.items():
                fo.write(separator)
                fo.write(f'uid: {uid} pinned: {tus.pinned}\n')
                if uid in self._table_users:
                    tid = self._table_users[uid].full_text_id
                    fo.write(f'From [users] -> {tid}\n\n')
                else:
                    fo.write('User uid missing in [users]\n\n')
                fo.write(f'{tus.blob}\n\n')

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
            row.content = '{} {}'.format(
                chat.blob.sname, TRow.dict_to_string(chat.dict_id))

            if chat.creation_date:
                row.timestamp = to_date(chat.creation_date)
                row.type = TYPE_CHAT_CREATION_DATE
            else:
                row.type = chat.blob.sname

            flags = getattr(chat.blob, 'flags', None)
            if flags:
                df = {}
                if getattr(flags, 'creator', None):
                    df['creator'] = 'true'
                if getattr(flags, 'left', None):
                    df['left'] = 'true'
                if getattr(flags, 'broadcast', None):
                    df['broadcast'] = 'true'
                if getattr(flags, 'megagroup', None):
                    df['megagroup'] = 'true'
                if getattr(flags, 'has_participants_count', None):
                    df['members'] = chat.blob.participants_count
                row.content += ' {}'.format(TRow.dict_to_string(df))

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

            echat_sname = getattr(echat.blob, 'sname', '')
            row.content = '{} {}'.format(
                echat_sname, TRow.dict_to_string(echat.dict_id))

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
        media = getattr(msg.blob, 'media', None)
        if not media:
            return None
        media = media.media

        document = getattr(media, 'document', None)
        photo = getattr(media, 'photo', None)
        webpage = getattr(media, 'webpage', None)
        media_field = None
        if document:
            assert media.flags.has_document
            document = document.document

            ret_str = 'document id:{} date:{} mime:{} size:{}'.format(
                document.id, to_date(document.date.epoch),
                document.mime_type.string, document.size)

            for entry in document.document_attributes_array:
                if entry.document.sname == 'document_attribute_filename':
                    file_name = entry.document.file_name.string
                    ret_str += ' file_name:{}'.format(file_name)
            media_field = ret_str

        elif photo:
            assert media.flags.has_photo
            photo = photo.photo

            ret_str = 'photo id:{} date:{}'.format(
                photo.id, to_date(photo.date.epoch))

            for entry in photo.photo_size_array:
                ps = entry.photo_size
                file_location = getattr(ps, 'file_location', None)
                if file_location:
                    fl = file_location.file_location
                    ret_str += ' {}x{}({} bytes):{}_{}.jpg'.format(
                        ps.w, ps.h, ps.size, fl.volume_id, fl.local_id)
            media_field = ret_str

        elif webpage:
            webpage = webpage.webpage
            url_string = ''
            url = getattr(webpage, 'url', None)
            if url:
                url_string = url.string
            ret_str = 'webpage id:{} url:{}'.format(
                webpage.id, url_string)
            title = getattr(webpage, 'title', None)
            if title:
                ret_str += ' title:{}'.format(webpage.title.string)
            description = getattr(webpage, 'description', None)
            if description:
                ret_str += ' description:{}'.format(webpage.description.string)
            media_field = ret_str

        else:
            media_field = media.sname

        return media_field

    def __messages_to_timeline(self):
        # pylint: disable=R0912,R0915
        for mid, msg in self._table_messages.items():
            row = TRow()
            row.source = 'messages'
            row.id = mid

            if msg.blob.from_id:
                row.from_id = msg.blob.from_id
                if msg.blob.from_id in self._table_users:
                    user = self._table_users[msg.blob.from_id]
                    row.from_who = user.shortest_id
                else:
                    row.from_who = msg.blob.from_id

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

            row.type = msg.blob.sname
            action, action_dict = msg.action_string_and_dict
            if action:
                assert not msg.message_content
                row.extra.update(action_dict)
                row.content = action
            else:
                row.content = msg.message_content.strip('"\'')

            if msg.blob_reply:
                replied_msg = msg
                replied_msg.blob = msg.blob_reply
                replied_msg.blob_reply = None
                row.content += ' [IS REPLY TO MSG ID {} {}]\n{}'.format(
                    replied_msg.blob.id,
                    to_date(replied_msg.message_date_from_blob),
                    replied_msg.message_content.strip('"\''))

            fwd_from = getattr(msg.blob, 'fwd_from', None)
            if fwd_from:
                fwd_from = fwd_from.fwd_from
                row.content += ' [FORWARDED OF MSG BY {} {}]'.format(
                    fwd_from.from_id, to_date(fwd_from.date.epoch))

            views = getattr(msg.blob, 'views', None)
            if views:
                row.extra.update({'views': views})

            media = self.__message_media(mid, msg)
            if media:
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

            row.content = '{}'.format(TRow.dict_to_string(user.dict_id))
            ui_dict = {}
            flags = getattr(user.blob, 'flags', None)
            if flags:
                if flags.has_status:
                    ui_dict['status'] = user.blob.status.status.sname
                if user.blob.flags.is_bot:
                    ui_dict['bot'] = 'true'
                if user.blob.flags.is_mutual_contact:
                    ui_dict['mutual_contact'] = 'true'
                elif user.blob.flags.is_contact:
                    ui_dict['contact'] = 'true'
            if ui_dict:
                row.content += ' {}'.format(TRow.dict_to_string(ui_dict))

            if user.photo_info:
                row.media = user.photo_info
            yield row

    def create_timeline(self):
        with open(os.path.join(self._outdirectory, 'timeline.csv'),
                  mode='w', encoding='utf-8') as fo:
            fo.write('{}\n'.format(self._separator.join(TRow.fieldsnames())))

            for row in self.__chats_to_timeline():
                fo.write('{}\n'.format(row.to_row_string(self._separator)))

            for row in self.__dialogs_to_timeline():
                fo.write('{}\n'.format(row.to_row_string(self._separator)))

            for row in self.__enc_chats_to_timeline():
                fo.write('{}\n'.format(row.to_row_string(self._separator)))

            for row in self.__users_to_timeline():
                fo.write('{}\n'.format(row.to_row_string(self._separator)))

            for row in self.__messages_to_timeline():
                fo.write('{}\n'.format(row.to_row_string(self._separator)))

# ------------------------------------------------------------------------------


class TBase:

    def __init__(self, model):
        self.model = model


class TUIDModel(TBase):

    @property
    def blob(self):
        return self.model.blob

    @property
    def uid(self):
        return self.model.uid


class TRow():

    # def __init__(self):
    #     self._timestamp = ''
    #     self._source = ''
    #     self._id = ''
    #     self._type = ''
    #     self._from_who = ''
    #     self._from_id = ''
    #     self._to_who = ''
    #     self._to_id = ''
    #     self._dialog = ''
    #     self._dialog_type = ''
    #     self._content = ''
    #     self._media = ''
    #     self._extra = {}

    def fieldsnames():
        # pylint: disable=E0211,R0201
        return ('timestamp', 'source', 'id', 'type',
                'from', 'from_id', 'to', 'to_id',
                'dialog', 'dialog_type',
                'content', 'media', 'extra')

    def dict_to_string(dict_in):
        # pylint: disable=E0213,E1101
        return ' '.join("{}:{}".format(k, v) for (k, v) in dict_in.items())

    def to_row_string(self, separator):
        # pylint: disable=W1308
        return '{}{}{}{}{}{}{}{}{}{}{}{}{}{}{}{}{}{}{}{}{}{}{}{}{}'.format(
            self._timestamp, separator,
            self._source, separator,
            self._id, separator,
            self._type, separator,
            self._from_who, separator,
            self._from_id, separator,
            self._to_who, separator,
            self._to_id, separator,
            self._dialog, separator,
            self._dialog_type, separator,
            escape_csv_string(self._content), separator,
            self._media, separator,
            escape_csv_string(TRow.dict_to_string(self._extra)))

    @property
    def timestamp(self):
        return self.model.timestamp

    @timestamp.setter
    def timestamp(self, value):
        self.model.timestamp = value

    @property
    def source(self):
        return self.model.source

    @source.setter
    def source(self, value):
        self.model.source = value

    @property
    def id(self):
        return self.model.id

    @id.setter
    def id(self, value):
        self.model.id = value

    @property
    def type(self):
        return self.model.type

    @type.setter
    def type(self, value):
        self.model.type = value

    @property
    def from_who(self):
        return self.model.from_who

    @from_who.setter
    def from_who(self, value):
        self.model.from_who = value

    @property
    def from_id(self):
        return self.model.from_id

    @from_id.setter
    def from_id(self, value):
        self.model.from_id = value

    @property
    def to_who(self):
        return self.model.to_who

    @to_who.setter
    def to_who(self, value):
        self.model.to_who = value

    @property
    def to_id(self):
        return self.model.to_id

    @to_id.setter
    def to_id(self, value):
        self.model.to_id = value

    @property
    def dialog(self):
        return self.model.dialog

    @dialog.setter
    def dialog(self, value):
        self.model.dialog = value

    @property
    def dialog_type(self):
        return self.model.dialog_type

    @dialog_type.setter
    def dialog_type(self, value):
        self.model.dialog_type = value

    @property
    def content(self):
        return self.model.content

    @content.setter
    def content(self, value):
        self.model.content = value

    @property
    def media(self):
        return self.model.media

    @media.setter
    def media(self, value):
        self.model.media = value

    @property
    def extra(self):
        return self.model.extra

    @extra.setter
    def extra(self, value):
        pass

# ------------------------------------------------------------------------------


class TChat(TUIDModel):

    @property
    def name(self):
        return self.model.name

    @property
    def dict_id(self):
        dictid = {}
        dictid['title'] = search_attribute(self.blob, 'title.string')
        has_username = search_attribute(self.blob, 'flags.has_username')
        if has_username:
            dictid['username'] = search_attribute(self.blob, 'username.string')
        return dictid

    @property
    def chat_type(self):
        ct = ''
        if not hasattr(self.blob, 'flags'):
            return ct
        left = search_attribute(self.blob, 'flags.left')
        has_username = search_attribute(self.blob, 'flags.has_username')
        broadcast = search_attribute(self.blob, 'flags.broadcast')
        megagroup = search_attribute(self.blob, 'flags.megagroup')
        if broadcast:
            assert not megagroup
            ct = '1-N'
        elif megagroup:
            assert not broadcast
            ct = 'N-N'
        else:
            ct = '?-?'
        if has_username:
            ct += ' pub'
        else:
            ct += ' prv'
        if left:
            ct += ' left'
        return ct

    @property
    def shortest_id(self):
        sid = ''
        has_username = search_attribute(self.blob, 'flags.has_username')
        if has_username:
            if self.blob.username.string:
                sid = '{}'.format(self.blob.username.string)
        elif self.blob.title.string:
            sid = '{}'.format(self.blob.title.string)
        else:
            sid = self.uid
        return sid

    @property
    def creation_date(self):
        return search_attribute(self.blob, 'date.epoch')

    @property
    def photo_info(self):
        ph_info = ''
        blob = self.blob
        photo = getattr(blob, 'photo', None)
        if photo:
            ph_blob = blob.photo.photo
            ph_info = '{}'.format(ph_blob.sname)
            ps_blob = getattr(ph_blob, 'photo_small', None)
            if ps_blob:
                ps_blob = ph_blob.photo_small.photo_small
                psf = '{}_{}.jpg'.format(ps_blob.volume_id, ps_blob.local_id)
                ph_info += ' small: {}'.format(psf)
            pb_blob = getattr(ph_blob, 'photo_big', None)
            if pb_blob:
                pb_blob = ph_blob.photo_big.photo_big
                pbf = '{}_{}.jpg'.format(pb_blob.volume_id, pb_blob.local_id)
                ph_info += ' big: {}'.format(pbf)
        return ph_info

# ------------------------------------------------------------------------------


class TDialog(TBase):

    @property
    def did(self):
        return self.model.did

    @property
    def date(self):
        return self.model.date

    @property
    def unread_count(self):
        return self.model.unread_count

    @property
    def last_mid(self):
        return self.model.last_mid

    @property
    def inbox_max(self):
        return self.model.inbox_max

    @property
    def outbox_max(self):
        return self.model.outbox_max

    @property
    def last_mid_i(self):
        return self.model.last_mid_i

    @property
    def unread_count_i(self):
        return self.model.unread_count_i

    @property
    def pts(self):
        return self.model.pts

    @property
    def date_i(self):
        return self.model.date_i

    @property
    def pinned(self):
        return self.model.pinned

    @property
    def flags(self):
        return self.model.flags

# ------------------------------------------------------------------------------


class TEchat(TUIDModel):

    @property
    def user(self):
        return self.model.user

    @property
    def name(self):
        return self.model.name

    @property
    def g(self):
        return self.model.g

    @property
    def authkey(self):
        return self.model.authkey

    @property
    def ttl(self):
        return self.model.ttl

    @property
    def layer(self):
        return self.model.layer

    @property
    def seq_in(self):
        return self.model.seq_in

    @property
    def seq_out(self):
        return self.model.seq_out

    @property
    def use_count(self):
        return self.model.use_count

    @property
    def exchange_id(self):
        return self.model.exchange_id

    @property
    def key_date(self):
        return self.model.key_date

    @property
    def fprint(self):
        return self.model.fprint

    @property
    def fauthkey(self):
        return self.model.fauthkey

    @property
    def khash(self):
        return self.model.khash

    @property
    def in_seq_no(self):
        return self.model.in_seq_no

    @property
    def admin_id(self):
        return self.model.admin_id

    @property
    def mtproto_seq(self):
        return self.model.mtproto_seq

    @property
    def dict_id(self):
        dictid = {'name': self.name, 'ttl': self.ttl,
                  'seq_in': self.seq_in, 'seq_out': self.seq_out}
        return dictid

    @property
    def shortest_id(self):
        if self.name:
            return self.name
        return self.uid

    @property
    def creation_date(self):
        date = getattr(self.blob, 'date', None)
        if date:
            epoch = getattr(date, 'epoch', None)
            return epoch
        return None

    @property
    def participant_id(self):
        # Normally the db user entry is equal to blob participant_id, but there
        # are cases where user=admin_id=admin_id_blob
        participant_id = getattr(self.blob, 'participant_id', None)
        if participant_id:
            return int(participant_id)
        if self.admin_id != self.user:
            return int(self.user)
        logger.warning('encrypted chat %s has not a valid participant_id!',
                       self.uid)
        return None


# ------------------------------------------------------------------------------

class TMedia(TBase):

    @property
    def blob(self):
        return self.model.blob

    @property
    def mid(self):
        return self.model.mid

    @property
    def uid(self):
        return self.model.uid

    @property
    def date(self):
        return self.model.date

    @property
    def type(self):
        return self.model.type

# ------------------------------------------------------------------------------


class TMessage(TBase):

    @property
    def blob(self):
        return self.model.blob

    @blob.setter
    def blob(self, value):
        self.model.blob = value

    @property
    def blob_reply(self):
        return self.model.replydata_blob

    @blob_reply.setter
    def blob_reply(self, value):
        self.model.replydata_blob = value

    @property
    def mid(self):
        return self.model.mid

    @property
    def uid(self):
        return self.model.uid

    @property
    def read_state(self):
        return self.model.read_state

    @property
    def send_state(self):
        return self.model.send_state

    @property
    def date(self):
        return self.model.date

    @property
    def out(self):
        return self.model.out

    @property
    def ttl(self):
        return self.model.ttl

    @property
    def media(self):
        return self.model.media

    @property
    def imp(self):
        return self.model.imp

    @property
    def mention(self):
        return self.model.mention

    @property
    def to_id_and_type(self):
        to_id_c = self.blob.to_id.to_id
        if to_id_c.sname == 'peer_channel':
            return (to_id_c.channel_id, TYPE_MSG_TO_CHANNEL)
        if to_id_c.sname == 'peer_user':
            return (to_id_c.user_id, TYPE_MSG_TO_USER)
        return (None, None)

    @property
    def message_content(self):
        msg = getattr(self.blob, 'message', None)
        if msg:
            return escape_csv_string(msg.string)
        return ''

    @property
    def message_date_from_blob(self):
        if hasattr(self.blob, 'date'):
            return getattr(self.blob.date, 'epoch', None)
        return None

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
        action = getattr(self.blob, 'action', None)
        if action:
            action_copy = action.action
            del action_copy['_io']
            del action_copy['signature']
            return action_copy.sname, action_copy
        return None, None

# ------------------------------------------------------------------------------


class TSentFile(TBase):

    @property
    def blob(self):
        return self.model.blob

    @property
    def uid(self):
        return self.model.uid

    @property
    def ttype(self):
        return self.model.type

    @property
    def parent(self):
        return self.model.parent

# ------------------------------------------------------------------------------


class TUserSettings(TBase):

    @property
    def uid(self):
        return self.model.uid

    @property
    def blob(self):
        return self.model.info_blob

    @property
    def pinned(self):
        return self.model.pinned

# ------------------------------------------------------------------------------


class TUser(TBase):

    def __init__(self, model):
        super().__init__(model)
        assert self.uid == self.blob.id

    @property
    def uid(self):
        return self.model.uid

    @property
    def name(self):
        return self.model.name

    @property
    def status(self):
        return self.model.status

    @property
    def blob(self):
        return self.model.blob

    # The following are useful fiels extracted from the blob.

    @property
    def first_name(self):
        if self.model.blob.flags.has_first_name:
            return self.model.blob.first_name.string
        return ''

    @property
    def last_name(self):
        if self.model.blob.flags.has_last_name:
            return self.model.blob.last_name.string
        return ''

    @property
    def username(self):
        if self.model.blob.flags.has_username:
            return self.model.blob.username.string
        return ''

    @property
    def phone(self):
        if self.model.blob.flags.has_phone:
            return self.model.blob.phone.string
        return ''

    @property
    def full_text_id(self):
        return 'uid: {} nick: {} fullname: {} {} phone: {}'.format(
            self.uid, self.username, self.first_name, self.last_name,
            self.phone)

    @property
    def dict_id(self):
        dictid = {}
        if self.username:
            dictid['username'] = self.username
        if self.first_name:
            dictid['firstname'] = self.first_name
        if self.last_name:
            dictid['lastname'] = self.last_name
        if self.phone:
            dictid['phone'] = self.phone
        return dictid

    @property
    def shortest_id(self):
        if self.username:
            sis = '{}'.format(self.username)
        elif self.first_name or self.last_name:
            if self.first_name and self.last_name:
                sis = '{} {}'.format(self.first_name, self.last_name)
            elif self.first_name:
                sis = '{}'.format(self.first_name)
            else:
                sis = '{}'.format(self.last_name)
        else:
            sis = self.uid

        if self.is_self:
            return '{} (owner)'.format(sis)
        return sis

    @property
    def photo_info(self):
        ph_info = ''
        blob = self.model.blob
        photo = getattr(blob, 'photo', None)
        if photo:
            ph_blob = blob.photo.photo
            ph_info = '{}'.format(ph_blob.sname)
            ps_blob = getattr(ph_blob, 'photo_small', None)
            if ps_blob:
                ps_blob = ph_blob.photo_small.photo_small
                psf = '{}_{}.jpg'.format(ps_blob.volume_id, ps_blob.local_id)
                ph_info += ' small: {}'.format(psf)
            pb_blob = getattr(ph_blob, 'photo_big', None)
            if pb_blob:
                pb_blob = ph_blob.photo_big.photo_big
                pbf = '{}_{}.jpg'.format(pb_blob.volume_id, pb_blob.local_id)
                ph_info += ' big: {}'.format(pbf)
        return ph_info

    @property
    def is_self(self):
        flags = getattr(self.blob, 'flags', None)
        if flags:
            user_self = getattr(flags, 'is_self', None)
            if user_self:
                return flags.is_self
        return False

# ------------------------------------------------------------------------------
