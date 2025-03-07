# -*- coding: utf-8 -*-
"""
Created on Sat Feb  8 15:17:15 2025

@author: C. David
"""
import os
import re
import json
import pickle
import shutil
import os.path as osp
from glob import iglob
from tqdm import tqdm
import logger
from database import TelegramDB
from datatype import pythonic, get_obj_value, MIME_TYPE
from tools import sanitize_filename


def logger_print(text, *args):
    arg = text, *args
    print(*arg, flush=True)


log_print = logger_print


def get_tables_count(path):
    db_path = osp.join(path, 'cache4.db')
    db = TelegramDB(db_path)
    tables = db.tables()
    for item in tables:
        print(item,
              db.table_count(item),
              [x['name'] for x in db.inspect.get_columns(item)])


def get_document_name(document):
    name = f'{document.dc_id}_{document.id}'
    ext = None
    if document.attributes:
        attributes = document.attributes.content
        for item in attributes:
            attribute = item.attributes
            if hasattr(attribute, 'file_name'):
                file_name = attribute.file_name.string
                ext = osp.splitext(file_name)[1]
    if ext is None:
        ext = MIME_TYPE.get(document.mime_type.string)
    return f'{name}{ext}'


def dump_obj(path, obj):
    with open(path, 'w+', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=4, default=str)


def load_obj(path):
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def dump_pickle_obj(path, obj):
    with open(path, 'wb') as f:
        pickle.dump(obj, f)


def load_pickle_obj(path):
    try:
        with open(path, 'rb') as f:
            return pickle.load(f)
    except Exception:
        return {}


def check_parser(path, table_name=None):
    db_path = osp.join(path, 'cache4.db')
    db = TelegramDB(db_path)
    tables = db.tables()
    for table in tables:
        # if table_name and table_name != table:
        #     continue
        if table_name and table_name > table:
            continue
        model = db.get_table_model(table)
        query = db.session.query(model)
        data_count = query.count()
        if data_count == 0:
            continue
        # log_print(f'{table}\t{data_count}')
        result = query.all()
        columns = db.get_blob_columns(table)
        for rowid, row in tqdm(enumerate(result),
                               desc=f"Processing {table}",
                               unit="item"):
            for column in columns:
                try:
                    _ = getattr(row, f'{column}_blob')
                except Exception as e:
                    data = getattr(row, column)
                    log_print(table, rowid, column, e, data)
                    raise e


# def check_parser(path, table_name=None):
#     db_path = osp.join(path, 'cache4.db')
#     db = TelegramDB(db_path)
#     tables = db.tables()
#     for table in tables:
#         if table_name and table_name != table:
#             continue
#         model = db.get_table_model(table)
#         query = db.session.query(model)
#         data_count = query.count()
#         if data_count == 0:
#             continue
#         # log_print(f'{table}\t{data_count}')
#         result = query.all()
#         data = [y for x in result if (y:=x.pbytes)]
#         for item in tqdm(data,
#                          desc=f"Processing {table}",
#                          unit="item"):
#             print(item)

def get_data(path, table, n, col):
    db_path = osp.join(path, 'cache4.db')
    db = TelegramDB(db_path)
    model = db.get_table_model(table)
    query = db.session.query(model)
    if not (row := query.offset(n-1).limit(1).first()):
        return
    data = getattr(row, f'{col}_blob')
    return data


def get_all(path, table):
    db_path = osp.join(path, 'cache4.db')
    db = TelegramDB(db_path)
    model = db.get_table_model(table)
    query = db.session.query(model)
    return query.all()


def get_user(path, uid):
    db_path = osp.join(path, 'cache4.db')
    db = TelegramDB(db_path)
    model = db.get_table_model('users')
    query = db.session.query(model).filter(model.uid == uid)
    ret = query.first()
    if ret:
        print(ret.data_blob)
    return ret


def get_channel(path, uid):
    db_path = osp.join(path, 'cache4.db')
    db = TelegramDB(db_path)
    model = db.get_table_model('chats')
    query = db.session.query(model).filter(model.uid == uid)
    ret = query.first()
    if ret:
        print(ret.name, ret.data_blob)
    return ret


