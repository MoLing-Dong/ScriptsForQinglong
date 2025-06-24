"""
推歌参谋
name: 推歌参谋数据查询
定时规则
cron: 0 8,12,23 * * *
变量名：WYY_YYR  多账号换行
格式：手机号:密码:cookie
示例：13800138000:123456:WYY_YYR_COOKIE
注意：cookie可以不填，若不填则会自动登录获取cookie

@site: https://st.music.163.com/g/push-assiant
"""

import json
import os
import re
import hashlib
import requests
import execjs
from datetime import datetime, timedelta
from operator import itemgetter
from loguru import logger
import utils.pyEnv as env

# 日志配置
logger.remove()
logger.add("./log/musician_api.log", rotation="50 MB", level="DEBUG")
logger.add(lambda msg: print(msg, end=""), format="{message}", level="INFO")

# 请求头配置
HEADERS = {
    "accept": "application/json, text/javascript",
    "accept-language": "zh-CN,zh;q=0.9",
    "cache-control": "no-cache",
    "content-type": "application/x-www-form-urlencoded",
    "origin": "https://music.163.com",
    "pragma": "no-cache",
    "referer": "https://music.163.com/musician/artist/home",
    "sec-ch-ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "x-requested-with": "XMLHttpRequest",
}


def compile_js(js_path: str) -> any:
    """编译 JavaScript 加密文件"""
    try:
        with open(js_path, "r", encoding="utf-8") as f:
            js_content = f.read()
        return execjs.compile(js_content)
    except Exception as e:
        logger.error(f"加载 JavaScript 文件失败: {e}")
        raise


def get_encrypted_data(js_compiled: any, params: dict[str, str]) -> dict[str, str]:
    """生成加密请求参数"""
    try:
        result = js_compiled.call("getData", params)
        return {"params": result["encText"], "encSecKey": result["encSecKey"]}
    except Exception as e:
        logger.error(f"执行 JavaScript 加密失败: {e}")
        raise


def create_session(cookies: str) -> requests.Session:
    """创建带 Cookie 的 Session"""
    session = requests.Session()
    session.headers.update(HEADERS)
    session.headers.update({"cookie": cookies})
    return session


def login_user(js_compiled: any, phone: str, password: str) -> str:
    """用户登录获取 Cookie"""
    try:
        # 密码使用MD5加密
        encrypted_pwd = hashlib.md5(password.encode("utf-8")).hexdigest()

        # 生成登录参数
        login_params = {
            "phone": phone,
            "password": encrypted_pwd,
            "rememberLogin": "true",
        }
        encrypted_data = get_encrypted_data(js_compiled, login_params)

        # 发送登录请求
        response = requests.post(
            "https://music.163.com/weapi/login/cellphone",
            headers=HEADERS,
            data=encrypted_data,
        )
        response.raise_for_status()

        # 检查登录结果
        login_result = response.json()
        if login_result.get("code") != 200:
            raise Exception(f"登录失败: {login_result.get('message')}")

        # 提取Cookie
        cookie_dict = requests.utils.dict_from_cookiejar(response.cookies)
        cookie_str = "; ".join([f"{k}={v}" for k, v in cookie_dict.items()])
        logger.success(f"用户 {phone} 登录成功")
        return cookie_str

    except Exception as e:
        logger.error(f"用户 {phone} 登录失败: {str(e)}")
        raise


def get_account_info(session: requests.Session, js_compiled: any) -> int:
    """获取用户账号信息"""
    try:
        # 获取CSRF token
        csrf_token = re.search(r"__csrf=([^;]+)", session.headers["cookie"])
        if not csrf_token:
            raise ValueError("未找到CSRF token")

        params = {"csrf_token": csrf_token.group(1)}
        encrypted_data = get_encrypted_data(js_compiled, params)

        # 获取账户信息
        response = session.post(
            "https://interface.music.163.com/api/nuser/account/get", data=encrypted_data
        )
        response.raise_for_status()

        account_info = response.json()
        account_id = account_info.get("account", {}).get("id")
        if not account_id:
            raise ValueError("未获取到账户ID")

        logger.info(f"当前用户 ID: {account_id}")
        return account_id

    except Exception as e:
        logger.error(f"获取账户信息失败: {str(e)}")
        raise


