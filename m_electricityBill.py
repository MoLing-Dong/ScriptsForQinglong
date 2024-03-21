"""
new Env('宿舍电费');
EBILL={
    "userXq": "",
    "userFj": "",
    "payType": "",
}
0 7,18 * * *  m_electricityBill.py
"""

import json
from utils import pyEnv
import requests


def get_electricityBill(user_info_list):
    user_info_list = json.loads(user_info_list[0])
    userXq = user_info_list.get("userXq", "")
    userFj = user_info_list.get("userFj", "")
    payType = user_info_list.get("payType", "")
    url = "http://www.dianzichaxun.com/Home/GetElectricityBill"
    headers = {
        "Content-Type": "application/json",
    }
    data = {
        "userXq": userXq,
        "userFj": userFj,
        "payType": payType,
    }
    response = requests.post(url, headers=headers, data=json.dumps(data))
    return response.json()


if __name__ == "__main__":
    user_info_list = pyEnv.get_env("EBILL")
    # 是否是符合json
    message = get_electricityBill(user_info_list)
    print(message)
