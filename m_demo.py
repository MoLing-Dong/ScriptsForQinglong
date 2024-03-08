# # -*- coding: utf-8 -*-
# 从 "./utils/pyEnv.py"导入get_env函数
from utils.pyEnv import get_env

if __name__ == "__main__":
    # 获取环境变量
    env = get_env("SU_SHE")
    print(env)
