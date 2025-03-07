#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Telegram cache4 db parser.
# Part of the project: tblob.py tdb.py logger.py
#
# Version History
# - 20250306: added support for version 11.7.0
# - 20240328: added support for version 10.9.1
# - 20221201: added support for version 9.2.1
# - 20200807: added support for version 6.3.0
# - 20200803: changed sqlite3 opening to 'bytes', fixed tdb.py on ver 4.9.0
# - 20200731: fixed wrong object ID for page_block_subtitle
# - 20200622: fixed wrong object 0x83e5de54 (message_empty_struct)
# - 20200617: added support for 5.15.0
# - 20200418: change eol terminators, added requirements file
# - 20200407: [tblob] fixed a bug, [tdb] added a couple of checks base on
#             version 4.8.11, added small script to test/debug single blobs
# - 20200406: first public release (5.5.0, 5.6.2)
# - 20190729: first private release
#
# Released under MIT License
#
# Copyright (c) 2019 Francesco "dfirfpi" Picasso, Reality Net System Solutions
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
'''Telegram cache4 db parser, script entry point.'''

# pylint: disable= C0103,C0116
import sys
import os.path as osp
from argparse import ArgumentParser
from database import TelegramDB
import logger
import tdb2 as tdb

VERSION = '20250306'

# ------------------------------------------------------------------------------


def process(db_path, outdir):
    db = TelegramDB(db_path)

    teledb = tdb.TDB(outdir, db)
    teledb.parse()

    teledb.save_parsed_tables()
    teledb.create_timeline()


def main():

    parser = ArgumentParser(description=f'Telegram parser version {VERSION}')
    parser.add_argument('database', help='input file cache4.db')
    parser.add_argument('outdir', help='output directory, must exist')
    parser.add_argument('-v', '--verbose', action='count',
                        help='verbose level, -v to -vvv')
    args = parser.parse_args()

    logger.configure_logging(args.verbose)

    if osp.isdir(args.database):
        database = osp.join(args.database, 'cache4.db')
        if not osp.isfile(database):
            logger.error('The provided input dir does not contain cache4.db: %s',
                         args.database)
            return
    else:
        database = args.database
        if not osp.exists(database):
            logger.error('The provided input file does not exist: %s',
                         args.database)
            return
    if osp.isdir(args.outdir):
        process(database, args.outdir)
    else:
        logger.error('Output directory [%s] does not exist!',
                     args.outdir)

# ------------------------------------------------------------------------------


if __name__ == '__main__':
    if sys.version_info[:2] < (3, 8):
        sys.exit('Python 3.8 or above version is required.')
    main()
