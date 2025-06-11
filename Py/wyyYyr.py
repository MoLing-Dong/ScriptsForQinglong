"""
推歌参谋
name: 推歌参谋数据查询
定时规则
cron: 0 7,18 * * *
@site: https://st.music.163.com/g/push-assiant
"""

import json
import os
from datetime import datetime, timedelta
from operator import itemgetter
from typing import Dict, List, Any
import utils.pyEnv as env

import execjs
import requests
from loguru import logger

# 移除默认的 handler（包含时间戳等）
logger.remove()

# 添加只输出消息内容的 handler
logger.add(lambda msg: print(msg, end=""), format="{message}")
# 配置信息
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

PARAMS = {"csrf_token": "005b52c72ebb34e46b28221f28c55064"}


def compile_js(js_path: str) -> Any:
    """编译 JavaScript 文件并返回可调用对象"""
    try:
        with open(js_path, "r", encoding="utf-8") as f:
            js_content = f.read()
        return execjs.compile(js_content)
    except Exception as e:
        logger.error(f"加载 JavaScript 文件失败: {e}")
        raise


def get_data(js_compiled: Any, params: Dict[str, str]) -> Dict[str, str]:
    """通过 JavaScript 加密生成参数"""
    try:
        result = js_compiled.call("getData", params)
        return {"params": result["encText"], "encSecKey": result["encSecKey"]}
    except Exception as e:
        logger.error(f"执行 JavaScript 加密失败: {e}")
        raise


def create_session(cookies) -> requests.Session:
    """为每个用户创建独立的 Session 并设置 Cookies"""
    try:
        session = requests.Session()
        session.headers.update(HEADERS)
        session.headers.update({"cookie": cookies})
        return session
    except Exception as e:
        logger.error(f"创建 Session 失败: {e}")
        raise


def post_request(
    session: requests.Session,
    url: str,
    data: Dict[str, str] = None,
    params: Dict[str, str] = None,
) -> str:
    """发送 POST 请求并打印响应结果"""
    try:
        response = session.post(url, params=params, data=data)
        response.raise_for_status()
        # logger.debug(response.text)
        return response.text
    except requests.RequestException as e:
        logger.error(f"请求 {url} 失败: {e}")
        raise


def fetch_data(
    session: requests.Session,
    page_num,
    page_size,
    artist_id,
    dt,
    order_field,
    order_direction,
):
    """获取实时歌曲数据"""
    json_data = {
        "page_num": page_num,
        "artist_id": artist_id,
        "dt": dt,
        "page_size": page_size,
        "order_field": order_field,
        "order_direction": order_direction,
        "use_total_num": 1,
    }
    try:
        session.headers.update({"content-type": "application/json"})
        response = session.post(
            "https://interface.music.163.com/api/push-song-advisor/open/api/data-service/advisor/real_time_song_list",
            json=json_data,
        )
        response.raise_for_status()
        data = response.json()
        # logger.debug(f"获取数据成功: {data}")
        return data
    except requests.RequestException as e:
        logger.error(f"请求失败: {e}")
        raise


