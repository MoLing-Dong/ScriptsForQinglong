import os
import sys
import urllib.parse
import re
from datetime import datetime
import requests


def get_env(env_name):
    """
    @Created by Mol on 2024/02/27
    @description 获取环境变量
    @param {String} env_name 环境变量名称
    """
    # 转为大写
    env_name = env_name.upper()
    environment_variable = ["", ""]  # 初始化空列表
    IP = ""
    print(os.environ.get(env_name, "false"))
    if os.environ.get(env_name, "false"):
        if "&" in os.environ.get(env_name, "false"):
            environment_variable = os.environ.get(env_name, "false").split("&")
        elif "\n" in os.environ.get(env_name, "false"):
            environment_variable = os.environ.get(env_name, "false").split("\n")
        else:
            environment_variable = [os.environ.get(env_name, "false")]

    if "GITHUB" in str(os.environ):
        print(
            "请勿使用 GitHub Action 运行此脚本, 无论你是从你自己的私库还是其他哪里拉取的源代码，都会导致被封号\n"
        )

    # 去重并过滤空值
    environment_variable = list(
        set(filter(lambda item: bool(item), environment_variable))
    )

    if os.getenv("DEBUG") == "false":
        print("my_module")

    print(
        f"\n====================共{len(environment_variable)}个任务=================\n"
    )

    # 对环境变量中包含的中文字符进行编码
    # environment_variable = [urllib.parse.quote(item) for item in environment_variable]

    return environment_variable


def get_ip():
    url = "https://www.cip.cc/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers, timeout=5)
        ip = re.search(
            r"((2(5[0-5]|[0-4]\d))|[0-1]?\d{1,2})(\.((2(5[0-5]|[0-4]\d))|[0-1]?\d{1,2})){3}",
            response.text,
        )
        if ip:
            print
            (f"\n当前公网IP: {ip.group(0)}")
        return ip.group(0) if ip else None
    except requests.RequestException as e:
        print(f"获取IP失败: {e}")
        return None


def get_current_activity_script_file_name():
    return os.path.basename(sys.argv[0])


def format_date(date):
    return date.strftime("%Y/%m/%d %H:%M:%S")
