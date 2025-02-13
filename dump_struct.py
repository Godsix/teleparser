# -*- coding: utf-8 -*-
"""
Created on Thu Feb 13 18:10:55 2025

@author: 皓
"""
import re
import os.path as osp
import pyperclip


def main():
    content = pyperclip.paste()
    FUNCTION_PATTERN = re.compile(r"^ +@constructor\((\w+), +'(\w+)'\)", re.M)
    if (m := FUNCTION_PATTERN.match(content)):
        name = m.group(2)
        content = content.replace(name, '{name}')
        path = osp.realpath(osp.join('generater', 'structs', m.group(1)))
        # print(path, content)
        if osp.isfile(path):
            print(f'File has exists:{path}')
        else:
            with open(path, "w+", encoding="utf-8", newline='') as f:
                f.write(content)
            print("剪切板内容已写入 {osp.basename(path)}")
    else:
        print(f'content not match:{content}')


if __name__ == '__main__':
    main()