def main(user_cookies_list: List[Dict[str, str]], js_path: str):
    try:
        # 加载并编译 JavaScript 文件
        js_compiled = compile_js(js_path)
        msg = ""
        for i, user_cookies in enumerate(user_cookies_list, start=1):
            msg = ""
            try:
                logger.info(f"处理第 {i} 个用户的请求")
                msg += f"第 {i} 个用户: "
                session = create_session(user_cookies)
                data = get_data(js_compiled, PARAMS)

                # 先请求用户账号信息
                account_response = post_request(
                    session,
                    "https://interface.music.163.com/api/nuser/account/get",
                    params=PARAMS,
                )
                account_id = json.loads(account_response).get("account").get("id")
                logger.info(f"当前用户 ID: {account_id}")
                msg += f"当前用户 ID: {account_id}\n"
                # 根据用户账号信息进行后续请求
                post_request(
                    session,
                    "https://interface.music.163.com/weapi/push-song-advisor/open/api/id/trans",
                    get_data(
                        js_compiled,
                        {
                            "id": account_id,
                            "sourceIdType": "userId",
                            "targetIdType": "artistId",
                        },
                    ),
                    PARAMS,
                )

                # 请求音乐人信息
                user_info = post_request(
                    session,
                    "https://music.163.com/weapi/nmusician/entrance/user/musician/info/get",
                    data,
                    PARAMS,
                )
                msg += f"音乐人信息: {user_info}\n"
                user_info = json.loads(user_info)
                logger.info(
                    f'状态: {user_info["message"]} ,当前用户名: {user_info["data"]["artistName"]}'
                )

                # 请求音乐人统计数据
                musician_creator = post_request(
                    session,
                    "https://music.163.com/weapi/creator/musician/statistic/data/overview/get",
                    data,
                    PARAMS,
                )
                musician_creator = json.loads(musician_creator)
                logger.info(
                    f'昨日播放: {musician_creator["data"]["playCount"]} ,总播放: {musician_creator["data"]["totalPlayCount"]}'
                )
                msg += f'昨日播放: {musician_creator["data"]["playCount"]} ,总播放: {musician_creator["data"]["totalPlayCount"]}\n'
                # 请求音乐人收入
                musician_income = post_request(
                    session,
                    "https://music.163.com/weapi/nmusician/workbench/creator/wallet/overview",
                    data,
                    PARAMS,
                )
                # logger.debug(musician_income)
                musician_income = json.loads(musician_income)
                logger.info(
                    f'月收入: {musician_income["data"]["monthAmount"]} ,日收入: {musician_income["data"]["dailyAmount"]}'
                )
                msg += f'月收入: {musician_income["data"]["monthAmount"]} ,日收入: {musician_income["data"]["dailyAmount"]}\n'
                # 获取歌曲的今日播放趋势数据
                tend_info = post_request(
                    session,
                    "https://music.163.com/weapi/creator/musician/play/count/statistic/data/trend/get",
                    get_data(
                        js_compiled,
                        {
                            "startTime": (datetime.now() - timedelta(days=7)).strftime(
                                "%Y-%m-%d"
                            ),
                            "endTime": (datetime.now() - timedelta(days=1)).strftime(
                                "%Y-%m-%d"
                            ),
                            "csrf_token": "51c7384b8dead9388a033b43afd1b40c",
                        },
                    ),
                    PARAMS,
                )
                tend_info = json.loads(tend_info)

                # 检查 tend_info 的结构
                if "data" in tend_info and isinstance(tend_info["data"], list):
                    for entry in tend_info["data"]:
                        date_time = entry.get("dateTime", "N/A")
                        data_value = entry.get("dataValue", "N/A")
                        logger.info(f"日期: {date_time} ,播放量: {data_value}")
                else:
                    logger.error("Unexpected structure of tend_info")

                # 获取歌曲数据
                page_size = 200
                artist_id = account_id
                dt = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
                order_field = "today_play_cnt"
                order_direction = "desc"
                page_num = 1

                all_songs = []
                first_page_data = fetch_data(
                    session,
                    page_num,
                    page_size,
                    artist_id,
                    dt,
                    order_field,
                    order_direction,
                )
                total_num = first_page_data.get("data", {}).get("total_num", 0)
                total_pages = (total_num + page_size - 1) // page_size
                logger.info(f"总数据量: {total_num}, 总页数: {total_pages}")
                msg += f"总数据量: {total_num}, 总页数: {total_pages}\n"
                # 收集第一页数据
                all_songs.extend(first_page_data.get("data", {}).get("data", []))

                # 收集其他页数据
                for page_num in range(2, total_pages + 1):
                    data = fetch_data(
                        session,
                        page_num,
                        page_size,
                        artist_id,
                        dt,
                        order_field,
                        order_direction,
                    )
                    all_songs.extend(data.get("data", {}).get("data", []))

                # 按 today_play_cnt 降序排序
                sorted_songs = sorted(
                    all_songs, key=itemgetter("today_play_cnt"), reverse=True
                )

                today_play_cnt_total = sum(
                    song.get("today_play_cnt", 0) for song in sorted_songs
                )
                logger.info(f"今日播放总量: {today_play_cnt_total}")
                msg += f"今日播放总量: {today_play_cnt_total}\n"
                # 输出排序结果
                for song in sorted_songs:
                    song_name = song.get("song_name", "未知歌曲名")
                    today_play_cnt = song.get("today_play_cnt", 0)
                    yesterday_play_cnt = song.get("yesterday_play_cnt", 0)
                    thumbnails = song.get("thumbnails", 0)
                    logger.info(
                        f"歌曲名: {song_name}, 今日播放量: {today_play_cnt}, 昨日播放量: {yesterday_play_cnt}, "
                        f"实时数据: {thumbnails}"
                    )
                    msg += (
                        f"歌曲名: {song_name}, 今日播放量: {today_play_cnt}, 昨日播放量: {yesterday_play_cnt}, "
                        f"实时数据: {thumbnails}\n"
                    )
                QLAPI.systemNotify(
                    {
                        "title": f"网易云音乐人推歌参谋",
                        "content": msg,
                    }
                )
            except Exception as e:
                logger.error(f"用户 {i} 数据获取失败: {e}")

    except Exception as e:
        logger.error(f"处理失败: {e}")


def load_user_cookies(file_path: str) -> list:
    """加载用户 Cookies 列表"""
    if not os.path.exists(file_path):
        logger.error(f"文件不存在: {file_path}")
        return []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            user_cookies_list = json.load(f)
        if not isinstance(user_cookies_list, list):
            logger.error(f"文件内容格式错误，应为列表: {file_path}")
            return []
        return user_cookies_list
    except json.JSONDecodeError as e:
        logger.error(f"解析 JSON 文件失败: {e}")
        return []
    except Exception as e:
        logger.error(f"加载用户 Cookies 失败: {e}")
        return []


def get_js_path(base_dir: str, relative_path: str) -> str:
    """获取 JavaScript 文件路径"""
    js_path = os.path.join(base_dir, relative_path)
    if not os.path.exists(js_path):
        logger.error(f"JavaScript 文件不存在: {js_path}")
        return ""
    return js_path


if __name__ == "__main__":

    logger.add("./log/musician_api.log", rotation="50 MB")

    # 获取脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # 加载用户 Cookies 列表
    all_data = env.get_env("WYY_YYR")
    logger.info(f"获取到 {len(all_data)} 个用户 Cookies")
    if not all_data:
        logger.error("用户 Cookies 列表为空，程序终止")
        exit(1)

    # 获取 JavaScript 文件路径
    JS_PATH = get_js_path(script_dir, "./utils/js_reverse/wyy_reverse.js")
    if not JS_PATH:
        logger.error("JavaScript 文件路径无效，程序终止")
        exit(1)
    # 执行主函数
    main(all_data, JS_PATH)
