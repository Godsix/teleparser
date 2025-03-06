"""
Created on Thu Dec  1 15:43:28 2022

@author: C. David
"""
import re
from functools import lru_cache
from sqlalchemy import Table, Column, BLOB
from tools.utils import name_convert_to_pascal
from .base import BaseDB
from .models import TModel, get_parser


def get_column_param(**kwargs):
    if "type" in kwargs:
        kwargs['type_'] = kwargs.pop("type")
    return kwargs


class TelegramDB(BaseDB):
    LRU = ('get_blob_columns', 'get_table_model')

    @lru_cache()
    def get_blob_columns(self, table_name: str):
        '''Get all blob columns from a given table'''
        columns = self.inspect.get_columns(table_name)
        result = {x['name']: x for x in columns if isinstance(x['type'], BLOB)}
        if 'unread' in result:
            del result['unread']
        return result

    @lru_cache()
    def get_table_model(self, name: str):
        '''Return the SQLAlchemy ORM class of a telegram database table'''
        pattern = re.compile(rf'{name}(?:$|_v\d+)', re.M)
        tables = self.tables()
        if not (table_name := next(filter(pattern.fullmatch, tables), None)):
            return None
        class_name = name_convert_to_pascal(table_name)
        bases = tuple([TModel])
        attrs = {}
        schemas = []
        columns = self.inspect.get_columns(table_name)
        for column in columns:
            name = column['name']
            schemas.append(Column(**get_column_param(**column)))
            if isinstance(column['type'], BLOB) and name != 'unread':
                attrs[f'{name}_blob'] = property(get_parser(name))
        if all(x['primary_key'] == 0 for x in columns):
            schemas[0].primary_key = True
        metaclass = type(class_name, bases, attrs)
        table = Table(table_name, self.metadata, *schemas)
        self.registry.map_imperatively(metaclass, table)
        return metaclass

    def get_table_data(self, name: str) -> list:
        '''Retrieve generic table data'''
        model = self.get_table_model(name)
        query = self.session.query(model)
        result = query.all()
        return result

    def get_chats(self) -> list:
        '''Retrieve chat data'''
        return self.get_table_data('chats')

    def get_contacts(self) -> list:
        '''Retrieve contact data'''
        return self.get_table_data('contacts')

    def get_dialogs(self) -> list:
        '''Retrieve dialog data'''
        return self.get_table_data('dialogs')

    def get_enc_chats(self) -> list:
        '''Retrieve encrypted chat data'''
        return self.get_table_data('enc_chats')

    def get_media(self) -> list:
        '''Retrieve media data'''
        return self.get_table_data('media')

    def get_messages(self) -> dict:
        '''Retrieve message data'''
        return self.get_table_data('messages')

    def get_sent_files(self) -> list:
        '''Retrieve sent file data'''
        return self.get_table_data('sent_files')

    def get_users(self) -> list:
        '''Retrieve user data'''
        return self.get_table_data('users')

    def get_user_settings(self) -> list:
        '''Retrieve user settings data'''
        return self.get_table_data('user_settings')
