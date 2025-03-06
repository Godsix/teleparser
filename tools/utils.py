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
#     """驼峰转下划线"""
#     if '_' not in name:
#         name = SNAKE.sub(sub_snake, name)
#     else:
#         raise ValueError(f'{name}字符中包含下划线，无法转换')
#     return name.lower()


@lru_cache(maxsize=1024)
def name_convert_to_snake(name: str) -> str:
    """驼峰转下划线"""
    if any(x.isupper() for x in name):
        name = SNAKE.sub(sub_snake, name)
        return name.lower()
    else:
        return name


def name_convert_to_camel(name: str) -> str:
    """下划线转驼峰(小驼峰)"""
    ret = re.sub(r'_([a-z])', lambda x: x.group(1).upper(), name)
    return f'{ret[0].lower()}{ret[1:]}'


def name_convert_to_pascal(name: str) -> str:
    """下划线转驼峰(大驼峰)"""
    ret = re.sub(r'_([a-z])', lambda x: x.group(1).upper(), name)
    return f'{ret[0].upper()}{ret[1:]}'


def print_run_time(fmt='{name} spend time: {time:.3f} s.', logger=print):
    if isinstance(fmt, str):
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
        return decorator
    elif callable(fmt):
        default_fmt = '{name} spend time: {time:.3f} s.'
        name = getattr(fmt, '__name__', repr(fmt))
        param = {'name': name}

        @wraps(fmt)
        def wrapper(*args, **kwargs):
            start = time.time()
            ret = fmt(*args, **kwargs)
            end = time.time()
            _ = param.setdefault('time', end - start)
            logger(default_fmt.format_map(param))
            return ret
        return wrapper
    raise TypeError(
        'Expected first argument to be an string, or a callable.')
