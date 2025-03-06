# -*- coding: utf-8 -*-
"""
Created on Wed Sep  7 08:42:28 2022

@author: C. David
"""
from database import BaseDB
from tools.utils import name_convert_to_pascal
try:
    from .utils import is_builtin_module, get_model_content
except ImportError:
    from generater.utils import is_builtin_module, get_model_content


class SQLiteDataBase(BaseDB):
    def __init__(self, path):
        super().__init__(path)
        self.data = {}
        self.import_info = self.data.setdefault('import', {})

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


def test(path):
    import os.path as osp
    helper = SQLiteDataBase(osp.join(path, 'cache4.db'))
    with open('models-1.py', mode='w+', encoding='utf-8') as f:
        f.write(helper.generate(parent=['BaseModel']))


def main():
    path = r'E:\Project\Godsix\teleparser\version_2'
    test(path)


# ------------------------------------------------------------------------------
if __name__ == '__main__':
    main()