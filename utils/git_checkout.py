# -*- coding: utf-8 -*-
"""
Created on Thu Dec  8 19:16:51 2022

@author: 皓
"""
import re
import os
import os.path as osp
from subprocess import check_output, call
import shutil
from glob import iglob, glob


URL = 'https://github.com/DrKLO/Telegram.git'


def git_checkout(url, path):
    ret = call(['git', 'clone', url], cwd=path)
    assert ret == 0
    return ret


def git_pull(path):
    return call(['git', 'pull'], cwd=path)


def git_remote(path):
    ret = check_output(['git', 'remote', '-v'], cwd=path,
                       universal_newlines=True)
    return re.search(r'origin\s+([^\s]+)\s+\(fetch\)', ret).group(1)


def get_git_log(path):
    dirname, basename = osp.split(osp.realpath(path))
    output = check_output(['git', 'log', basename], cwd=dirname,
                          universal_newlines=True)
    log_pattern = re.compile(r'commit (\w{40})(?:(?!commit \w{40}).)+', re.S)
    version_pattern = re.compile(r'Update to ([\d\.]+)', re.I)
    log_info = {}
    for item in log_pattern.finditer(output):
        content = item.group(0)
        commit_hash = item.group(1)
        try:
            version = version_pattern.search(content).group(1)
        except AttributeError as e:
            print(content)
            raise e
        info = {'hash': commit_hash, 'version': version, 'content': content}
        log_info[commit_hash] = info
    return log_info


def git_checkout_file(path, outdir=None):
    path = osp.realpath(path)
    outdir = osp.realpath(outdir) if outdir else os.getcwd()
    log_info = get_git_log(path)
    # print(log_info)
    dirname, basename = osp.split(osp.realpath(path))
    fname, ext = osp.splitext(basename)
    checkout = False
    for commit_hash, commit_info in log_info.items():
        s_commit = commit_hash[:8]
        version = commit_info['version']
        find_files = glob(osp.join(outdir,
                                   f'{fname}-{version}-*-{s_commit}{ext}'))
        if find_files:
            continue  # pylint: disable=E275
        ret = call(['git', 'checkout', commit_hash, basename], cwd=dirname)
        checkout = True
        print('Checkout', s_commit, 'version', version)
        assert ret == 0
        with open(path, encoding='utf-8') as f:
            c = f.read(10000)
        try:
            layer = re.search(r'int LAYER = (\d+);', c).group(1)
        except AttributeError:
            layer = 'null'
        dst = osp.join(outdir, f'{fname}-{version}-{layer}-{s_commit}{ext}')
        if not osp.exists(dst):
            shutil.copy2(path, dst)
    if checkout:
        origin_commit = list(log_info.values())[0]
        call(['git', 'checkout', origin_commit['hash'], basename], cwd=dirname)


def check_layer(path, index):
    path = os.getcwd() if not path else osp.realpath(path)
    assert osp.isdir(path)
    lays = []
    vers = []
    for file in iglob(osp.join(path, '*')):
        fname = osp.splitext(osp.basename(file))[0]
        *_, ver, lay, ci = fname.split('-')
        with open(file, encoding='utf-8') as f:
            c = f.read()
            if c.find(index) < 0:
                continue  # pylint: disable=E275
            lays.append(int(lay))
            vers.append(ver)
    if lays:
        print(f'layer range [{min(lays)}, {max(lays)}]')
    else:
        print('Can not find index', index)
    if vers:
        print(f'version range [{min(vers)}, {max(vers)}]')
    else:
        print('Can not find version', index)


def update_telegram(path=None):
    if not path:
        path = os.getcwd()
    telegram_path = osp.join(path, 'Telegram')
    if not osp.exists(telegram_path):
        print('Git clone', URL)
        git_checkout(URL, path)
    else:
        url = git_remote(telegram_path)
        print('Git fetch', url)
        git_pull(telegram_path)
    TLRPC_path = osp.join(telegram_path,
                          'TMessagesProj',
                          r'src\main\java\org\telegram\tgnet\TLRPC.java')
    git_checkout_file(TLRPC_path, 'files')


def check_layer_range(path, index=None):
    index = '0xa518110d'
    index = '0x818426cd'
    path = 'file'
    check_layer(path, index)


def main(path=None):
    update_telegram(path)
    # check_layer_range('files')


if __name__ == '__main__':
    main()
