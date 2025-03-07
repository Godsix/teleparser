# -*- coding: utf-8 -*-
"""
Created on Thu Dec 15 14:22:33 2022

@author: C. David
"""
import json
from construct import Container, ListContainer


MIME_TYPE = {
    "video/mp4": ".mp4",
    "video/x-matroska": ".mkv",
    "audio/ogg": ".ogg"
}


def get_obj_value(obj, key, default=None):
    '''Get value from an object using dot notation'''
    if not obj:
        return None
    key_list = key.split('.')
    cur = obj
    for item in key_list:
        if cur and item in cur:
            cur = cur[item]
        else:
            return default
    return cur


def pythonic(obj, key=None):
    '''Convert a Construct object to Python data structure'''
    if isinstance(obj, Container):
        sname = obj.get('sname')
        if sname == 'vector':
            return pythonic(obj['content'], key)
        if sname in {'string', 'bytes', 'boolean'}:
            return obj['value']
        if sname == 'timestamp':
            return obj['epoch']
        if key in obj:
            return pythonic(obj[key])
        else:
            return {x: pythonic(obj[x], x) for x in obj if not x.startswith('_')}
    elif isinstance(obj, ListContainer):
        return [pythonic(x, key) for x in obj]
    else:
        return obj


def format_dict(obj: dict):
    '''Format dictionary as JSON string and indented output'''
    return json.dumps(obj, ensure_ascii=False, indent=4, default=str)
