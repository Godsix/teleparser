# -*- coding: utf-8 -*-
"""
Created on Thu Dec 15 10:43:58 2022

@author: 皓
"""
import logging
from generater.parser import TLRPCParser


def main():
    # path = r"utils\files\TLRPC-9.4.5-152-810bc4ae.java"
    path = r"utils\files\TLRPC-10.9.1-176-d62d2ed5.java"
    parser = TLRPCParser(path, level=logging.INFO, strict=True)
    # parser.generate_tlrpc('new.py')
    # print(parser.cache)
    parser.merge_tlrpc(r'datatype\telegram.py', 'new.py')
    # parser.generate_tlrpc('new.py')
    # TLRPCParser.collect_dup(r'datatype\telegram.py', 'a.py', 'b.py')
    # TLRPCParser.remove_dup(r'datatype\telegram.py', 'new.py', True)
    # TLRPCParser.format_pycode2(r'datatype\telegram.py', 'new.py')
    # TLRPCParser.format_pycode('new.py')
    # TLRPCParser.sort_func(r'datatype\telegram.py', 'new.py')
    # TLRPCParser.remove_dup_func(r'datatype\telegram.py', 'new.py', path)
    


if __name__ == '__main__':
    main()
