import os
from datetime import datetime, timedelta
import urllib.parse

# 定义全局变量
environmentVariable = []


def custom_print(*args, **kwargs):
    """自定义打印函数，根据DEBUG环境变量决定是否打印"""
    if os.getenv("DEBUG") != "false":
        print(*args, **kwargs)


def get_env(envName: str) -> list:
    global environmentVariable
    envName = envName.upper()
    if envName in os.environ:
        custom_print(
            f"检测到环境变量{envName}存在，开始解析环境变量"
        )  # 使用自定义的打印函数
        if "&" in os.environ[envName]:
            environmentVariable = os.environ[envName].split("&")
        elif "\n" in os.environ[envName]:
            environmentVariable = os.environ[envName].split("\n")
        else:
            environmentVariable = [os.environ.get(envName, "")]
    else:
        environmentVariable = []

    if any("GITHUB" in key for key in os.environ):
        custom_print("请勿使用github action运行此脚本...")

    # 过滤空字符串并去重
    environmentVariable = list(set(filter(None, environmentVariable)))

    custom_print(
        f"\n====================共{len(environmentVariable)}个任务=================\n"
    )

    # 调整为当前时区的时间
    current_time = datetime.now() + timedelta(hours=8)
    custom_print(
        f"============脚本执行时间：{current_time.strftime('%Y-%m-%d %H:%M:%S')}=============\n"
    )

    
    return environmentVariable
