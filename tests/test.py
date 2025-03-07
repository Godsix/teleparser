# -*- coding: utf-8 -*-
"""
Created on Mon Dec 12 08:51:24 2022

@author: C. David
"""
import re
import os.path as osp
from database import TelegramDB
from datatype import get_obj_value
import mimetypes
from glob import glob


PATH = r'cache4.db'


def get_extension(mime, filename):
    if filename:
        ext = osp.splitext(filename)[1]
    else:
        ext = mimetypes.guess_extension(mime)
    return ext


def test1():
    db = TelegramDB(PATH)
    print(db.user_version)
    print(db.get_chats())
    print(db.get_chats()[0], dir(db.get_chats()[0]))
    return
    results = db.get_media()
    # result = db.session.query(Users).get(5560797026)
    # print(result)
    ef = r'F:\Project\MIUI\20221020_112446\org.telegram.messenger\ef\Telegram'
    info = {}
    for i, item in enumerate(results):
        try:
            document = item.blob.media.media.document.document
            mime_type = document.mime_type.string
            dc_id = document.dc_id
            id_ = document.id
            attributes = document.attributes
            filename = get_obj_value(attributes.content,
                                     'attributes.file_name.string')
            ext = get_extension(mime_type, filename)
            fname = f'{dc_id}_{id_}*'
            fls = glob(osp.join(ef, '**', fname), recursive=True)
            if fls:
                fl = fls[0]
                dirname = osp.basename(osp.dirname(fl))
                info[dirname] = None
                ext1 = osp.splitext(fl)[1]
                # print(ext, ext1, mime_type, filename)
                if dirname == 'Telegram Documents':
                    print(ext, ext1, mime_type, filename, dirname)
                    print(item.blob, item.type)
                    break

                # break
            # print(mime_type)
            # info[mime_type] = None
            # if
        except AttributeError as e:
            pass
            # print(item.blob)
            # print(i, e)
            # raise e
        # try:
        #     # print(item.blob)
        #     print(item.blob.media.media.document.document.mime_type)
        # except Exception as e:
        #     key = int.from_bytes(item.data[:4], 'little')
        #     print(f'0x{key:08x}', item.data)
        #     print(i, e)
        #     break
        #     raise e
    print(list(info))
    # for k in info:
    #     print(k, mimetypes.guess_all_extensions(k))
    # print('Count:', len(results))
    # item = results[262]
    # document = item.blob.media.media.document.document
    # mime_type = document.mime_type.string
    # dc_id = document.dc_id
    # id_ = document.id
    # attributes = document.attributes
    # fname = f'{dc_id}_{id_}*'
    # fl = glob(osp.join(ef, '**', fname), recursive=True)
    # ext = osp.splitext(fl[0])[1]
    # print(ext, mime_type)
    # print(attributes.content)


def main():
    test1()


# ------------------------------------------------------------------------------
if __name__ == '__main__':
    # generate_code()
    main()
