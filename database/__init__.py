# -*- coding: utf-8 -*-
"""
Created on Thu Dec  1 15:43:28 2022

@author: 皓
"""
import re
from functools import lru_cache
from .base import BaseDB
from .models import (Chats, Dialogs, EncChats, MediaV4, MessagesV2,
                     SentFilesV2, Users, UserSettings, TModel,
                     get_data_blob, get_info_blob, get_replydata_blob)


class TelegramDB(BaseDB):

    @lru_cache()
    def get_table_model(self, name, blob=True):
        pattern = re.compile(rf'{name}(?:$|_v\d+)', re.M)
        for table in self.inspect.get_table_names():
            if pattern.fullmatch(table):
                table_name = table
                break  # pylint: disable=E501
        else:
            return None
        columns = self.inspect.get_columns(table_name)
        column_info = {x['name']: x for x in columns}
        attrs = {}
        if 'data' in column_info:
            attrs['blob'] = property(get_data_blob)
        if 'info' in column_info:
            attrs['info_blob'] = property(get_info_blob)
        if 'replydata' in column_info:
            attrs['replydata_blob'] = property(get_replydata_blob)
        # attrs = {'blob': property(get_data_blob)} if blob else None
        return self.get_model(table_name, parents=[TModel], attrs=attrs)

    def get_chats(self) -> list:
        model = self.get_table_model('chats')
        query = self.session.query(model)
        result = query.all()
        return result

    def get_contacts(self) -> list:
        model = self.get_table_model('contacts', False)
        query = self.session.query(model)
        result = query.all()
        return result

    def get_dialogs(self) -> list:
        model = self.get_table_model('dialogs')
        query = self.session.query(model)
        result = query.all()
        return result

    def get_enc_chats(self) -> list:
        model = self.get_table_model('enc_chats')
        query = self.session.query(model)
        result = query.all()
        return result

    def get_media(self) -> list:
        model = self.get_table_model('media')
        query = self.session.query(model)
        result = query.all()
        return result

    def get_messages(self) -> dict:
        model = self.get_table_model('messages')
        query = self.session.query(model)
        result = query.all()
        return result

    def get_sent_files(self) -> list:
        model = self.get_table_model('sent_files')
        query = self.session.query(model)
        result = query.all()
        return result

    def get_users(self) -> list:
        model = self.get_table_model('users')
        query = self.session.query(model)
        result = query.all()
        return result

    def get_user_settings(self) -> list:
        model = self.get_table_model('user_settings')
        query = self.session.query(model)
        result = query.all()
        return result
