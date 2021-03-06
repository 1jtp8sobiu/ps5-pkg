#!/usr/bin/env python3
import os
import json
import urllib.request
import urllib.error
import hashlib
import sys
import subprocess
import time
import ssl
import csv
import datetime
import traceback
import xml.etree.ElementTree as ET
ssl._create_default_https_context = ssl._create_unverified_context


import show_ps5_pkg_metadata as ps5meta


def convert_date_format(lastmodified):
    modified_yyyy = lastmodified[12:16]
    modified_month = lastmodified[8:11]

    if   modified_month == 'Jan':
        modified_mm = '01'
    elif modified_month == 'Feb':
        modified_mm = '02'
    elif modified_month == 'Mar':
        modified_mm = '03'
    elif modified_month == 'Apr':
        modified_mm = '04'
    elif modified_month == 'May':
        modified_mm = '05'
    elif modified_month == 'Jun':
        modified_mm = '06'
    elif modified_month == 'Jul':
        modified_mm = '07'
    elif modified_month == 'Aug':
        modified_mm = '08'
    elif modified_month == 'Sep':
        modified_mm = '09'
    elif modified_month == 'Oct':
        modified_mm = '10'
    elif modified_month == 'Nov':
        modified_mm = '11'
    elif modified_month == 'Dec':
        modified_mm = '12'

    modified_dd = lastmodified[5:7]
    modified_hh = lastmodified[17:19]
    modified_mn = lastmodified[20:22]
    modified_ss = lastmodified[23:25]
    
    modified_mmdd = modified_mm + modified_dd
    modified_hhmnss = modified_hh + modified_mn + modified_ss
        
    return modified_yyyy + modified_mmdd + '_' + modified_hhmnss


def get_hash_value(data, algo='sha256'):
    h = hashlib.new(algo)
    h.update(data)
    return h.hexdigest()


def wait_interval(seconds):
    ## チェック中(1) or 待機中(0)かをテキストに書き出し
    try:
        with open('C:/Settings/running.txt', 'w') as f:
            f.write('0')
    except:
        pass

    start = time.time()
    print('waiting interval...next check is in')
    count = seconds
    while time.time()-start < seconds:
        print(seconds-(time.time()-start), '\r', end='')
        time.sleep(60)
        
        ## check 'PS5_XML.tsv' hash
        if is_ps5_xml_tsv_updated():
            break

    print()
    time.sleep(10) ## スリープ復帰後だった場合のwait

    try:
        with open('C:/Settings/running.txt', 'w') as f:
            f.write('1')
    except:
        pass


def running_log(comment):
    with open('LOG/running.log', mode='a', encoding='utf-8', newline='\r\n') as f:
        f.write(f"[{datetime.datetime.now()}] {comment}\n")


def error_log(comment):
    with open('LOG/error.log', mode='a', encoding='utf-8', newline='\r\n') as f:
        f.write(f"[{datetime.datetime.now()}] {'-'*80}\n")
        f.write(f'{comment}\n')


def is_ps5_xml_tsv_updated():
    global ps5_xml_tsv_hash

    in_file = 'PS5_XML.tsv'
    with open(in_file, mode='rb') as f_in:
        tsv_hash = get_hash_value(f_in.read())

    if tsv_hash != ps5_xml_tsv_hash:
        ps5_xml_tsv_hash = tsv_hash
        return True
    else:
        return False


def snoretoast(title='Snoretoast', comment='Comment', icon_path=''):
    snoretoast_exe = 'C:/bin/snoretoast/snoretoast.exe'
    if not os.path.isfile(snoretoast_exe):
        return
    cmd = [snoretoast_exe, '-t', title, '-p', icon_path, '-m', comment, '-silent']
    subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def git_commit(comment):
    try:
        cmd = ['git', 'add', '.']
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(proc.stdout.decode('utf8'))

        cmd = ['git', 'commit', '-a', '-m', comment]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(proc.stdout.decode('utf8'))

        cmd = ['git', 'push', 'origin', 'master']
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(proc.stdout.decode('utf8'))
    except:
        pass


def download_ps5_xml_tsv(url):
    with urllib.request.urlopen(url) as res, open('PS5_XML.tsv', mode='wb') as f:
        f.write(res.read())


def append_new_tittle_id_to_tsv(param_json):
    new_contentId = param_json['contentId']
    new_defaultLanguage = param_json['localizedParameters']['defaultLanguage']
    new_titleName = param_json['localizedParameters'][new_defaultLanguage]['titleName']
    new_versionFileUri = param_json['versionFileUri'].strip()

    with open('PS5_XML.tsv', mode='a', encoding='utf-8', newline='\r\n') as f:
        f.write(f'\n')
        f.write(f'{new_contentId}\t{new_titleName}\t{new_versionFileUri}')