def mod_parser(test_file):
    from datatype import TLStruct
    test_path = osp.realpath(test_file)
    db = TelegramDB(test_path)
    model = db.get_table_model('messages')
    query = db.session.query(model)
    # result = query.all()
    # item = result[0]
    n = 2
    item = query.offset(n-1).limit(1).first()
    data = item.data
    print(item, item.data_blob)


# {'media.document.id': None,
# 'media.webpage.document.id': None,
# 'media.alt_documents[i].id': None,
# 'entities[i].document_id': 动态表情,
# 'reply_to.reply_media.document.id': 回复媒体}
def get_media_info(obj):
    obj = pythonic(obj)
    result = []
    media_list = []
    document_list = []
    photo_list = []
    if get_obj_value(obj, 'flags.has_media', False):
        media = get_obj_value(obj, 'media')
        media_list.append(media)
    if get_obj_value(obj, 'flags.has_reply_to', False):
        reply_to = get_obj_value(obj, 'reply_to')
        if get_obj_value(reply_to, 'flags.has_reply_media', False):
            media = get_obj_value(reply_to, 'reply_media')
            media_list.append(media)

    for media in media_list:
        if get_obj_value(media, 'flags.has_document', False):
            document = get_obj_value(media, 'document')
            document_list.append(document)
        if get_obj_value(media, 'flags.has_alt_documents', False):
            alt_documents = get_obj_value(media, 'alt_documents')
            document_list.extend(alt_documents)
        if (webpage := get_obj_value(media, 'webpage')):
            if get_obj_value(webpage, 'flags.has_document'):
                document = get_obj_value(webpage, 'document')
                document_list.append(alt_documents)
            if get_obj_value(webpage, 'flags.has_photo'):
                photo = get_obj_value(webpage, 'photo')
                photo_list.append(photo)
            if get_obj_value(webpage, 'flags.has_cached_page'):
                documents = get_obj_value(webpage, 'cached_page.documents', [])
                document_list.extend(documents)
                photos = get_obj_value(webpage, 'cached_page.photos', [])
                photo_list.extend(photos)

    if get_obj_value(obj, 'flags.has_entities', False):
        entities = get_obj_value(obj, 'entities')
        for entity in entities:
            if (document_id := get_obj_value(entity, 'document_id')):
                result.append(document_id)

    for item in document_list:
        try:
            document_id = item['id']
            dc_id = item['dc_id']
        except Exception as e:
            print(item)
            raise e
        # result.append(f'{dc_id}_{document_id}')
        result.append(f'{document_id}')
    return result


# EXCEPT = {'access_hash'}


# def get_media_info2(obj):
#     obj = pythonic(obj)
#     result = re.findall(r"'(\w+)': (\d{16,20})", str(obj))
#     return [x[1] for x in result if x[0] not in EXCEPT]


def get_media_info2(obj):
    obj = pythonic(obj)
    return re.findall(r"'\w+': (\d{16,20})", str(obj))


def get_media_info(obj):
    obj = pythonic(obj)
    result = []
    has_media = get_obj_value(obj, 'flags.has_media', False)
    if not has_media:
        return result
    document_list = []
    media = get_obj_value(obj, 'media')
    has_document = get_obj_value(media, 'flags.has_document', False)
    if has_document:
        document = get_obj_value(media, 'document')
        document_list.append(document)
    has_cached_page = get_obj_value(
        media, 'webpage.flags.has_cached_page', False)
    if has_cached_page:
        page = get_obj_value(media, 'webpage.cached_page', False)
        document_list.extend(get_obj_value(page, 'documents', []))
    for item in document_list:
        try:
            document_id = item['id']
            dc_id = item['dc_id']
        except Exception as e:
            print(item)
            raise e
        # result.append(f'{dc_id}_{document_id}')
        result.append(f'{document_id}')
    return result


# EXCEPT = {'access_hash'}


# def get_media_info2(obj):
#     obj = pythonic(obj)
#     result = re.findall(r"'(\w+)': (\d{16,20})", str(obj))
#     return [x[1] for x in result if x[0] not in EXCEPT]


