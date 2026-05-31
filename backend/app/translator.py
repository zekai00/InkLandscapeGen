# /app/image_router.py
import hashlib
import os
import json
import random

import requests

BAIDU_TRANSLATE_URL = "https://fanyi-api.baidu.com/api/trans/vip/translate"

APP_ID = os.getenv("BAIDU_TRANSLATE_APP_ID", "")
API_KEY = os.getenv("BAIDU_TRANSLATE_API_KEY", "")


def make_md5(s, encoding='utf-8'):
    return hashlib.md5(s.encode(encoding)).hexdigest()


def translate(text: str):
    if not APP_ID or not API_KEY:
        return text

    print("im in translate")
    from_lang = 'zh'  # 中文
    to_lang = 'en'  # 英文
    salt = str(random.randint(32768, 65536))

    # 签名：appid+q+salt+密钥 的MD5值
    sign = make_md5(APP_ID + text + salt + API_KEY)

    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
    }

    # 构建请求参数
    data = {
        'q': text,
        'from': from_lang,
        'to': to_lang,
        'appid': APP_ID,
        'salt': salt,
        'sign': sign,
    }

    print("prepare to do requests")
    try:
        response = requests.get(BAIDU_TRANSLATE_URL, params=data, timeout=20)
        # 如果状态码不是200，也认为是请求失败
        if response.status_code != 200:
            print(f"请求失败，状态码：{response.status_code}")
        else:
            print(response.json())  # 请求成功，打印响应的JSON
    except requests.exceptions.RequestException as e:
        # 捕获所有请求相关的错误
        print(f"请求出错：{e}")
        return text

    print("prepare to get result")
    result = json.loads(response.text)

    # 检查是否存在错误码
    if 'error_code' in result:
        error_msg = result.get('error_msg', 'No error message provided')
        return f"Error: {result['error_code']} - {error_msg}"

    if 'trans_result' in result:
        return result['trans_result'][0]['dst']
    else:
        return "Error: Unable to translate, unknown error."

# 使用示例
# print(translate("需要翻译的文本", "你的APPID", "你的密钥"))
