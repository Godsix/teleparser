# -*- coding: utf-8 -*-
"""
Created on Tue Dec  6 00:45:38 2022

@author: 皓
"""
from datetime import datetime, UTC
from construct import (Struct, Computed, Int32ul, Hex, Byte, Bytes,
                       IfThenElse, If, Padding, Peek, this)
import logger


def decode_tstring(binarray):
    try:
        str_utf = binarray.decode('utf-8')
    except UnicodeDecodeError:
        logger.error('unable to decode string: %s', binarray)
        str_utf = binarray
    return str_utf


TString = Struct(
    '_sname' / Computed('tstring'),
    '_check' / Peek(Byte),
    '_pl' / IfThenElse(this._check >= 254, Int32ul, Byte),
    '_len' / IfThenElse(this._check >= 254,
                        Computed(this._pl >> 8),
                        Computed(this._pl)),
    # 'value' / PaddedString(this._len, 'utf-8'),
    '_value' / Bytes(this._len),
    'string' / Computed(lambda x: decode_tstring(x._value)),
    IfThenElse(this._check >= 254,
               If(this._len % 4, Padding(4 - this._len % 4)),
               If((this._len + 1) % 4, Padding(4 - (this._len + 1) % 4))))


TBytes = Struct(
    '_sname' / Computed('tbytes'),
    '_check' / Peek(Byte),
    '_pl' / IfThenElse(this._check >= 254, Int32ul, Byte),
    'len' / IfThenElse(this._check >= 254,
                       Computed(this._pl >> 8),
                       Computed(this._pl)),
    # 'bytes' / Array(this.len, Byte),
    'bytes' / Hex(Bytes(this.len)),
    IfThenElse(this._check >= 254,
               If(this.len % 4, Padding(4 - this.len % 4)),
               If((this.len + 1) % 4, Padding(4 - (this.len + 1) % 4))))

TBool = Struct(
    'sname' / Computed('boolean'),
    '_signature' / Int32ul,
    'value' / IfThenElse(this._signature == 0xbc799737,
                         Computed('false'),
                         IfThenElse(this._signature == 0x997275b5,
                                    Computed('true'),
                                    Computed('ERROR'))))

# This is not struct define by Telegram, but it's useful to get human readable
# timestamps.
TTimestamp = Struct(
    'epoch' / Int32ul,
    'date' / Computed(lambda ctx: datetime.fromtimestamp(ctx.epoch, UTC).isoformat()))
