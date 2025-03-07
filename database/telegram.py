"""
Created on Thu Dec  1 15:43:28 2022

@author: C. David
"""
import re
from functools import lru_cache
from sqlalchemy import Table, Column, BLOB, inspect
from datatype import TLStruct
from tools.utils import name_convert_to_pascal
from .base import BaseDB


PARSER = TLStruct()


def get_column_param(**kwargs):
    if "type" in kwargs:
        kwargs['type_'] = kwargs.pop("type")
    return kwargs


def get_parser(name):
    def wrapper(self):
        if (data := getattr(self, name, None)) is None:
            return None
        return PARSER.parse_blob(data)
    return wrapper


class TModel:  # pylint: disable=R0903
    '''A base class to represent an Telegram Data object'''

    def __repr__(self) -> str:
        state = inspect(self)
        if state.transient:
            pk = f"(transient {id(self)})"
        elif state.pending:
            pk = f"(pending {id(self)})"
        else:
            pk = ", ".join(str(x) for x in state.identity)
        return f"<{type(self).__name__} {pk}>"


class TelegramDB(BaseDB):
    LRU = ('get_columns', 'get_blob_columns', 'get_table_model')
    UNPARSE = {'messages_v2': {'custom_params'},
               'params': {'pbytes'},
               'stickers_featured': {'unread'}}

    @lru_cache()
    def get_columns(self, table_name: str):
        '''Get all columns from a given table'''
        return self.inspect.get_columns(table_name)

    @lru_cache()
    def get_blob_columns(self, table_name: str):
        '''Get all blob columns from a given table'''
        columns = self.get_columns(table_name)
        result = {x['name']: x for x in columns if isinstance(x['type'], BLOB)}
        if (unparse := self.UNPARSE.get(table_name)):
            for key in unparse:
                del result[key]
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
        blob_columns = self.get_blob_columns(table_name)
        attrs = {f'{x}_blob': property(get_parser(x)) for x in blob_columns}
        columns = self.get_columns(table_name)
        schemas = [Column(**get_column_param(**x)) for x in columns]
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