def get_media_info2(obj):
    obj = pythonic(obj)
    return re.findall(r"'file_name': (\d{16,20})", str(obj))


def test2():
    path = 'cache4.db'
    table = 'media'
    ret = get_data(path, table, 8, 'data')
    print(get_media_info(ret))
    # print(dir(ret.media.media.webpage.webpage.cached_page.cached_page.documents))
    # print(ret.media.media.webpage.webpage.cached_page.cached_page.documents.sname)
    # print(get_data(path, table, 1, 'data'))

    # get_user(path, 1763508756)
    # get_channel(path, 1294171381)   # 1505881006


def test3():
    path = 'cache4.db'
    table = 'media'
    path = osp.realpath(path)
    db = TelegramDB(path)
    media_class = db.get_table_model(table)
    query = db.session.query(media_class)
    media_list = query.all()
    chats_class = db.get_table_model('chats')
    query = db.session.query(chats_class)
    chats_list = query.all()
    channel_info = {x.uid: x.name for x in chats_list}
    uid_info = dict.fromkeys(x.uid for x in media_list)
    for k in uid_info:
        if k < 0:
            channel_id = k * -1
            print(channel_id, channel_info.get(channel_id, 'unknown'))

    # get_user(path, 1763508756)
    # get_channel(path, 1294171381)   # 1505881006


def test4():
    path = 'cache4.db'
    file_path = r'K:\Software\files\Telegram\Telegram Video'
    dc_info_path = 'dc_info.json'
    ch_info_path = 'ch_info.json'
    print('Get file list')
    filelist = [x for x in os.listdir(file_path) if re.fullmatch(
        r'\d_\d+', osp.splitext(x)[0])]
    file_info = {}
    for item in filelist:
        fname, ext = osp.splitext(item)
        if fname not in file_info:
            file_info[fname] = item
        else:
            print(fname, file_info[fname], item)
    path = osp.realpath(path)
    db = TelegramDB(path)
    print('Get document info')
    dc_info = load_obj(dc_info_path)
    if not dc_info:
        media_class = db.get_table_model('media')
        query = db.session.query(media_class)
        media_list = query.all()
        for item in tqdm(media_list, desc="Processing", unit="item"):
            data = item.data_blob
            ret = get_media_info(data)
            if not ret:
                continue
            uid = item.uid
            for subitem in ret:
                info = dc_info.setdefault(subitem, {})
                info[uid] = None
        dc_info = {k: list(v) for k, v in dc_info.items()}
        dump_obj(dc_info_path, dc_info)

    print('Get chat info')
    ch_info = load_obj(ch_info_path)
    if not ch_info:
        chats_class = db.get_table_model('chats')
        query = db.session.query(chats_class)
        chats_list = query.all()
        ch_info = {x.uid: x.name for x in chats_list}
        dump_obj(ch_info_path, ch_info)
    else:
        ch_info = {int(k): v for k, v in ch_info.items()}

    dir_info = {}

    for k, v in dc_info.items():
        if k in file_info:
            names = [ch_info[y] for x in v if x < 0 and (y := -x) in ch_info]
            if len(names) > 1:
                print(k, *names)
            elif len(names) == 1:
                name = names[0]
                src = osp.join(file_path, file_info[k])
                if name not in dir_info:
                    vname = sanitize_filename(name)
                    dst_dir = osp.join(file_path, vname)
                    dst = osp.join(dst_dir, file_info[k])
                    if not osp.isdir(dst_dir):
                        os.makedirs(dst_dir)
                    dir_info[name] = vname
                else:
                    dst_dir = osp.join(file_path, dir_info[name])
                    dst = osp.join(dst_dir, file_info[k])
                shutil.move(src, dst)
            elif not names:
                if len(v) == 1:
                    name = str(v[0])
                    src = osp.join(file_path, file_info[k])
                    if name not in dir_info:
                        vname = sanitize_filename(name)
                        dst_dir = osp.join(file_path, vname)
                        dst = osp.join(dst_dir, file_info[k])
                        if not osp.isdir(dst_dir):
                            os.makedirs(dst_dir)
                        dir_info[name] = vname
                    else:
                        dst_dir = osp.join(file_path, dir_info[name])
                        dst = osp.join(dst_dir, file_info[k])
                    shutil.move(src, dst)
                else:
                    print(v)
            else:
                print(v)


