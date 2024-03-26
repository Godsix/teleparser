# -*- coding: utf-8 -*-
"""
Created on Fri Dec  2 15:26:34 2022

@author: 皓
"""
from functools import wraps


def lazy_property(func):
    attr_name = "_lazy_{}".format(func.__name__)

    @property
    def _lazy_property(self):
        if not hasattr(self, attr_name):
            ret = func(self)
            if ret is None:
                return ret
            setattr(self, attr_name, ret)
        return getattr(self, attr_name)

    return _lazy_property


def del_lazy_attr(obj):
    for item in tuple(x for x in dir(obj) if x.startswith('_lazy_')):
        delattr(obj, item)


def lazy_clear(*params):
    if not params:
        def decorator(func):

            @wraps(func)
            def wrapper(self, *args, **kwargs):
                ret = func(self, *args, **kwargs)
                del_lazy_attr(self)
                return ret
            return wrapper
        return decorator
    if len(params) == 1 and callable(params[0]):
        func = params[0]

        @wraps(func)
        def wrapper(self, *args, **kwargs):
            ret = func(self, *args, **kwargs)
            del_lazy_attr(self)
            return ret
        return wrapper
    if all(isinstance(x, str) for x in params):
        def decorator(func):

            @wraps(func)
            def wrapper(self, *args, **kwargs):
                ret = func(self, *args, **kwargs)
                for item in args:
                    lazy_name = "_lazy_{}".format(item)
                    if hasattr(self, lazy_name):
                        delattr(self, lazy_name)
                return ret
            return wrapper
        return decorator
    raise ValueError('Parameters error, args: {}.'.format(params))
