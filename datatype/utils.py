# -*- coding: utf-8 -*-
"""
Created on Thu Dec 15 14:22:33 2022

@author: 皓
"""


def search_attribute(obj, keys):
    if not obj:
        return None
    key, left = keys.split('.', maxsplit=1)
    if isinstance(obj, dict):
        if hasattr(obj, key):
            node = getattr(obj, key)
        else:
            return None
        if left:
            return search_attribute(node, left)
        else:
            return node
    elif isinstance(obj, list):
        for item in obj:
            if hasattr(item, key):
                node = getattr(item, key)
                if left:
                    ret = search_attribute(node, left)
                    if ret is not None:
                        return ret
                else:
                    return node
        else:
            return None
