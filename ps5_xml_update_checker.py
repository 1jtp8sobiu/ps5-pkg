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
import xml.etree.ElementTree as ET
ssl._create_default_https_context = ssl._create_unverified_context


import show_ps5_pkg_metadata


def conver_date_format(lastmodified):
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


def wait_interval():
    # チェック中(1) or 待機中(0)かをテキストに書き出し
    with open('C:/Settings/running.txt', 'w') as f:
        f.write('0')
    
    start = time.time()
    print('waiting interval')
    while time.time()-start < 3600 * 1:
        time.sleep(60)
        print(time.time()-start, '\r', end='')
        
        # check 'PS5_XML.tsv' hash
        if is_ps5_xml_tsv_updated():
            break
    
    print()
    time.sleep(15) # スリープ復帰後だった場合のwait

    with open('C:/Settings/running.txt', 'w') as f:
        f.write('1')


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


def git_commit():
    cmd = ['git', 'add', '.']
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print(proc.stdout.decode('utf8'))
    
    cmd = ['git', 'commit', '-a', '-m', 'Update xml']
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print(proc.stdout.decode('utf8'))
    
    cmd = ['git', 'push', 'origin', 'master']
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print(proc.stdout.decode('utf8'))


def download_ps5_xml_tsv(url):
    with urllib.request.urlopen(url) as res, open('PS5_XML.tsv', mode='wb') as f:
        f.write(res.read())


def parse_ps5_xml(xml_data):
    root = ET.fromstring(xml_data)
    tag_index = len(root[0]) - 1
    
    content_id = root[0].attrib['content_id']
    content_ver = root[0][tag_index].attrib['content_ver']
    manifest_url = root[0][tag_index].attrib['manifest_url']
    system_ver = root[0][tag_index].attrib['system_ver']
    
    try:
        delta_url = root[0][0].attrib['delta_url']
        delta_url_titileId = delta_url.split('/')[-1][7:19]
    except KeyError:
        delta_url = None
        delta_url_titileId = None
    
    system_ver_hex = f'{int(system_ver):x}'
    fw_version = '0' + system_ver_hex[0] + '.' + system_ver_hex[1:3] + '.' + system_ver_hex[3:5] + '.' + system_ver_hex[5:7]
    
    return content_id, content_ver, manifest_url, fw_version, delta_url, delta_url_titileId


def append_new_tittle_id_to_tsv(param_json):
    new_contentId = param_json['contentId']
    new_defaultLanguage = param_json['localizedParameters']['defaultLanguage']
    new_titleName = param_json['localizedParameters'][new_defaultLanguage]['titleName']
    new_versionFileUri = param_json['versionFileUri'].strip()

    with open('PS5_XML.tsv', mode='a', encoding='utf-8') as f:
        f.write(f'\n')
        f.write(f'{new_contentId}\t{new_titleName}\t{new_versionFileUri}')


def main():
    os.makedirs(f'LOG', exist_ok=True)

    print('waiting...10 seconds')
    time.sleep(10)
    while True:
        #download_ps5_xml_tsv(sys.argv[1])
    
        xml_link_dict = {}
        in_file = 'PS5_XML.tsv'
        with open(in_file, encoding='utf-8') as f_in:
            f_in.readline()
            for row in csv.reader(f_in, delimiter='\t'):
                title_id = f'{row[0][7:16]}_00'
                title_name = row[1]
                xml_link = row[2]
                xml_link_dict[title_id] = {'XML_LINK': xml_link, 'TITLE_NAME': title_name}

        in_file = 'XML_HASH.json'
        with open(in_file) as f_in:
            xml_hash_dict = json.load(f_in)

        # snoretoast('PS5 XML Check', 'チェック開始')
        print('Update check started...')
        
        for title_id in xml_link_dict:
            updated_title = []
            
            xml_link = xml_link_dict[title_id]['XML_LINK']
            xml_file_name = xml_link.split('/')[-1]
            title_name = xml_link_dict[title_id]['TITLE_NAME']

            time.sleep(3)
            try:
                with urllib.request.urlopen(xml_link) as res:
                    headers = res.getheaders()
                    xml_data = res.read()
                    
                    for i in headers:
                        if i[0] == 'Last-Modified':
                            xml_date = conver_date_format(i[1])
                            break
            except urllib.error.HTTPError as err:
                if err.code == 404:
                    print(f'error {err.code}')
                    continue
                elif err.code == 403:
                    snoretoast('PS5 XML Check', f'ERROR! http_code: {err.code}')
                    print(f'ERROR! http_code: {err.code}')
                    sys.exit(-1)
            except urllib.error.URLError as err:
                print(f'error {err}')

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

            content_id, content_ver, manifest_url, fw_version, delta_url, delta_url_titileId = show_ps5_pkg_metadata.parse_ps5_xml(xml_data)
            print(f'xml link    : {xml_link}')
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
            with open(out_file, mode='a', encoding='utf-8') as f_out:
                f_out.write(f'{xml_date} | {title_id} | {content_id} | {content_ver} | {fw_version} | {title_name}\n')

            # delta_titleID が PS5_XML.tsv 内に存在しない場合は追記
            if delta_url_titileId and delta_url_titileId not in xml_link_dict:
                param_json = show_ps5_pkg_metadata.get_param_json(delta_url)
                append_new_tittle_id_to_tsv(param_json)
                
                #show_ps5_pkg_metadata.print_param(param_json)
                snoretoast('PS5 XML Check', f'PS5_XML.tsv 追加 {delta_url_titileId}')
            
            updated_title.append(title_id)
        print('Update check ended...')
        if updated_title:
            snoretoast('PS5 XML Check', f'XML 更新')
        git_commit()
        wait_interval()


if __name__ == '__main__':
    in_file = 'PS5_XML.tsv'
    with open(in_file, mode='rb') as f_in:
        ps5_xml_tsv_hash = get_hash_value(f_in.read())
        
    main()