def main():
    #print('waiting...10 seconds')
    #time.sleep(10)

    ## データ初期化
    error_count = 0
    while True:
        #download_ps5_xml_tsv(sys.argv[1])

        xml_link_dict = {}
        in_file = 'PS5_XML.tsv'
        with open(in_file, encoding='utf-8') as f_in:
            f_in.readline()
            for row in csv.reader(f_in, delimiter='\t'):
                try:
                    title_id = f'{row[0][7:16]}_00'
                    title_name = row[1]
                    xml_link = row[2]
                    xml_link_dict[title_id] = {'XML_LINK': xml_link, 'TITLE_NAME': title_name}
                except IndexError:
                    continue

        in_file = 'XML_HASH.json'
        with open(in_file) as f_in:
            xml_hash_dict = json.load(f_in)

        #snoretoast('PS5 XML Check', 'チェック開始')
        print(f'[{datetime.datetime.now()}] Update check started...')
        running_log('check started')

        ## データ初期化
        updated_title = []
        for title_id in xml_link_dict:
            ## エラーチェック
            if error_count == 4:
                time.sleep(3600)
            if error_count > 4:
                raise Exception('ERROR! Script stopped working with error')

            ## データ初期化
            xml_data = None

            xml_link = xml_link_dict[title_id]['XML_LINK']
            xml_file_name = xml_link.split('/')[-1]
            title_name = xml_link_dict[title_id]['TITLE_NAME']

            print(title_id, title_name+' '*50,'\r', end='')
            time.sleep(1)

            try:
                with urllib.request.urlopen(xml_link) as res:
                    headers = res.getheaders()
                    xml_data = res.read()
                    
                    for i in headers:
                        if i[0] == 'Last-Modified':
                            xml_date = convert_date_format(i[1])
                            break
            except urllib.error.HTTPError as err:
                if err.code == 404:
                    print(f'error {err.code}')
                    continue
                elif err.code == 403:
                    snoretoast('PS5 XML Check', f'ERROR! http_code: {err.code}')
                    print(f'ERROR! http_code: {err.code}')
                    raise
                else:
                    print(f'error {err.code}')
                    #error_log(f'[WARN] ERROR CODE: {err.code}')
                    error_count += 1
                    time.sleep(180)
                    continue
            except urllib.error.URLError as err:
                print(f'error {err}')
                #error_log(err)
                error_count += 1
                time.sleep(180)
                continue
            except http.client.RemoteDisconnected as err:
                print(f'error {err}')
                error_count += 1
                time.sleep(180)
                continue

            ## エラーチェック
            if xml_data:
                error_count = 0
            else:
                continue

            sha256_hash = get_hash_value(xml_data)
            try:
                if sha256_hash == xml_hash_dict[title_id]:
                    continue
            except KeyError:
                pass

            xml_hash_dict[title_id] = sha256_hash
            out_file = 'XML_HASH.json'
            with open(out_file, mode='w') as f_out:
                json.dump(xml_hash_dict, f_out, indent=4)

            os.makedirs(f'PS5_XML/{title_id}/{xml_date}_{sha256_hash}', exist_ok=True)
            out_file = f'PS5_XML/{title_id}/{xml_date}_{sha256_hash}/{xml_file_name}'
            with open(out_file, mode='wb') as f_out:
                f_out.write(xml_data)

            content_id, content_ver, manifest_url, fw_version, delta_url, delta_url_titileId = ps5meta.parse_ps5_xml(xml_data)
            print()
            print(f'title_id    : {title_id}')
            print(f'xml_link    : {xml_link}')
            print(f'title_name  : {title_name}')
            print(f'xml_date    : {xml_date}')
            print(f'content_id  : {content_id}')
            print(f'content_ver : {content_ver}')
            print(f'fw_version  : {fw_version}')
            print(f'delta_url   : {delta_url}')
            print(f'delta_TID   : {delta_url_titileId}')
            print(f'manifest_url: {manifest_url}')
            print()

            #snoretoast('PS5 XML Check', f'{xml_date} | {content_id[0:2]} {title_id} | {content_ver} | {title_name}')
            out_file = 'LOG/update_check.log'
            with open(out_file, mode='a', encoding='utf-8', newline='\r\n') as f_out:
                f_out.write(f'{xml_date} | {title_id} | {content_id} | {content_ver} | {fw_version} | {title_name}\n')

            ## delta_titleID が PS5_XML.tsv 内に存在しない場合は追記
            if delta_url_titileId and delta_url_titileId not in xml_link_dict and delta_url_titileId not in updated_title:
                param_json = ps5meta.get_param_json(delta_url)
                append_new_tittle_id_to_tsv(param_json)
                updated_title.append(delta_url_titileId)

                #ps5meta.print_param(param_json)
                running_log(f'PS5_XML.tsv added {delta_url_titileId}')
                snoretoast('PS5 XML Check', f'PS5_XML.tsv 追加 {delta_url_titileId}')

            updated_title.append(title_id)
        print()
        print(f'[{datetime.datetime.now()}] Update check ended...')
        print('-'*80)
        running_log('check ended')

        if updated_title:
            snoretoast('PS5 XML Check', f'XML 更新')
            git_commit('Update xml')
            running_log('XML Updated')

        wait_interval(1800)


if __name__ == '__main__':
    ## 作業Dirの変更
    dpath = os.path.dirname(os.path.abspath(sys.argv[0]))
    os.chdir(dpath)
    
    os.makedirs(f'LOG', exist_ok=True)

    in_file = 'LOG/error.log'
    if not os.path.isfile(in_file):
        with open(in_file, mode='w') as f:
            pass

    in_file = 'PS5_XML.tsv'
    with open(in_file, mode='rb') as f_in:
        ps5_xml_tsv_hash = get_hash_value(f_in.read())

    try:
        main()
    except Exception as e:
        error_log(traceback.format_exc())
        sys.exit(1)
