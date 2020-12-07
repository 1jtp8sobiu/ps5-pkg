#!/usr/bin/env python3
import os
import json
import urllib.request
import urllib.error
import hashlib
import sys
import datetime
import subprocess
import time
import ssl
import csv
ssl._create_default_https_context = ssl._create_unverified_context

def conver_date_format(CURRENT_LASTMODIFIED):
    modified_yyyy = CURRENT_LASTMODIFIED[12:16]
    modified_month = CURRENT_LASTMODIFIED[8:11]
    
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
    
    modified_dd = CURRENT_LASTMODIFIED[5:7]
    modified_hh = CURRENT_LASTMODIFIED[17:19]
    modified_mn = CURRENT_LASTMODIFIED[20:22]
    modified_ss = CURRENT_LASTMODIFIED[23:25]
    
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
        
    print('waiting...')
    count = 0
    while count < 3600 * 1:
        time.sleep(10)
        count += 10
        dt_now = datetime.datetime.now()
        print(dt_now, '\r', end='')
        
    # while True:
    #     time.sleep(10)
    #     
    #     dt_now = datetime.datetime.now()
    #     print(dt_now, '\r', end='')
    #     print()
    #     print(dt_now.strftime('%H'))
    #     if dt_now.strftime('%H') != '05':
    #         continue
    #     print()
    #     break
    time.sleep(10) # スリープ復帰後だった場合のwait

    with open('C:/Settings/running.txt', 'w') as f:
        f.write('1')


def snoretoast(title='Snoretoast', comment='Comment', icon_path=''):
    snoretoast_exe = 'C:/bin/snoretoast/snoretoast.exe'
    if not os.path.isfile(snoretoast_exe):
        raise
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


def main():
    print('waiting...')
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



        
        snoretoast('PS5 XML Check', 'チェック開始')
        start = time.time()
        for title_id in xml_link_dict:
            xml_link = xml_link_dict[title_id]['XML_LINK']
            xml_file_name = xml_link.split('/')[-1]
            title_name = xml_link_dict[title_id]['TITLE_NAME']
            

            try:
                with urllib.request.urlopen(xml_link) as res:
                    headers = res.getheaders()
                    ps5_xml = res.read()
                    
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
                    sys.exit(-1)
            except urllib.error.URLError as err:
                print(f'error {err}')

            print(f'xml link  : {xml_link}')
            print(f'file_name : {xml_file_name}')
            print(f'title_name: {title_name}')
            print(f'xml_date  : {xml_date}')
            print()

            sha256_hash = get_hash_value(ps5_xml)

            try:
                if sha256_hash == xml_hash_dict[title_id]:
                    continue
            except KeyError:
                pass
            xml_hash_dict[title_id] = sha256_hash
            out_file = 'XML_HASH.json'
            with open(out_file, mode='w') as f_out:
                json.dump(xml_hash_dict, f_out)
                    
            os.makedirs(f'PS5_XML/{title_id}/{xml_date}_{sha256_hash}', exist_ok=True)
            out_file = f'PS5_XML/{title_id}/{xml_date}_{sha256_hash}/{xml_file_name}'
            with open(out_file, mode='wb') as f_out:
                f_out.write(ps5_xml)
                
            out_file = 'LOG/update_check.log'
            with open(out_file, mode='a', encoding='utf-8') as f_out:
                f_out.write(f'{xml_date} XML更新 {title_id} {title_name}\n')
            snoretoast('PS5 XML Check', f'XML 更新 {title_id} | {title_name}')
        
        git_commit()
        wait_interval()


if __name__ == '__main__':
    main()

