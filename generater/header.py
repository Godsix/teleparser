# -*- coding: utf-8 -*-
"""
Created on Fri Dec  9 09:12:01 2022

@author: C. David
"""
# pylint: disable=protected-access,too-many-lines,too-many-public-methods,line-too-long
from functools import wraps, lru_cache
from construct import (Struct, Computed, Int32ul, Int64ul, Double, Hex,
                       FlagsEnum, Array, If, Peek,
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

def raise_exception(text, *args):
    string = text % args
    raise ValueError(string)


class TLStruct:
    LAYER = 198

    def __init__(self, raise_error=True):
        setGlobalPrintFullStrings(True)
        setGlobalPrintPrivateEntries(False)
        if raise_error:
            self.exception = raise_exception
        else:
            self.exception = logger.exception

    def parse_blob(self, data):
        result = self.parse(data)
        if not result:
            return None
        elif len(result) == 1:
            return result[0]
        else:
            return result

    def get_parser(self, data):
        signature = int.from_bytes(data[:4], 'little')
        return getattr(self, f'struct_0x{signature:08x}', None)

    def parse(self, data):
        result = []
        parser = self.get_parser(data)
        if parser is None:
            count = int.from_bytes(data[:4], 'little')
            unparsed = data[4:]
            parsed_len = 4
            unknown = count
        else:
            count = 256
            unparsed = data
            parsed_len = 0
            unknown = None
        data_len = len(data)
        for _ in range(count):
            parser = self.get_parser(unparsed)
            if parser:
                ret = parser().parse(unparsed)
                result.append(ret)
                parsed_len += ret._io.tell()
                if data_len == parsed_len:
                    break
                unparsed = data[parsed_len:]
            else:
                signature = int.from_bytes(unparsed[:4], 'little')
                if signature in INFO:
                    name = INFO.get(signature)
                    self.exception('Not all data parsed for object: %s [0x%08x], '
                                   'input: %d, parsed: %d, missed: %s',
                                   name, signature, data_len, parsed_len,
                                   data[parsed_len:])
                else:

                    self.exception('unknown signature: 0x%08x,'
                                   'data: %s',
                                   unknown or signature, data)
        return result

    # ---------------------------- Common start -------------------------------

    @constructor(0x1cb5c415, 'vector', use_lru=True)
    def vector(self, datatype, name: str):
        return Struct(
            'sname' / Computed('vector'),
            'signature' / Hex(Const(0x1cb5c415, Int32ul)),
            'count' / Int32ul,
            'content' / Array(this.count, datatype))

    # ---------------------------- Common end ---------------------------------

