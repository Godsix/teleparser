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
                    result = STRUCT_CACHE[cid]
                else:
                    result = func(*args, **kwargs)
                    STRUCT_CACHE[cid] = result
                return result
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
                # Some structures has the 'UNPARSED' field to get the remaining
                # bytes. It's expected to get some of these cases (e.g. wrong
                # flags, it happens...) and I want everything to be in front of
                # the analyst. So, if UNPARSED has a length > 0, a warning
                # message is raised, but the missing data is in the blob.
                unparsed = getattr(pblob, 'UNPARSED', None)
                if unparsed:
                    unparsed_len = len(pblob.UNPARSED)
                    if unparsed_len:
                        logger.warning('Object: %s [0x%x] contains unparsed '
                                       'data [%d bytes], see UPARSED field',
                                       name, signature, unparsed_len)
                data_len = len(data)
                # In case the object has not (yet) the UNPARSED field, the next
                # check will raise and error and report the missed data. Note
                # that the missed data will be not reported in the blob.
                object_len = pblob._io.tell()
                if data_len != object_len:
                    logger.error('Not all data parsed for object: %s [0x%x], '
                                 'input: %d, parsed: %d, missed: %s',
                                 name, signature, data_len, object_len,
                                 data[object_len:])
            # else:
            #     logger.warning('blob \'%s\' [%s] not supported',
            #                    name, hex(signature))
        else:
            logger.error('unknown signature %s', hex(signature))
        return pblob

    # ---------------------------- Common start -------------------------------

    @constructor(0x1cb5c415, 'vector', use_lru=True)
    def struct_0x1cb5c415(self, datatype, name: str):
        name = 'content'
        return Struct(
            'sname' / Computed('vector'),
            'signature' / Hex(Const(0x1cb5c415, Int32ul)),
            'count' / Int32ul,
            name / Array(this.count, datatype))

    # ---------------------------- Common end ---------------------------------
