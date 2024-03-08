import os
import re
from datetime import datetime, timedelta
import urllib.parse


environmentVariable = [
    "",
    "",
]


def get_env(envName: str) -> list:
    envName = envName.upper()
    if envName in os.environ:
        if "&" in os.environ[envName]:
            environmentVariable = os.environ[envName].split("&")
        elif "\n" in os.environ[envName]:
            environmentVariable = os.environ[envName].split("\n")
    else:
        environmentVariable = [os.environ[envName]]

    if any("GITHUB" in key for key in os.environ):
        print(
            "请勿使用github action运行此脚本,无论你是从你自己的私库还是其他哪里拉取的源代码，都会导致我被封号\n"
        )

    # 过滤空字符串并去重
    environmentVariable = list(set(filter(None, environmentVariable)))

    if os.getenv("DEBUG") == "false":
        # 重定义print函数以禁用打印
        def print(*args, **kwargs):
            pass

    print(
        f"\n====================共{len(environmentVariable)}个任务=================\n"
    )

    # 调整为当前时区的时间
    current_time = datetime.now() + timedelta(hours=8)
    print(
        f"============脚本执行时间：{current_time.strftime('%Y-%m-%d %H:%M:%S')}=============\n"
    )

    for i in range(len(environmentVariable)):
        environmentVariable[i] = urllib.parse.quote(environmentVariable[i], safe="")
    return environmentVariable