def get_musician_data(
    session: requests.Session, js_compiled: any, account_id: int
) -> dict[str, any]:
    """获取音乐人数据"""
    try:
        # 获取CSRF token
        csrf_token = re.search(r"__csrf=([^;]+)", session.headers["cookie"])
        if not csrf_token:
            raise ValueError("未找到CSRF token")

        # 转换用户ID到艺术家ID
        id_trans_params = {
            "id": account_id,
            "sourceIdType": "userId",
            "targetIdType": "artistId",
            "csrf_token": csrf_token.group(1),
        }
        encrypted_data = get_encrypted_data(js_compiled, id_trans_params)

        session.post(
            "https://interface.music.163.com/weapi/push-song-advisor/open/api/id/trans",
            data=encrypted_data,
        )

        # 获取音乐人信息
        params = {"csrf_token": csrf_token.group(1)}
        encrypted_data = get_encrypted_data(js_compiled, params)

        response = session.post(
            "https://music.163.com/weapi/nmusician/entrance/user/musician/info/get",
            data=encrypted_data,
        )
        response.raise_for_status()

        musician_info = response.json()
        artist_name = musician_info.get("data", {}).get("artistName", "未知艺术家")
        logger.info(f"音乐人名称: {artist_name}")

        # 获取统计数据
        response = session.post(
            "https://music.163.com/weapi/creator/musician/statistic/data/overview/get",
            data=encrypted_data,
        )
        response.raise_for_status()

        stats = response.json()
        daily_play = stats.get("data", {}).get("playCount", 0)
        total_play = stats.get("data", {}).get("totalPlayCount", 0)
        logger.info(f"昨日播放: {daily_play}, 总播放: {total_play}")

        # 获取收入数据
        response = session.post(
            "https://music.163.com/weapi/nmusician/workbench/creator/wallet/overview",
            data=encrypted_data,
        )
        response.raise_for_status()

        income = response.json()
        monthly_income = income.get("data", {}).get("monthAmount", 0)
        daily_income = income.get("data", {}).get("dailyAmount", 0)
        logger.info(f"月收入: {monthly_income}, 日收入: {daily_income}")

        return {
            "artist_name": artist_name,
            "daily_play": daily_play,
            "total_play": total_play,
            "monthly_income": monthly_income,
            "daily_income": daily_income,
        }

    except Exception as e:
        logger.error(f"获取音乐人数据失败: {str(e)}")
        raise


def get_song_data(session: requests.Session, artist_id: int) -> dict[str, any]:
    """获取歌曲数据"""
    try:
        # 计算日期
        today = datetime.now()
        yesterday = today - timedelta(days=1)

        # 请求参数
        json_data = {
            "page_num": 1,
            "artist_id": artist_id,
            "dt": yesterday.strftime("%Y-%m-%d"),
            "page_size": 200,
            "order_field": "today_play_cnt",
            "order_direction": "desc",
            "use_total_num": 1,
        }

        # 发送请求
        session.headers.update({"content-type": "application/json"})
        response = session.post(
            "https://interface.music.163.com/api/push-song-advisor/open/api/data-service/advisor/real_time_song_list",
            json=json_data,
        )
        response.raise_for_status()

        data = response.json().get("data", {})
        total_num = data.get("total_num", 0)
        all_songs = data.get("data", [])

        # 计算总页数
        page_size = 200
        total_pages = (total_num + page_size - 1) // page_size

        # 获取所有页面数据
        for page_num in range(2, total_pages + 1):
            json_data["page_num"] = page_num
            response = session.post(
                "https://interface.music.163.com/api/push-song-advisor/open/api/data-service/advisor/real_time_song_list",
                json=json_data,
            )
            response.raise_for_status()
            page_data = response.json().get("data", {}).get("data", [])
            all_songs.extend(page_data)
        # 输出每首歌曲的今日播放量
        for song in all_songs:
            song["today_play_cnt"] = song.get("today_play_cnt", 0)
            song["yesterday_play_cnt"] = song.get("yesterday_play_cnt", 0)
            song["thumbnails"] = song.get("thumbnails", 0)
            # 打印具体信息
            logger.info(
                f"歌曲: {song.get('song_name', '未知歌曲')}, "
                f"今日播放: {song.get('today_play_cnt', 0)}, "
                f"昨日播放: {song.get('yesterday_play_cnt', 0)}, "
                f"实时数据: {song.get('thumbnails', 0)}"
            )
        # 计算总播放量
        today_play_total = sum(song.get("today_play_cnt", 0) for song in all_songs)
        logger.info(f"歌曲总数: {len(all_songs)}, 今日播放总量: {today_play_total}")

        # 按播放量排序
        sorted_songs = sorted(all_songs, key=itemgetter("today_play_cnt"), reverse=True)

        return {
            "total_songs": len(all_songs),
            "today_play_total": today_play_total,
            "songs": sorted_songs,
        }

    except Exception as e:
        logger.error(f"获取歌曲数据失败: {str(e)}")
        raise


