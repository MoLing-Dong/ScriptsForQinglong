# # -*- coding: utf-8 -*-
"""
ENV=" "
"""
import os


def get_env(env, default=None):
    """
    青龙环境变量读取，支持将整数，bool类型变量转化为正常的值
    Args:
        env: 字符串，被读取的青龙环境变量
        default: 字符串，如果找不到这个环境变量，返回的默认变量
    Returns:
        result  被格式化的变量
    """
    if env in os.environ and os.environ[env]:
        if os.environ[env] in ["True", "False"]:
            return False if os.environ[env] == "False" else True
        elif os.environ[env].isdigit():
            return int(os.environ[env])
        else:
            return os.environ[env]
    else:
        if default:
            if default in ["True", "False"]:
                return False if default == "False" else True
            elif default.isdigit():
                return int(default)
            else:
                return default
        else:
            return None


if "__name__" == "__main__":
    ENV = get_env("PATH", "test")
    print(ENV)
