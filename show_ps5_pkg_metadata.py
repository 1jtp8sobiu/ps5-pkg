#!/usr/bin/env python3

### Extract param.json from the PS5 pkg link and display some information.
### 
### [Usage] show_ps5_pkg_metadata.py [-h] [--output] [URL of PS5 pkg (version.xml / .json / .DP.pkg / .sc.pkg)]
### [Examples]
### show_ps5_pkg_metadata.py https://sgst.prod.dl.playstation.net/sgst/prod/00/np/PPSA01280_00/d8ec167a-59da-4e54-8e2c-1161c706516a-version.xml
### show_ps5_pkg_metadata.py http://gst.prod.dl.playstation.net/gst/prod/00/PPSA01280_00/app/pkg/14/f_79cafe1a822dd62c55ebb4d08844deafe89d9e42366ddd8ade1d54de8f2f8eac/IP9100-PPSA01280_00-SFSRELE000000100-DP.pkg
### show_ps5_pkg_metadata.py https://sgst.prod.dl.playstation.net/sgst/prod/00/PPSA01280_00/app/info/13/f_504bd9d060d0861ae60bc680146dba2093041c29da446558392446d6eecc7330/IP9100-PPSA01280_00-SFSRELE000000100_sc.pkg
### show_ps5_pkg_metadata.py --output https://sgst.prod.dl.playstation.net/sgst/prod/00/np/PPSA01280_00/d8ec167a-59da-4e54-8e2c-1161c706516a-version.xml

import json
import urllib.request
import urllib.error
import sys
import ssl
import pprint
import argparse
import xml.etree.ElementTree as ET
ssl._create_default_https_context = ssl._create_unverified_context


def get_param_json(url, output=False):
    # URLの正当性を検証
    url = url.strip()
    
    #if 'gst.prod.dl.playstation.net' not in url:
    #    print(f'ERROR! Not PS5 pkg link')
    #    sys.exit(-1)

    if 'version.xml' in url:
        try:
            with urllib.request.urlopen(url) as res:
                xml_data = res.read()
        except urllib.error.HTTPError as err:
            if err.code == 404:
                print(f'error {err.code}')
                return
            elif err.code == 403:
                snoretoast('PS5 XML Check', f'ERROR! http_code: {err.code}')
                print(f'ERROR! http_code: {err.code}')
                sys.exit(-1)
        except urllib.error.URLError as err:
            print(f'error {err}')
            return 
        url = parse_ps5_xml(xml_data)[2]
        url = url.replace('.json', '_sc.pkg')

    if '.json' in url:
        url = url.replace('.json', '_sc.pkg')

    if 'DP.pkg' not in url and 'sc.pkg' not in url:
        print(f'ERROR! Not PS5 pkg link')
        sys.exit(-1)

    # ファイルを64KBのみダウンロード
    chunk_size = 1024 * 64
    try:
        with urllib.request.urlopen(url) as res:
            chunk = res.read(chunk_size)
    except urllib.error.HTTPError as err:
        if err.code == 404:
            print(f'error {err.code}')
        elif err.code == 403:
            snoretoast('PS5 XML Check', f'ERROR! http_code: {err.code}')
            print(f'ERROR! http_code: {err.code}')
            sys.exit(-1)
    except urllib.error.URLError as err:
        print(f'error {err}')

    json_data = extract_param_json(chunk)
    
    if output:
        out_file = 'param.json'
        with open(out_file, mode='wb') as f:
            f.write(json_data)
    
    return json.loads(json_data)


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
    fw_version = '0' + '.'.join([system_ver_hex[0], system_ver_hex[1:3], system_ver_hex[3:5], system_ver_hex[5:7]])
    
    return content_id, content_ver, manifest_url, fw_version, delta_url, delta_url_titileId


def extract_param_json(data):
    #  "param.json" の位置を探す
    find_str = 'param.json'.encode()
    temp_position = data.find(find_str)
    
    find_str = b'\x7b\x0d\x0a'
    start_position = data.find(find_str, temp_position)
    
    find_str = 'version.xml'.encode()
    temp_position = data.find(find_str)
    
    # 0x7D 0D 0A json終端部分を探す
    find_str = b'\x7d\x0d\x0a'
    end_position = data.find(find_str, temp_position) + 3
    
    json_data = data[start_position:end_position]
    return json_data


def print_param(param_json):
    print('-'*100)
    pprint.pprint(param_json)

    param_json = adjust_param_value(param_json)
    target_keys = ['titleId',
                    'contentId',
                    'defaultLanguage',
                    'titleName',
                    'applicationCategoryType',
                    'applicationDrmType',
                    'attribute',
                    'attribute2',
                    'attribute3',
                    'userDefinedParam1',
                    'userDefinedParam2',
                    'userDefinedParam3',
                    'userDefinedParam4',
                    'contentVersion',
                    'targetContentVersion',
                    'masterVersion',
                    'requiredSystemSoftwareVersion',
                    'sdkVersion',
                    'creationDate',
                    'versionFileUri']

    print('-'*100)
    for key in target_keys:
        try:
            value = param_json[key]
        except KeyError:
            value = None
        
        print(f'{key: <32} = {value}')
    print('-'*100)


def adjust_param_value(param_json):
    # Sub Keyの取得
    param_json['defaultLanguage'] = param_json['localizedParameters']['defaultLanguage']
    param_json['titleName'] = param_json['localizedParameters'][param_json['defaultLanguage']]['titleName']
    param_json['creationDate'] =  param_json['pubtools']['creationDate']
    param_json['toolVersion'] = param_json['pubtools']['toolVersion']

    # 値の変換
    param_json['versionFileUri'] = param_json['versionFileUri'].strip()
    param_json['titleId'] = param_json['titleId'] + '_00'
    
    fw = param_json['requiredSystemSoftwareVersion']
    param_json['requiredSystemSoftwareVersion'] = '.'.join([fw[2:4], fw[4:6], fw[6:8], fw[8:10]]) + '-' + '.'.join([fw[10:12], fw[12:14], fw[14:16], fw[16:17], fw[17:18]])

    try:
        param_json['attribute'] = hex(param_json['attribute'])
        param_json['attribute2'] = hex(param_json['attribute2'])
        param_json['attribute3'] = hex(param_json['attribute3'])
        
        sdk = param_json['sdkVersion']
        param_json['sdkVersion'] = '.'.join([sdk[2:4], sdk[4:6], sdk[6:8], sdk[8:10]]) + '-' + '.'.join([sdk[10:12], sdk[12:14], sdk[14:16], sdk[16:17], sdk[17:18]])
    except Exception:
        pass
    
    return param_json


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Show PS5 Pkg Metadata')
    parser.add_argument('url', help='URL of PS5 pkg (version.xml / .json / .DP.pkg / _sc.pkg)')
    parser.add_argument('--output', action='store_true', help='Output param.json file to the same folder in the script')
    args = parser.parse_args()

    param_json = get_param_json(args.url, args.output)
    print_param(param_json)