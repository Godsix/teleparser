# -*- coding: utf-8 -*-
"""
Created on Tue Dec  6 00:45:38 2022

@author: 皓
"""
from datetime import datetime, UTC
from construct import (Struct, Computed, Int32ul, Hex, Byte, Bytes,
                       IfThenElse, If, Padding, Peek, this)
import logger


def decode_string(ctx):
    value = ctx._value  # pylint: disable=W0212
    try:
        result = value.decode('utf-8')
    except UnicodeDecodeError:
        logger.error('unable to decode string: %s', value)
        result = value
    return result


def parse_boolean(ctx):
    value = ctx._value  # pylint: disable=W0212
    if value == 0x997275b5:
        return True
    elif value == 0xbc799737:
        return False
    else:
        logger.error('Not bool value: %s', value)
        return False


def parse_timestamp(ctx):
    epoch = ctx.epoch
    return datetime.fromtimestamp(epoch, UTC).isoformat()


def parse_varint(ctx):
    check = ctx._check  # pylint: disable=W0212
    pl = ctx._pl  # pylint: disable=W0212
    return pl >> 8 if check >= 254 else pl


TString = Struct(
    '_sname' / Computed('string'),
    '_check' / Peek(Byte),
    '_pl' / IfThenElse(this._check >= 254, Int32ul, Byte),  # pylint: disable=W0212
    'len' / Computed(parse_varint),
    '_value' / Bytes(this.len),
    'value' / Computed(decode_string),
    IfThenElse(this._check >= 254,    # pylint: disable=W0212
               If(this.len % 4, Padding(4 - this.len % 4)),
               If((this.len + 1) % 4, Padding(4 - (this.len + 1) % 4))))


TBytes = Struct(
    '_sname' / Computed('bytes'),
    '_check' / Peek(Byte),
    '_pl' / IfThenElse(this._check >= 254, Int32ul, Byte),  # pylint: disable=W0212
    'len' / Computed(parse_varint),
    'value' / Hex(Bytes(this.len)),
    IfThenElse(this._check >= 254,    # pylint: disable=W0212
               If(this.len % 4, Padding(4 - this.len % 4)),
               If((this.len + 1) % 4, Padding(4 - (this.len + 1) % 4))))

TBool = Struct(
    'sname' / Computed('boolean'),
    '_value' / Int32ul,
    'value' / Computed(parse_boolean))

# This is not struct define by Telegram, but it's useful to get human readable
# timestamps.
TTimestamp = Struct(
    '_sname' / Computed('timestamp'),
    'epoch' / Int32ul,
    'date' / Computed(parse_timestamp))