def test5():
    path = 'cache4.db'
    dc_info_path = 'media_info.json'
    path = osp.realpath(path)
    db = TelegramDB(path)
    print('Get document info')
    media_class = db.get_table_model('media')
    query = db.session.query(media_class)
    media_list = query.all()
    # media_list = [query.first()]
    dc_info = {}
    count = 0
    cur = 1
    for item in tqdm(media_list, desc="Processing", unit="item"):
        data = item.data_blob
        result = pythonic(data)
        dc_info[(item.mid, item.uid, item.type)] = result
        count += 1
        if count == 10000:
            dump_pickle_obj(f'media_info-{cur}.json', dc_info)
            cur += 1
            count = 0
            dc_info.clear()
    dump_pickle_obj(f'media_info-{cur}.json', dc_info)
    # dump_obj(dc_info_path, dc_info)


def get_telegram_video(path):
    result = {}
    for item in os.listdir(path):
        fname, ext = osp.splitext(item)

        if (m := re.fullmatch(r'\-(\d+)_(\d+)', fname)):
            doc_id, dc_id = m.groups()
            if doc_id not in result:
                result[doc_id] = item
            else:
                print(fname, result[doc_id], doc_id)
        elif (m := re.fullmatch(r'(\d)_(\d+)', fname)):
            dc_id, doc_id = m.groups()
            if doc_id not in result:
                result[doc_id] = item
            else:
                print(fname, result[doc_id], doc_id)
    return result

# Telegram Video {dc_id}_{id}
# Telegram Documents {dc_id}_{id}
# Telegram Audio {dc_id}_{id}
# Telegram Images -{id}_{id}


def test6(path):
    file_path = r'K:\Software\files\Telegram\Telegram Video'
    # file_path = r'K:\Software\files\Telegram\Telegram Documents'
    # file_path = r'K:\Software\files\Telegram\Telegram Images'
    # file_path = r'K:\Software\files\Telegram\Telegram Stories'
    # file_path = r'K:\Software\files\Telegram\Telegram Audio'

    db_path = osp.join(path, 'cache4.db')
    media_info_path = osp.join(path, 'media_info.pickle')
    message_info_path = osp.join(path, 'message_info.pickle')
    ch_info_path = osp.join(path, 'channel_info.json')
    print('Get file list')
    file_info = get_telegram_video(file_path)

    db = TelegramDB(db_path)

    print('Get media info')
    media_info = load_pickle_obj(media_info_path)
    if not media_info:
        media_class = db.get_table_model('media')
        query = db.session.query(media_class)
        media_list = query.all()
        for item in tqdm(media_list, desc="Processing", unit="item"):
            data = item.data_blob
            media_info[(item.mid, item.uid, item.type)] = get_media_info2(data)
        dump_pickle_obj(media_info_path, media_info)

    print('Get message info')
    message_info = load_pickle_obj(message_info_path)
    if not message_info:
        messages_class = db.get_table_model('messages')
        query = db.session.query(messages_class)
        messages_list = query.all()
        for item in tqdm(messages_list, desc="Processing", unit="item"):
            data = item.data_blob
            message_info[(item.mid, item.uid)] = get_media_info2(data)
        dump_pickle_obj(message_info_path, message_info)

    print('Get chat info')
    ch_info = load_obj(ch_info_path)
    if not ch_info:
        chats_class = db.get_table_model('chats')
        query = db.session.query(chats_class)
        chats_list = query.all()
        ch_info = {x.uid: x.name for x in chats_list}
        dump_obj(ch_info_path, ch_info)
    else:
        ch_info = {int(k): v for k, v in ch_info.items()}

    finfo = {}

    for k, v in media_info.items():
        uid = k[1]
        for item in v:
            if item in file_info:
                fname = file_info[item]
                info = finfo.setdefault(fname, {})
                info[uid] = None

    for k, v in message_info.items():
        uid = k[1]
        for item in v:
            if item in file_info:
                fname = file_info[item]
                info = finfo.setdefault(fname, {})
                info[uid] = None

    finfo = {k: list(v) for k, v in finfo.items()}

    dir_info = {}

    for k, v in finfo.items():
        if not v:
            continue
        if len(v) == 1:
            vv = v[0]
            if vv > 0:
                name = str(vv)
            else:
                name = ch_info.get(-vv, str(vv))
        else:
            names = [ch_info[y] for x in v if x < 0 and (y := -x) in ch_info]
            if names:
                name = names[0]
            else:
                name = str(v[0])
        src = osp.join(file_path, k)
        if name not in dir_info:
            vname = sanitize_filename(name)
            dst_dir = osp.join(file_path, vname)
            dst = osp.join(dst_dir, k)
            if not osp.isdir(dst_dir):
                os.makedirs(dst_dir)
            dir_info[name] = vname
        else:
            dst_dir = osp.join(file_path, dir_info[name])
            dst = osp.join(dst_dir, k)
        print(f'{src} => {dst}')
        shutil.move(src, dst)


