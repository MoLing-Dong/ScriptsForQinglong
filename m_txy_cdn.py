"""
new Env('腾讯云CDN定时刷新');

0 7-18 * * *  m_txy_cdn.py 
"""

import utils.pyEnv as env
import os


txy_cdn = env.get_env("TXY_CDN")
print(txy_cdn)
