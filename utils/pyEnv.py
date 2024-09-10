from loguru import logger
import os
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
    env_name = env_name.upper().strip()

    environment_variable = ["", ""]  # 初始化空列表
    IP = ""

    if os.getenv(env_name):
        if "&" in os.getenv(env_name):
            environment_variable = os.getenv(env_name).split("&")
        elif "\n" in os.getenv(env_name):
            environment_variable = os.getenv(env_name).split("\n")
        else:
            environment_variable = [os.getenv(env_name)]

    if "GITHUB" in str(os.environ):
        logger.warning(
            "请勿使用 GitHub Action 运行此脚本, 无论你是从你自己的私库还是其他哪里拉取的源代码，都会导致我被封号\n"
        )

    # 去重并过滤空值
    environment_variable = list(
        set(filter(lambda item: bool(item), environment_variable))
    )

    if os.getenv("DEBUG") == "false":
        logger.disable("my_module")

    logger.info(
        f"\n====================共{len(environment_variable)}个任务=================\n"
    )
    logger.info(
        f"============脚本执行时间：{format_date(datetime.utcnow())}=============\n"
    )

    # 对环境变量中包含的中文字符进行编码
    environment_variable = [urllib.parse.quote(item) for item in environment_variable]

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
            logger.info(f"\n当前公网IP: {ip.group(0)}")
        return ip.group(0) if ip else None
    except requests.RequestException as e:
        logger.error(f"获取IP失败: {e}")
        return None


def get_current_activity_script_file_name():
    import sys
    import os

    return os.path.basename(sys.argv[0])


def format_date(date):
    return date.strftime("%Y/%m/%d %H:%M:%S")
