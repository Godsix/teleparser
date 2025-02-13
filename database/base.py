# -*- coding: utf-8 -*-
"""
Created on Thu Dec  1 15:44:55 2022

@author: 皓
"""
import os.path as osp
from functools import lru_cache
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy import Column
from .lazy import lazy_property, lazy_clear
from .utils import name_convert_to_pascal, gen_model


def get_column_param(**kwargs):
    if "type" in kwargs:
        kwargs['type_'] = kwargs.pop("type")
    return kwargs


class BaseDB:
    def __init__(self, path):
        self.path = path

    @property
    def path(self):
        return self._path

    @path.setter
    def path(self, value):
        assert osp.isfile(value), f'No such file: {value}'
        realpath = osp.realpath(value)
        self.db_uri = f'sqlite:///{realpath}'
        self.engine = create_engine(self.db_uri)
        self.session = scoped_session(sessionmaker(bind=self.engine))

    @property
    def engine(self):
        return self._engine

    @engine.setter
    @lazy_clear
    def engine(self, value):
        self._engine = value
        if hasattr(self, 'get_model'):
            self.__get_model.cache_clear()

    @lazy_property
    def inspect(self):
        return inspect(self.engine)

    @property
    def user_version(self):
        return self.execute('PRAGMA user_version').fetchall()[0][0]

    def execute(self, statement, *args, **kwargs):
        if isinstance(statement, str):
            statement = text(statement)
        return self.session.execute(statement)

    def tables(self):
        return self.inspect.get_table_names()

    def table_count(self, name):
        return self.execute(f'SELECT COUNT(*) FROM {name}').scalars().first()

    @lru_cache()
    def __get_model(self, table_name, parents=None, attrs=None):
        if not self.inspect.has_table(table_name):
            return None
        class_name = name_convert_to_pascal(table_name)
        columns = self.inspect.get_columns(table_name)
        columns_list = [Column(**get_column_param(**x)) for x in columns]
        if all(x['primary_key'] == 0 for x in columns):
            columns_list[0].primary_key = True
        return gen_model(class_name, table_name, *columns_list,
                         parents=parents, attrs=attrs)

    def get_model(self, table_name, parents=None, attrs=None):
        parents = tuple(parents) if parents else None
        attrs = tuple(attrs.items()) if attrs else None
        return self.__get_model(table_name, parents=parents, attrs=attrs)
