# -*- coding: utf-8 -*-
"""
Created on Thu Dec  1 15:44:55 2022

@author: C. David
"""
import os.path as osp
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy import MetaData
from sqlalchemy.orm import registry
from tools.lazy import lazy_property, del_lazy_attr


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
        self._path = realpath
        self.db_uri = f'sqlite:///{realpath}'
        del_lazy_attr(self)
        self.session = scoped_session(sessionmaker(bind=self.engine))
        if (lru_names := getattr(self.__class__, 'LRU', None)):
            for name in lru_names:
                if lru_func := getattr(self, name, None):
                    lru_func.cache_clear()

    @lazy_property
    def engine(self):
        return create_engine(self.db_uri)

    @lazy_property
    def inspect(self):
        return inspect(self.engine)

    @lazy_property
    def metadata(self):
        return MetaData()

    @lazy_property
    def registry(self):
        return registry()

    @property
    def user_version(self):
        return self.execute('PRAGMA user_version').fetchall()[0][0]

    def execute(self, statement):
        '''Execute a SQLAlchemy SQL string'''
        if isinstance(statement, str):
            statement = text(statement)
        return self.session.execute(statement)

    def tables(self):
        return self.inspect.get_table_names()

    def table_count(self, name):
        return self.execute(f'SELECT COUNT(*) FROM {name}').scalars().first()
