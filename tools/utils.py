# -*- coding: utf-8 -*-
"""
Created on Wed Sep  7 08:55:54 2022

@author: C. David
"""
import re
import time
from functools import wraps, lru_cache


def sub_snake(match):
    m, n, *_ = [x for x in match.groups() if x]
    return f'{m}_{n}'


SNAKE = re.compile('([A-Z])([A-Z](?=[a-z]))|'
                   '([a-z])([A-Z](?=[A-Z]))|'
                   '([a-z])([A-Z](?=[a-z]))')


# def name_convert_to_snake(name: str) -> str:
#     '''
#     Convert camel case names into snake case, like:
#     >>> name_convert_to_snake("CamelCase")
#     'camel_case'
#     '''
#     if '_' not in name:
#         name = SNAKE.sub(sub_snake, name)
#     else:
#         raise ValueError(f'{name} contains underscore')
#     return name.lower()


@lru_cache(maxsize=1024)
def name_convert_to_snake(name: str) -> str:
    '''
    Convert camel case names into snake case, like:
    >>> name_convert_to_snake("CamelCase")
    'camel_case'
    '''
    if any(x.isupper() for x in name):
        name = SNAKE.sub(sub_snake, name)
        return name.lower()
    else:
        return name


def name_convert_to_camel(name: str) -> str:
    '''
    Convert snake case names into camel case(Lower Camel Case), like:
    >>> name_convert_to_camel("camel_case")
    'camelCase'
    '''
    ret = re.sub(r'_([a-z])', lambda x: x.group(1).upper(), name)
    return f'{ret[0].lower()}{ret[1:]}'


def name_convert_to_pascal(name: str) -> str:
    '''
    Convert snake case names into pascal case(Upper Camel Case), like:
    >>> name_convert_to_pascal("camel_case")
    'CamelCase'
    '''
    ret = re.sub(r'_([a-z])', lambda x: x.group(1).upper(), name)
    return f'{ret[0].upper()}{ret[1:]}'


def print_run_time(obj='{name} spend time: {time:.3f} s.', logger=print):
    '''Print the run time of function'''
    if isinstance(obj, str):
        fmt = obj
    elif callable(obj):
        fmt = '{name} spend time: {time:.3f} s.'
    else:
        raise TypeError('Expected argument1 to be a str or function.')

    def decorator(func):
        name = getattr(func, '__name__', repr(func))
        param = {'name': name}

        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            ret = func(*args, **kwargs)
            end = time.time()
            _ = param.setdefault('time', end - start)
            logger(fmt.format_map(param))
            return ret
        return wrapper

    if isinstance(obj, str):
        return decorator
    else:
        return decorator(obj)


INVALID_CHAR = re.compile(r'[<>:"/\\\|\?\*]')
RESERVE_NAME = {'CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'LPT1', 'LPT2'}


def sanitize_filename(filename):
    if filename.upper() in RESERVE_NAME:
        # check if the filename is a reserved name
        filename = f"{filename}_file"
    else:
        # replace invalid characters with underscores
        filename = INVALID_CHAR.sub('_', filename)
    return filename
