# -*- coding: utf-8 -*-
"""
new Env('腾讯云CDN定时刷新');
TXY_CDN = secret_id#secret_key#urlList
urlList = url1,url2,url3
*/10 7-20 * * * m_txy_cdn.py 
"""
import hashlib
import hmac
import json
import sys
import time
from datetime import datetime

if sys.version_info[0] <= 2:
    from httplib import HTTPSConnection
else:
    from http.client import HTTPSConnection

import utils.pyEnv as env

txy_cdn = env.get_env("TXY_CDN")


def sign(key, msg):
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def main(secret_id, secret_key, urlList):
    urlList = json.dumps(urlList)
    token = ""
    service = "cdn"
    host = "cdn.tencentcloudapi.com"
    region = ""
    version = "2018-06-06"
    action = "PurgeUrlsCache"
    # payload = f'{"Urls":{urlList}}' # 不能这样写，会报错!!!
    payload = f'{{"Urls":{urlList}}}'
    params = json.loads(payload)
    endpoint = "https://cdn.tencentcloudapi.com"
    algorithm = "TC3-HMAC-SHA256"
    timestamp = int(time.time())
    date = datetime.utcfromtimestamp(timestamp).strftime("%Y-%m-%d")

    # ************* 步骤 1：拼接规范请求串 *************
    http_request_method = "POST"
    canonical_uri = "/"
    canonical_querystring = ""
    ct = "application/json; charset=utf-8"
    canonical_headers = "content-type:%s\nhost:%s\nx-tc-action:%s\n" % (
        ct,
        host,
        action.lower(),
    )
    signed_headers = "content-type;host;x-tc-action"
    hashed_request_payload = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    canonical_request = (
        http_request_method
        + "\n"
        + canonical_uri
        + "\n"
        + canonical_querystring
        + "\n"
        + canonical_headers
        + "\n"
        + signed_headers
        + "\n"
        + hashed_request_payload
    )

    # ************* 步骤 2：拼接待签名字符串 *************
    credential_scope = date + "/" + service + "/" + "tc3_request"
    hashed_canonical_request = hashlib.sha256(
        canonical_request.encode("utf-8")
    ).hexdigest()
    string_to_sign = (
        algorithm
        + "\n"
        + str(timestamp)
        + "\n"
        + credential_scope
        + "\n"
        + hashed_canonical_request
    )

    # ************* 步骤 3：计算签名 *************
    secret_date = sign(("TC3" + secret_key).encode("utf-8"), date)
    secret_service = sign(secret_date, service)
    secret_signing = sign(secret_service, "tc3_request")
    signature = hmac.new(
        secret_signing, string_to_sign.encode("utf-8"), hashlib.sha256
    ).hexdigest()

    # ************* 步骤 4：拼接 Authorization *************
    authorization = (
        algorithm
        + " "
        + "Credential="
        + secret_id
        + "/"
        + credential_scope
        + ", "
        + "SignedHeaders="
        + signed_headers
        + ", "
        + "Signature="
        + signature
    )

    # ************* 步骤 5：构造并发起请求 *************
    headers = {
        "Authorization": authorization,
        "Content-Type": "application/json; charset=utf-8",
        "Host": host,
        "X-TC-Action": action,
        "X-TC-Timestamp": timestamp,
        "X-TC-Version": version,
    }
    if region:
        headers["X-TC-Region"] = region
    if token:
        headers["X-TC-Token"] = token

    try:
        req = HTTPSConnection(host)
        req.request("POST", "/", headers=headers, body=payload.encode("utf-8"))
        resp = req.getresponse()
        print(resp.read())
    except Exception as err:
        print(err)


def get_txy_cdn():
    txy_cdn_list = env.get_env("TXY_CDN")
    if txy_cdn_list:
        for i in txy_cdn_list:
            txy_cdn = i.split("#")
            secret_id = txy_cdn[0]
            secret_key = txy_cdn[1]
            urlList = txy_cdn[2]
            urlList = urlList.split(",")
            main(secret_id, secret_key, urlList)


get_txy_cdn()
