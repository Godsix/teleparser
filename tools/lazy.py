# -*- coding: utf-8 -*-
"""
Created on Fri Dec  2 15:26:34 2022

@author: C. David
"""
from functools import wraps


def lazy_property(func):
    attr_name = f"_lazy_{func.__name__}"

    @property
    def _lazy_property(self):
        if not hasattr(self, attr_name):
            if (ret := func(self)) is None:
                return ret
            setattr(self, attr_name, ret)
        return getattr(self, attr_name)

    @_lazy_property.setter
    def _lazy_property(self, value):
        setattr(self, attr_name, value)

    @_lazy_property.deleter
    def _lazy_property(self):
        delattr(self, attr_name)

    return _lazy_property


def del_lazy_attr(obj, *attrs):
    if attrs:
        attr_iter = (y for x in attrs if hasattr(obj, y := f"_lazy_{x}"))
    else:
        attr_iter = (x for x in dir(obj) if x.startswith("_lazy_"))
    for item in attr_iter:
        delattr(obj, item)


def lazy_clear(*params):
    if len(params) == 1 and callable(func := params[0]):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            del_lazy_attr(self)
            return func(self, *args, **kwargs)
        return wrapper
    if all(isinstance(x, str) for x in params):
        def decorator(func):
            @wraps(func)
            def wrapper(self, *args, **kwargs):
                del_lazy_attr(self, *params)
                return func(self, *args, **kwargs)
            return wrapper
        return decorator
    raise ValueError(f'Parameters error, args: {params}.')
