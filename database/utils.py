# -*- coding: utf-8 -*-
"""
Created on Wed Sep  7 08:55:54 2022

@author: 皓
"""
import re
from sqlalchemy.orm import mapper, registry
from sqlalchemy import Table, MetaData


def sub_snake(match):
    ret = [x for x in match.groups() if x]
    return '{}_{}'.format(ret[0], ret[1])


SNAKE = re.compile(
    '([A-Z])([A-Z](?=[a-z]))|([a-z])([A-Z](?=[A-Z]))|([a-z])([A-Z](?=[a-z]))')


def name_convert_to_snake(name: str) -> str:
    """驼峰转下划线"""
    if '_' not in name:
        name = SNAKE.sub(sub_snake, name)
    else:
        raise ValueError(f'{name}字符中包含下划线，无法转换')
    return name.lower()


def name_convert_to_camel(name: str) -> str:
    """下划线转驼峰(小驼峰)"""
    ret = re.sub(r'_([a-z])', lambda x: x.group(1).upper(), name)
    return f'{ret[0].lower()}{ret[1:]}'


def name_convert_to_pascal(name: str) -> str:
    """下划线转驼峰(大驼峰)"""
    ret = re.sub(r'_([a-z])', lambda x: x.group(1).upper(), name)
    return f'{ret[0].upper()}{ret[1:]}'


metadata = MetaData()
registry_ = registry()


def gen_model(class_name, table_name, *columns, parents=None, attrs=None):
    parent_classes = []
    if parents:
        parent_classes.extend(parents)
    attributes = dict(metadata=metadata,
                      registry=registry_)
    if attrs:
        attributes.update(dict(attrs))
    metaclass = type(class_name, tuple(parent_classes), attributes)
    table = Table(table_name, metadata, *columns)
    mapper(metaclass, table)
    return metaclass
