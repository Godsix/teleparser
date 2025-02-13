# -*- coding: utf-8 -*-
"""
Created on Wed Sep  7 08:42:28 2022

@author: 皓
"""
import os.path as osp
from sqlalchemy import create_engine, inspect
try:
    from sqlalchemy.orm import declarative_base, DeclarativeMeta
except ImportError:
    # SQLAlchemy <= 1.3
    from sqlalchemy.ext.declarative import declarative_base, DeclarativeMeta

from sqlalchemy.orm import sessionmaker, scoped_session
try:
    from .utils import is_builtin_module, name_convert_to_pascal
    from .tools import get_model_content
except ImportError:
    from generater.utils import is_builtin_module, name_convert_to_pascal
    from generater.tools import get_model_content




Model = declarative_base(name='Model', metaclass=DeclarativeMeta)


class SQLiteDataBase:
    def __init__(self, path):
        self.path = path
        self.data = {}

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
        self.inspect = inspect(self.engine)

    def import_object(self, module: str, *objects):
        if not module:
            return None
        self.import_info = self.data.setdefault('import', {})
        import_info = self.import_info
        bi_flag = is_builtin_module(module)
        if objects:
            if bi_flag:
                modules = import_info.setdefault('builtin_objects', {})
            else:
                modules = import_info.setdefault('custom_objects', {})
            object_list = modules.setdefault(module, [])
            objs = dict.fromkeys(
                object_list + [x for x in objects if x is not None])
            object_list.clear()
            object_list.extend(objs)
        else:
            if bi_flag:
                modules = import_info.setdefault('builtin_modules', {})
            else:
                modules = import_info.setdefault('custom_modules', {})
            modules[module] = None

    def generate(self, table=None, parent=None):
        self.data.clear()
        if table is None:
            table_names = self.inspect.get_table_names()
        else:
            table_set = set(self.inspect.get_table_names())
            table_names = [x for x in table if x in table_set]
        tables = self.data.setdefault('tables', [])
        for table_name in table_names:
            item = {}
            item['name'] = table_name
            item['class_name'] = name_convert_to_pascal(table_name)
            item['parents'] = parent
            item['columns'] = self.inspect.get_columns(table_name)
            if item['columns']:
                self.import_object('sqlalchemy', 'Column')
            for subitem in item['columns']:
                self.import_object('sqlalchemy', str(subitem.get('type')))
            tables.append(item)
        return get_model_content(self.data)
