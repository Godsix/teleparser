# -*- coding: utf-8 -*-
"""
Created on Wed Dec  7 14:37:16 2022

@author: 皓
"""
import os.path as osp
import datetime
import getpass
from .utils import load_data, save_code
from .common import STRUCT_TEMPLATE, MODEL_TEMPLATE, STRUCTURES_TEMPLATE


def get_struct_content(data):
    if isinstance(data, (str, bytes)) and osp.isfile(data):
        data = load_data(data)
    return STRUCT_TEMPLATE.render(data)


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