def test7(path):
    db_path = osp.join(path, 'cache4.db')
    db = TelegramDB(db_path)
    regex = re.compile(r"'(\w+)': '([^']+\.txt)'")

    print('Get media info')
    media_class = db.get_table_model('media')
    query = db.session.query(media_class)
    media_list = query.all()
    media_info = {}
    for item in tqdm(media_list, desc="Processing", unit="item"):
        key = (item.mid, item.uid, item.type)
        data = item.data_blob
        obj = pythonic(data)
        obj_str = str(obj)
        result = regex.findall(obj_str)
        if result:
            for item in result:
                print(item)

    print('Get message info')
    message_info = {}
    messages_class = db.get_table_model('messages')
    query = db.session.query(messages_class)
    messages_list = query.all()
    for item in tqdm(messages_list, desc="Processing", unit="item"):
        key = (item.mid, item.uid)
        data = item.data_blob
        obj = pythonic(data)
        obj_str = str(obj)
        result = regex.findall(obj_str)
        if result:
            for item in result:
                print(item)


def parse_path(obj, path=None, result=None):
    if path is None:
        p = ''
    elif isinstance(obj, dict):
        p = f'{path}.'
    elif isinstance(obj, list):
        p = path
    else:
        return
    if result is None:
        result = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, (dict, list)):
                parse_path(v, f'{p}{k}', result)
            elif isinstance(v, int) and v > 10000000000:
                result[f'{p}{k}'] = v
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            if isinstance(item, (dict, list)):
                parse_path(item, f'{p}[{i}]', result)
            elif isinstance(item, int) and item > 10000000000:
                result[f'{p}[{i}]'] = item
    return result


def parse_path2(obj, path=None, result=None):
    if path is None:
        p = ''
    elif isinstance(obj, dict):
        p = f'{path}.'
    elif isinstance(obj, list):
        p = path
    else:
        return
    if result is None:
        result = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, (dict, list)):
                parse_path2(v, f'{p}{k}', result)
            elif k == 'file_name':
                result[f'{p}{k}'] = v
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            if isinstance(item, (dict, list)):
                parse_path2(item, f'{p}[{i}]', result)
    return result


def pprint(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=4, default=str))


