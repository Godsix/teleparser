# -*- coding: utf-8 -*-
"""
Created on Mon Dec 12 10:14:11 2022

@author: 皓
"""
import fileinput


def test1():
    path = r'datatype/telegram.py'
    path2 = r'datatype/telegram2.py'
    ql = []
    with open(path2, 'w+', encoding='utf-8') as f:
        for line in fileinput.input(path, encoding='utf-8'):
            if line.lstrip().startswith('@constructor'):
                f.write(line)
                continue
            if len(line) > 80 and 0 < (p := line.rfind(',')) < 79:
                # print(len(line), p, line)
                # break
                ql.clear()
                for i in range(p, -1, -1):
                    if line[i] == ')':
                        ql.append(line[i])
                    elif line[i] == '(':
                        if ql:
                            ql.pop()
                        else:
                            index = i
                            break
                else:
                    index = -1
                if index == -1:
                    f.write(line)
                    continue
                f.write(f'{line[:p+1]}\n')
                f.write(f'{" " * (index + 0)}{line[p+1:]}')
            else:
                f.write(line)


def main():
    test1()


# ------------------------------------------------------------------------------
if __name__ == '__main__':
    # generate_code()
    main()
