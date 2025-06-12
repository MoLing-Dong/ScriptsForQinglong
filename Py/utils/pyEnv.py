import os
import sys
import re
import requests
from datetime import datetime
from urllib.parse import quote


def get_env(env_name: str) -> list[str]:
    """
    获取指定名称的环境变量值，支持从 QLAPI 或系统环境变量中提取。
    @Created by Mol on 2024/02/27
    @param env_name: 环境变量名称（不区分大小写）
    @return: 环境变量值列表（去重、过滤空值）
    """
    env_name = env_name.upper()
    env_values = []

    try:
        # 若 QLAPI 存在（需在外部定义 QLAPI 对象）
        if QLAPI.getEnvs({"searchValue": env_name})["data"]:
            data_list = QLAPI.getEnvs({"searchValue": env_name})["data"]

            env_values = [item["value"] for item in data_list if item["status"] == 0]
            return env_values
    except NameError:
        pass  # 若 QLAPI 未定义，跳过该部分

    raw_value = os.environ.get(env_name, "")
    if raw_value:
        if "&" in raw_value:
            env_values = raw_value.split("&")
        elif "\n" in raw_value:
            env_values = raw_value.split("\n")
        else:
            env_values = [raw_value]

    if "GITHUB" in os.environ:
        print("请勿使用 GitHub Action 运行此脚本，可能导致封号！\n")

    # 去重 + 过滤空字符串
    env_values = list({v.strip() for v in env_values if v.strip()})

    if os.getenv("DEBUG") == "false":
        print("my_module")

    print(f"\n==================== 共 {len(env_values)} 个任务 ====================\n")
    return env_values


def get_ip() -> str | None:
    """
    获取当前公网 IP 地址
    """
    url = "https://www.cip.cc/"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/95.0.4638.69 Safari/537.36"
        )
    }

    try:
        response = requests.get(url, headers=headers, timeout=5)
        ip_match = re.search(
            r"((25[0-5]|2[0-4]\d|1\d{2}|[1-9]?\d)\.){3}"
            r"(25[0-5]|2[0-4]\d|1\d{2}|[1-9]?\d)",
            response.text,
        )
        if ip_match:
            ip = ip_match.group(0)
            print(f"\n当前公网 IP: {ip}")
            return ip
    except requests.RequestException as e:
        print(f"获取 IP 失败: {e}")

    return None


def get_current_activity_script_file_name() -> str:
    """
    获取当前脚本的文件名
    """
    return os.path.basename(sys.argv[0])


def format_date(date: datetime) -> str:
    """
    格式化日期为字符串
    @param date: datetime 对象
    @return: 格式化字符串（例：2025/06/11 15:00:00）
    """
    return date.strftime("%Y/%m/%d %H:%M:%S")