def format_report(
    user_index: int, account_id: int, musician_data: dict, song_data: dict
) -> str:
    """生成报告"""
    report = [
        f"用户 #{user_index} 报告",
        f"账户 ID: {account_id}",
        f"音乐人名称: {musician_data['artist_name']}",
        f"昨日播放量: {musician_data['daily_play']}",
        f"总播放量: {musician_data['total_play']}",
        f"月收入: {musician_data['monthly_income']}",
        f"日收入: {musician_data['daily_income']}",
        f"歌曲总数: {song_data['total_songs']}",
        f"今日播放总量: {song_data['today_play_total']}",
        "",
        "歌曲播放排行:",
    ]

    # 添加歌曲信息
    for i, song in enumerate(song_data["songs"], 1):
        song_info = (
            f"{i}. {song.get('song_name', '未知歌曲')}: "
            f"今日播放 {song.get('today_play_cnt', 0)}, "
            f"昨日播放 {song.get('yesterday_play_cnt', 0)}, "
            f"实时数据 {song.get('thumbnails', 0)}"
        )
        report.append(song_info)

    return "\n".join(report)

def validate_cookie(session: requests.Session) -> bool:
    """验证 Cookie 是否有效"""
    try:
        # 尝试访问一个需要登录的接口
        test_url = "https://interface.music.163.com/api/nuser/account/get"
        response = session.post(test_url, data={"csrf_token": ""})
        logger.info(f"Cookie 验证成功: {json.loads(response.text).get('code')}")
        return response.json().get("code") != 301
    except Exception as e:
        logger.error(f"验证 Cookie 失败: {str(e)}")
        return False
def process_user(js_compiled: any, user_cred: str, index: int):
    """处理单个用户"""
    try:
        # 分割用户凭证
        if ":" not in user_cred:
            raise ValueError("用户凭证格式错误，应为 '手机号:密码:cookie'")
        parts = user_cred.split(":", 2)
        cookie = parts[2] if len(parts) > 2 else ""  # 分割成最多3部分
        phone = parts[0]
        password = parts[1]
        logger.info(f"处理用户 ########{index}: {phone}")

        # 登录获取Cookie（如果cookie为空，则调用登录接口）
        if cookie:
            session = create_session(cookie)
            if validate_cookie(session):
                logger.info(f"用户 {phone} 的 Cookie 仍然有效，跳过登录")
                cookie_str = cookie
            else:
                logger.warning(f"用户 {phone} 的 Cookie 已过期，正在重新登录...")
                cookie_str = login_user(js_compiled, phone, password)
        else:
            cookie_str = login_user(js_compiled, phone, password)

        # 只有在 Cookie 发生变化时才更新 QingLong 环境变量
        if not cookie or cookie_str != cookie:
            all_user = QLAPI.getEnvs({"searchValue": "WYY_YYR"})["data"]
            for user in all_user:
                if user["value"].find(phone) != -1:
                    logger.info(f"{phone}:{password}:{cookie_str}")
                    QLAPI.updateEnv(
                        {
                            "env": {
                                "id": user["id"],
                                "value": f"{phone}:{password}:{cookie_str}",
                            }
                        }
                    )
                    logger.info(f"更新用户:{phone}成功")
                    break

        # 创建Session
        session = create_session(cookie_str)

        # 获取账户信息
        account_id = get_account_info(session, js_compiled)

        # 获取音乐人数据
        musician_data = get_musician_data(session, js_compiled, account_id)

        # 获取歌曲数据
        song_data = get_song_data(session, account_id)

        # 生成报告
        report = format_report(index, account_id, musician_data, song_data)

        # 发送通知
        QLAPI.systemNotify(
            {"title": f"网易云音乐人报告 - 用户 #{index}", "content": report}
        )

        return True
    except Exception as e:
        logger.error(f"处理用户 #{index} 失败: {str(e)}")
        return False


def main():
    """主函数"""
    try:
        # 获取脚本目录
        script_dir = os.path.dirname(os.path.abspath(__file__))
        js_path = os.path.join(script_dir, "./utils/js_reverse/wyy_reverse.js")

        # 加载JS加密模块
        js_compiled = compile_js(js_path)

        # 获取用户凭证
        user_creds = env.get_env("WYY_YYR")
        if not user_creds:
            logger.error("未找到有效的用户凭证")
            return

        logger.info(f"找到 {len(user_creds)} 个用户")

        # 处理每个用户
        success_count = 0
        for i, cred in enumerate(user_creds, 1):
            if process_user(js_compiled, cred, i):
                success_count += 1

        logger.info(f"处理完成: 成功 {success_count}/{len(user_creds)} 个用户")
    except Exception as e:
        logger.error(f"程序执行失败: {str(e)}")


if __name__ == "__main__":
    main()