def test8(path):


    path_list = [
        r"E:\Project\Godsix\teleparser\version_1",
        # r"E:\Project\Godsix\teleparser\version_2"
    ]
    media_class = None
    messages_class = None
    media_info_list = []
    message_info_list = []
    index = 3
    for path in path_list:
        db_path = osp.join(path, 'cache4.db')
        db = TelegramDB(db_path)
        media_info_path = osp.join(path, f'media_info{index}.pickle')
        media_info = load_pickle_obj(media_info_path)
        if not media_info:
            print('Get media info')
            media_class = db.get_table_model('media')
            query = db.session.query(media_class)
            media_list = query.all()
            for item in tqdm(media_list, desc="Processing", unit="item"):
                data = item.data_blob
                obj = pythonic(data)
                ret = parse_path2(obj)
                if ret:
                    media_info[(item.mid, item.uid, item.type)] = ret
            dump_pickle_obj(media_info_path, media_info)
        media_info_list.append(media_info)

        message_info_path = osp.join(path, f'message_info{index}.pickle')
        message_info = load_pickle_obj(message_info_path)
        if not message_info:
            print('Get message info')
            messages_class = db.get_table_model('messages')
            query = db.session.query(messages_class)
            messages_list = query.all()

            for item in tqdm(messages_list, desc="Processing", unit="item"):
                data = item.data_blob
                obj = pythonic(data)
                ret = parse_path2(obj)
                if ret:
                    message_info[(item.mid, item.uid)] = ret
            dump_pickle_obj(message_info_path, message_info)
        message_info_list.append(message_info)
        
        
    find_key_info = {}
    
    for item in media_info_list + message_info_list:
        for k, v in item.items():
            print(k, v)
    
    return


    # file_path = r'K:\Software\files\Telegram'
    # file_path = r'K:\Software\files\Telegram\Telegram Video'
    # file_path = r'K:\Software\files\Telegram\Telegram Documents'
    file_path = r'K:\Software\files\Telegram\Telegram Images'
    # file_path = r'K:\Software\files\Telegram\Telegram Stories'
    # file_path = r'K:\Software\files\Telegram\Telegram Audio'

    # id_info_path = 'id_info_all.pickle'
    id_info_path = 'id_info.pickle'
    print('Get id info')
    id_info = load_pickle_obj(id_info_path)
    if not id_info:
        it = iglob(osp.join(file_path, '**', '*'), recursive=True)
        for item in it:
            dirname, basename = osp.split(item)
            fname, ext = osp.splitext(basename)
            if (m := re.fullmatch(r'\-(\d+)_(\d+)', fname)):
                doc_id, dc_id = m.groups()
                obj = id_info.setdefault(doc_id, [])
                obj.append(item)
            elif (m := re.fullmatch(r'(\d)_(\d+)', fname)):
                dc_id, doc_id = m.groups()
                obj = id_info.setdefault(doc_id, [])
                obj.append(item)
        id_info = {int(k): v for k, v in id_info.items()}
        dump_pickle_obj(id_info_path, id_info)

    find_id_info = {}
    find_key_info = {}

    db_path = osp.join(path, 'cache4.db')
    db = TelegramDB(db_path)
    media_class = db.get_table_model('media')
    messages_class = db.get_table_model('messages')
    # animated_emoji = db.get_table_model('animated_emoji')
    # query = db.session.query(animated_emoji)
    # animated_emojis = query.all()
    # for item in animated_emojis:
    #     if item.document_id in id_info:
    #         print(id_info[item.document_id])

    # return

    for item in media_info_list + message_info_list:
        for k, v in item.items():
            for subitem in set(v.values()):
                if subitem in id_info:
                    text = [key for key, value in v.items() if value ==
                            subitem]
                    if any(x.startswith('media.webpage.cached_page.blocks') for x in text):
                        print(text)
            # for subk, subv in v.items():
            #     if subv in id_info:
            #         find_id_info[subv] = None
            #         find_key_info[subk] = find_key_info.setdefault(subk, 0) + 1
            #         if subk.startswith('media.webpage.cached_page.blocks'):
            #             if len(k) == 3:
            #                 query = db.session.query(media_class).filter(media_class.mid == k[0], media_class.uid == k[1])
            #                 result = query.first()
            #             else:
            #                 query = db.session.query(messages_class).filter(messages_class.mid == k[0], messages_class.uid == k[1])
            #                 result = query.first()
            #             if result:
            #                 print(subk, subv)
            #                 pobj = pythonic(result.data_blob)
            #                 pprint(get_obj_value(pobj, 'media.webpage.cached_page.blocks'))
            #                 dump_obj('11.json', pobj)

    pprint(find_key_info)


def main(path=None):
    path = r"E:\Project\Godsix\teleparser\version_2"
    test8(path)
    # check_parser(path, 'params')
    # get_tables_count(path)


if __name__ == '__main__':
    main()
