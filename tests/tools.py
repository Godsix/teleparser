# -*- coding: utf-8 -*-
"""
Created on Mon Dec  5 18:59:20 2022

@author: 皓
"""
import re
import os.path as osp
import pyperclip
# from generate_code import PyCodeGenerator


# def translate_cpp_from_clipboard():
#     obj = PyCodeGenerator(r'datatype')
#     obj.parse()


def sub_func(match):
    return f'is_{match.group(1)}={match.group(2)},'


# def main():
#     # translate_cpp_from_clipboard()
#     content = pyperclip.paste()
#     c = re.sub(r'(\w+) = \(flags & (\d+)\) != 0;', sub_func, content)
#     print(c)
#     pyperclip.copy(c)

def main():
    # translate_cpp_from_clipboard()
    content = pyperclip.paste()
    index, _ = re.search(r"@constructor\((\w+), '(\w+)'.*\)", content).groups()
    path = osp.join(r'..\generater\structs', index)
    if osp.exists(path):
        print('path exists:', path)
    c = content.encode()
    for i in range(3):
        c = c.replace(b'\r\n', b'\n')
    c = c.replace(b'\n', b'\r\n')
    with open(path, 'wb') as f:
        f.write(c)
        print('File is OK', index)


if __name__ == "__main__":
    main()
