# -*- coding: utf-8 -*-
"""
Created on Wed Sep  7 08:55:54 2022

@author: C. David
"""
import os.path as osp
import re
import json
import getpass
import importlib
from glob import iglob
from datetime import datetime
from inspect import getsource
from functools import partial, cmp_to_key
from types import MethodType, FunctionType
from zipfile import ZipFile, ZIP_DEFLATED
import autopep8
from .common import (STRUCT_TEMPLATE, MODEL_TEMPLATE, STRUCTURES_TEMPLATE,
                     SIMPLE_STRUCT_TEMPLATE, TODO_STRUCT_TEMPLATE)

try:
    import yaml
    try:
        from yaml import CLoader as Loader, CDumper as Dumper
    except ImportError:
        from yaml import Loader, Dumper
except ModuleNotFoundError:
    yaml = None


def load_data(path):
    _, ext = osp.splitext(path)
    if ext in {'.yaml', '.yml'}:
        if yaml is None:
            raise ModuleNotFoundError("No module named 'yaml'")
        loader = partial(yaml.load, Loader=Loader)
    elif ext in {'.json'}:
        loader = partial(json.load)
    else:
        raise TypeError(f'File extention must be YAML or JSON,but {ext}.')
    with open(path, 'rb') as f:
        return loader(f)


def dump_data(data, path):
    _, ext = osp.splitext(path)
    if ext in {'.yaml', '.yml'}:
        if yaml is None:
            raise ModuleNotFoundError("No module named 'yaml'")
        dumper = partial(yaml.dump, Dumper=Dumper)
    elif ext in {'.json'}:
        dumper = partial(json.dump, ensure_ascii=False)
    else:
        raise TypeError(f'File extention must be YAML or JSON,but {ext}.')
    with open(path, 'w+', encoding='utf-8') as f:
        return dumper(data, f)


def save_code(path, content, pep8=False, options=None, encoding=None,
              apply_config=False, **kwargs):
    if pep8:
        content = autopep8.fix_code(content,
                                    options,
                                    encoding,
                                    apply_config)
    else:
        content = content
    with open(path, 'w+', encoding='utf-8', newline='\n') as f:
        f.write(content)


def get_struct_content(data):
    if isinstance(data, (str, bytes)) and osp.isfile(data):
        data = load_data(data)
    return STRUCT_TEMPLATE.render(data)


def get_simple_struct_content(data):
    if isinstance(data, (str, bytes)) and osp.isfile(data):
        data = load_data(data)
    return SIMPLE_STRUCT_TEMPLATE.render(data)


def get_todo_struct_content(data):
    if isinstance(data, (str, bytes)) and osp.isfile(data):
        data = load_data(data)
    return TODO_STRUCT_TEMPLATE.render(data)


def generate_struct_code(path, data, **kwargs):
    data.setdefault('localtime', datetime.now().strftime('%c'))
    data.setdefault('username', getpass.getuser())
    content = get_struct_content(data)
    save_code(path, content, **kwargs)


def get_structures_content(data):
    if isinstance(data, (str, bytes)) and osp.isfile(data):
        data = load_data(data)
    return STRUCTURES_TEMPLATE.render(data)


def generate_structures_code(path, data, **kwargs):
    data.setdefault('localtime', datetime.now().strftime('%c'))
    data.setdefault('username', getpass.getuser())
    content = get_structures_content(data)
    save_code(path, content, **kwargs)


def get_model_content(data):
    if isinstance(data, (str, bytes)) and osp.isfile(data):
        data = load_data(data)
    return MODEL_TEMPLATE.render(data)


def generate_model_code(path, data, **kwargs):
    data.setdefault('localtime', datetime.now().strftime('%c'))
    data.setdefault('username', getpass.getuser())
    content = get_model_content(data)
    save_code(path, content, **kwargs)

# ---------------------------- Common end ---------------------------------


def get_lineno(method_or_func):
    code = None
    # get decorator wrapped content
    if hasattr(method_or_func, '__wrapped__'):
        method_or_func = method_or_func.__wrapped__
    if hasattr(method_or_func, '__code__'):
        code = method_or_func.__code__
    else:
        if hasattr(method_or_func, '__func__'):
            func = method_or_func.__func__
            if hasattr(func, '__code__'):
                code = func.__code__
    return code.co_firstlineno


