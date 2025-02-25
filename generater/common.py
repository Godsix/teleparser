# -*- coding: utf-8 -*-
"""
Created on Wed Sep  7 08:45:08 2022

@author: 皓
"""
import os.path as osp
import builtins
from jinja2 import Environment, FileSystemLoader


DIR = osp.realpath(osp.dirname(__file__))
TEMPLATE_DIR = osp.join(DIR, 'templates')
ENV = Environment(loader=FileSystemLoader(TEMPLATE_DIR),
                  trim_blocks=True,
                  lstrip_blocks=True)
STRUCT_TEMPLATE = ENV.get_template('struct.tmpl')
SIMPLE_STRUCT_TEMPLATE = ENV.get_template('simple_struct.tmpl')
STRUCTURES_TEMPLATE = ENV.get_template('structures.tmpl')
MODEL_TEMPLATE = ENV.get_template('model.tmpl')
STRUCT_CACHE = osp.join(DIR, 'structs')
HEADER = osp.join(DIR, 'header.py')
BUILTIN_OBJECT = set(x for x in dir(builtins) if not x.startswith('_'))
