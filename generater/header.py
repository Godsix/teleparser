# -*- coding: utf-8 -*-
"""
Created on Fri Dec  9 09:12:01 2022

@author: 皓
"""
# pylint: disable=protected-access,too-many-lines,too-many-public-methods
from functools import wraps, lru_cache
from construct import (Struct, Computed, Int32ul, Int64ul, Double, Hex,
                       FlagsEnum, GreedyBytes, Array, IfThenElse, If, Peek,
                       Const, LazyBound, Switch, this,
                       setGlobalPrintFullStrings, setGlobalPrintPrivateEntries)
import logger
from .common import TString, TBytes, TBool, TTimestamp
# -----------------------------------------------------------------------------


INFO = {}

STRUCT_CACHE = {}


def constructor(cid, name, use_lru=False):
    INFO[cid] = name

    if not use_lru:  # pylint: disable=R1705
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                if cid in STRUCT_CACHE:
                    ret = STRUCT_CACHE[cid]
                else:
                    result = func(*args, **kwargs)
                    if isinstance(result, (list, tuple)):
                        ret = Struct('sname' / Computed(name),
                                     'signature' / Hex(Const(cid, Int32ul)),
                                     *result)
                    elif isinstance(result, dict):
                        ret = Struct('sname' / Computed(name),
                                     'signature' / Hex(Const(cid, Int32ul)),
                                     **result)
                    else:
                        ret = result
                    STRUCT_CACHE[cid] = ret
                return ret
            return wrapper
        return decorator
    else:
        return lru_cache()


structures = lru_cache()

# -----------------------------------------------------------------------------


class TLStruct:  # pylint: disable=C0103
    LAYER = 176

    def __init__(self):
        setGlobalPrintFullStrings(True)
        setGlobalPrintPrivateEntries(False)

    def parse_blob(self, data):
        pblob = None
        signature = int.from_bytes(data[:4], 'little')
        struct_name = f'struct_0x{signature:08x}'
        if hasattr(self, struct_name):
            blob_parser = getattr(self, struct_name)
            name = INFO.get(signature)
            if blob_parser:
                pblob = blob_parser().parse(data)
                data_len = len(data)
                object_len = pblob._io.tell()
                if data_len != object_len:
                    logger.error('Not all data parsed for object: %s [0x%x], '
                                 'input: %d, parsed: %d, missed: %s',
                                 name, signature, data_len, object_len,
                                 data[object_len:])
                    # raise ValueError('Not all data parsed for object')
        else:
            try:
                pblob_parser = self.struct_list()
                pblob = pblob_parser.parse(data)
            except Exception:
                print(f'unknown signature: 0x{signature:08x}')
                # raise ValueError('unknown signature')
        return pblob

    # ---------------------------- Common start -------------------------------

    @constructor(0x1cb5c415, 'vector', use_lru=True)
    def vector(self, datatype, name: str):
        return Struct(
            'sname' / Computed('vector'),
            'signature' / Hex(Const(0x1cb5c415, Int32ul)),
            'count' / Int32ul,
            'content' / Array(this.count, datatype))

    @structures
    def struct_list(self):
        # pylint: disable=C0301
        tag_map = {
            0xc077ec01: LazyBound(self.struct_0xc077ec01),
            0x40d13c0e: LazyBound(self.struct_0x40d13c0e),
            0xfb197a65: LazyBound(self.struct_0xfb197a65),
            0x2b085862: LazyBound(self.struct_0x2b085862),
        }
        return Struct(
            'sname' / Computed('list'),
            'count' / Int32ul,
            'content' / Array(this.count, Struct(
                                                '_signature' / Peek(Int32ul),
                                                'item' / Switch(this._signature, tag_map))))

    # ---------------------------- Common end ---------------------------------
