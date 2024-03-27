# -*- coding: utf-8 -*-
"""
Created on Thu Dec 15 10:43:58 2022

@author: 皓
"""
import logging
from generater.parser import TLRPCParser


def main():
    # path = r"utils\files\TLRPC-9.4.5-152-810bc4ae.java"
    path = r"utils\files\TLRPC-9.3.3-151-1c03d75e.java"
    parser = TLRPCParser(path, level=logging.INFO, strict=True)
    # parser.generate_tlrpc('new.py')
    # print(parser.cache)
    parser.merge_tlrpc(r'datatype\telegram.py', 'new.py')


if __name__ == '__main__':
    main()
