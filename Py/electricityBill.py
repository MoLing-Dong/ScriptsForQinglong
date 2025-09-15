"""
宿舍电费
name: 宿舍电费查询
定时规则
cron: 0 7,20 * * *

ELECTRICITY_BILL = 
{
    'userXq': '山东华宇工学院',
    'userFj': '1501018',
    'payType': '1',
}

"""

import json
import re
import utils.pyEnv as env

import requests
from requests.exceptions import RequestException


# 常量定义
URL = "http://df.huayu.edu.cn/wxapp/pay/queryElectricity"
COOKIES = {
    "JSESSIONID": "7BADF1EB7FD02E56B8DCEA08C04E40A5",
}
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 NetType/WIFI MicroMessenger/7.0.20.1781(0x6700143B) WindowsWechat(0x63090b19) XWEB/11253 Flue",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Origin": "http://df.huayu.edu.cn",
    "Referer": "http://df.huayu.edu.cn/wxapp/api/oauth",
    "Accept-Language": "zh-CN,zh;q=0.9",
}


def sanitize_json(json_str):
    """修复各种JSON格式问题"""
    try:
        # 首先尝试直接解析
        return json.loads(json_str)
    except json.JSONDecodeError:
        try:
            # 清理字符串
            cleaned = json_str.strip()
            
            # 修复单引号为双引号
            cleaned = re.sub(r"'([^']*)':", r'"\1":', cleaned)
            cleaned = re.sub(r":\s*'([^']*)'", r': "\1"', cleaned)
            
            # 修复末尾多逗号
            cleaned = re.sub(r",\s*}", "}", cleaned)
            cleaned = re.sub(r",\s*]", "]", cleaned)
            
            # 修复属性名没有引号的问题
            cleaned = re.sub(r"(\w+):", r'"\1":', cleaned)
            
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            print(f"JSON修复失败，原始字符串: {json_str}")
            raise e


def fetch_electricity_info(account_data: dict):
    try:
        response = requests.post(
            URL, cookies=COOKIES, headers=HEADERS, data=account_data, verify=False
        )
        response.raise_for_status()
    except RequestException as e:
        print(f"[{account_data.get('userFj', '未知')}]: 请求失败: {e}")
        return None

    try:
        response_json = response.json()["message"]
    except (json.JSONDecodeError, KeyError) as e:
        print(f"[{account_data.get('userFj', '未知')}]: 响应解析失败: {e}")
        return None

    info = (
        f"宿舍号：{response_json.get('room', 'N/A')}\n"
        f"剩余免费电量：{response_json.get('freeElec', 'N/A')} 度\n"
        f"总电量：{response_json.get('plusElec', 'N/A')} 度\n"
        f"剩余电费：{response_json.get('feeElec', 'N/A')} 元\n"
        f"状态：{response_json.get('status', 'N/A')}"
    )
    return info


if __name__ == "__main__":
    all_data = env.get_env("ELECTRICITY_BILL")

    if not all_data:
        print("未获取到任何账户配置")
        exit(1)

    for i, raw in enumerate(all_data):
        print(raw)
        try:
            account = sanitize_json(raw)
        except json.JSONDecodeError as e:
            print(f"[账户{i+1}] JSON 解析失败: {e}")
            continue

        print(f"\n==== 查询第 {i+1} 个账户 ====")
        result = fetch_electricity_info(account)
        if result:
            print(result)
            QLAPI.notify(f"宿舍电费查询 ", result)

        else:
            print("查询失败。")