def cmp(x, y):
    if x > y:
        return -1
    if x < y:
        return 1
    return 0


def compare_object_lineno(obj):
    def wrapper(left, right):
        return cmp(get_lineno(getattr(obj, left)),
                   get_lineno(getattr(obj, right)))
    return wrapper


def cmp_func():
    def wrapper(left, right):
        return cmp(get_lineno(left), get_lineno(right))
    return cmp_to_key(wrapper)


def get_pattern(pattern, flags=0):
    if isinstance(pattern, (bytes, str)):
        return re.compile(pattern, flags)
    if isinstance(pattern, re.Pattern):
        return pattern


def find_content_from_func(func, pattern, index=0):
    source_code = getsource(func)
    pattern = get_pattern(pattern)
    m = pattern.search(source_code)
    if m:
        return m.group(index)
    return None


def is_method_function(obj):
    return isinstance(obj, (MethodType, FunctionType))


def is_builtin_module(module):
    if module.startswith('.'):
        builtin_flag = False
    else:
        try:
            mod = importlib.import_module(module)
            if hasattr(mod, __file__):
                pass
            path = mod.__file__
            builtin_flag = ('site-packages' not in path)
        except ModuleNotFoundError:
            builtin_flag = False
        except AttributeError:
            builtin_flag = False
    return builtin_flag


def get_class_functions(class_):
    dir_list = (x for x in dir(class_) if not x.startswith('_'))
    attr_list = list(getattr(class_, x) for x in dir_list)
    func_list = [x for x in attr_list if is_method_function(x)]
    functions = list(sorted(func_list, key=cmp_func(), reverse=True))
    print(len(functions))
    return functions


def zip_file(file_path, zip_path, mode='a', filename=None):
    realpath = osp.realpath(file_path)
    if not filename:
        filename = osp.basename(file_path)
    with ZipFile(zip_path, mode, compression=ZIP_DEFLATED) as zip_file:
        zip_file.write(realpath, filename)


DX_REGEXS = [re.compile(r'/\*!<(.+)\*/'),
             re.compile(r'/\*!(.+)\*/'),
             re.compile(r'/\*(.+)\*/'),
             re.compile('//(.+)')]


def regexp_match(text, *patterns, index=0):
    for pattern in (get_pattern(x) for x in patterns):
        m = pattern.match(text)
        if m:
            return m.group(index)
    return None


def regexp_findall(text, *patterns, limit=None):
    assert isinstance(limit, (int, type(None)))
    start_p = 0
    result = []
    text_len = len(text)
    patterns = tuple(get_pattern(x) for x in patterns)
    while True:
        i_matches = (x.search(text, start_p) for x in patterns)
        matches = [x for x in i_matches if x]
        if not matches:
            break
        min_start_point = text_len
        min_start = None
        for match in matches:
            match_start = match.start()
            if ((match_start < min_start_point) or
                ((match_start == min_start_point) and
                 (min_start.end() == text_len))):
                min_start_point = match_start
                min_start = match
        item = min_start.groups()
        if limit is not None:
            item_value = (item + (None, ) * (limit - len(item)))[:limit]
        else:
            item_value = item
        result.append(item_value)
        start_p = min_start.end()
    return result


def process_doxygen(c_in):
    if c_in is None:
        return ''
    s = c_in.strip()
    if not s:
        return s
    result = regexp_match(s, *DX_REGEXS, index=1)
    if result is None:
        return s
    return result.strip()


def find_import(mod_path, *patterns, index=1):
    result = []
    for path in iglob(osp.join(mod_path, '*.py')):
        with open(path, encoding='utf-8') as f:
            obj_tuple = regexp_findall(f.read(), patterns)
            if not obj_tuple:
                continue
            objects = [x[index-1] for x in obj_tuple]
            name = osp.splitext(osp.basename(path))[0]
            result.append(f'from .{name} import {", ".join(objects)}')
    return '\n'.join(result)
