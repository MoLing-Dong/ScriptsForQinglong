"""
name: bing 积分
定时规则
cron: 1 9 * * *

使用Edge浏览器打开必应 https://rewards.bing.com/ F12抓取Cookie即可

变量名：BING_COOKIE  多账号换行
"""
import requests
import os
import time
import random
import json
import datetime
import urllib.parse
import re

# --- 核心功能 ---


def get_dashboard_data(session: requests.Session) -> tuple[dict | None, str | None]:
    """获取并解析 Bing Rewards 页面的 dashboard 数据和用户邮箱。"""
    try:
        response = session.get(
            "https://rewards.bing.com",
            headers={
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36 Edg/137.0.0.0"
            },
            timeout=15,
        )
        response.raise_for_status()
        html_text = response.text

        # 提取 dashboard JSON
        dashboard_match = re.search(
            r"var dashboard\s*=\s*(\{.*?\});", html_text, re.DOTALL
        )
        if not dashboard_match:
            print_log("错误", '未找到 "var dashboard"。')
            return None, None

        try:
            dashboard_json = json.loads(dashboard_match.group(1).rstrip().rstrip(";"))
        except json.JSONDecodeError as e:
            print_log("解析错误", f"无法解析 Dashboard JSON: {e}")
            return None, None

        # 提取 email (优先使用正则从 JS 块中提取)
        email_match = re.search(r'email\s*:\s*"([^"]+)"', html_text)
        email = email_match.group(1) if email_match else None

        # 若正则失败，则从 HTML 元素中后备提取
        if not email:
            email_match_fallback = re.search(
                r'<div id="mectrl_currentAccount_secondary"[^>]*>\s*([^<]+)\s*</div>',
                html_text,
            )
            email = (
                email_match_fallback.group(1).strip()
                if email_match_fallback
                else "未知邮箱"
            )

        return dashboard_json, email

    except requests.exceptions.RequestException as e:
        print_log("网络错误", f"请求 Bing Rewards 页面失败: {e}")
        return None, None
    except Exception as e:
        print_log("未知错误", f"获取数据时发生意外: {e}")
        return None, None


def bing_search(session: requests.Session, query_str: str):
    """执行单次电脑端 Bing 搜索。"""
    try:
        url = f"https://cn.bing.com/search?q={query_str}&qs=LT&form=TSASDS"
        headers = {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36 Edg/137.0.0.0",
            "referer": "https://rewards.bing.com/",
        }
        response = session.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            print_log(
                "搜索失败",
                f"关键词: {urllib.parse.unquote(query_str)}, 状态码: {response.status_code}",
            )
    except Exception as e:
        print_log("搜索异常", str(e))


def complete_daily_set_tasks(
    session: requests.Session, dashboard_data: dict, request_token: str
):
    """完成每日任务集。"""
    print_log("任务检查", "--- 开始执行每日任务集 ---")
    today_str = datetime.date.today().strftime("%m/%d/%Y")
    todays_tasks = dashboard_data.get("dailySetPromotions", {}).get(today_str, [])

    if not todays_tasks:
        print_log("任务总结", f"今日({today_str})无每日任务。")
        return

    incomplete_tasks = [
        t for t in todays_tasks if not t.get("complete") and "name" in t and "hash" in t
    ]

    if not incomplete_tasks:
        print_log("任务总结", "今日所有每日任务均已完成。")
        return

    print_log(
        "任务信息", f"发现 {len(incomplete_tasks)} 个未完成的每日任务，即将执行。"
    )
    post_url = (
        "https://rewards.bing.com/api/reportactivity?X-Requested-With=XMLHttpRequest"
    )
    post_headers = {
        "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
        "referer": "https://rewards.bing.com/",
    }

    for i, task in enumerate(incomplete_tasks, 1):
        payload = f"id={task['name']}&hash={task['hash']}&timeZone=480&activityAmount=1&dbs=0&form=&type=&__RequestVerificationToken={request_token}"
        try:
            print(
                f"({i}/{len(incomplete_tasks)}) 正在处理: '{task.get('title', '未知任务')}'...",
                end="",
                flush=True,
            )
            response = session.post(
                post_url, headers=post_headers, data=payload, timeout=15
            )
            time.sleep(random.uniform(2, 4))
            if response.ok and response.json().get("status") == "Success":
                result = response.json()
                print(f" 成功! 当前总积分: {result.get('balance', 'N/A')}。")
            else:
                print(
                    f" 失败! 状态码: {response.status_code}, 原因: {response.text[:100]}"
                )
        except Exception as e:
            print(f" 出错! 异常: {e}")

    print_log("任务结束", "--- 每日任务集执行完毕 ---")


# --- 辅助函数 ---


def get_random_char() -> str:
    """随机生成一个汉字。"""
    return chr(random.randint(0x4E00, 0x9FA5))


def print_log(title: str, msg: str):
    """格式化打印日志。"""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"{now} [{title}]: {msg or ''}")


def get_request_verification_token(session: requests.Session) -> str | None:
    """从页面提取 __RequestVerificationToken。"""
    try:
        response = session.get("https://rewards.bing.com/")
        response.raise_for_status()
        match = re.search(
            r'name="__RequestVerificationToken".*?value="([^"]+)"', response.text
        )
        if match:
            return match.group(1)
        print_log("错误", "未能找到 __RequestVerificationToken。")
        return None
    except requests.RequestException as e:
        print_log("网络错误", f"获取验证令牌失败: {e}")
        return None


# --- 主逻辑 ---


def start_main(bing_ck: str) -> str | None:
    """单个账号的完整任务流程，返回执行摘要。"""
    session = requests.Session()
    session.headers.update(
        {
            "cookie": bing_ck,
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36 Edg/137.0.0.0",
        }
    )

    dashboard_data, email = get_dashboard_data(session)
    print_log("当前账号", email or "未能获取邮箱")

    if not dashboard_data:
        print_log("初始化失败", "无法获取用户 Dashboard，请检查 Cookie。")
        return f"账号: {email or '未知'}\n状态: 初始化失败，无法获取 Dashboard"

    user_status = dashboard_data.get("userStatus", {})
    start_balance = user_status.get("availablePoints")
    market = user_status.get("market", "")

    if start_balance is None:
        print_log("初始化失败", "无法获取可用积分。")
        return f"账号: {email or '未知'}\n状态: 初始化失败，无法获取积分"

    level_info = user_status.get("levelInfo", {})
    level = level_info.get("activeLevel", "N/A")
    progress = level_info.get("progress", "N/A")
    progress_max = level_info.get("progressMax", "N/A")
    print_log("账号信息", f"等级: {level}, 进度: {progress}/{progress_max}")
    print_log("初始积分", str(start_balance))

    # 1. 执行电脑搜索
    pc_search = next(iter(user_status.get("counters", {}).get("pcSearch", [])), {})
    pc_progress, pc_total = pc_search.get("pointProgress", 0), pc_search.get(
        "pointProgressMax", 0
    )

    print_log("电脑搜索", f"当前进度: {pc_progress}/{pc_total}")
    if pc_progress < pc_total:
        search_count = (pc_total - pc_progress) // 3 + 3
        print_log("任务开始", f"--- 开始电脑搜索 (预计 {search_count} 次) ---")

        old_balance = start_balance
        for i in range(1, search_count + 1):
            query = urllib.parse.quote(get_random_char() + get_random_char())
            bing_search(session, query)
            time.sleep(random.uniform(2.5, 4.5))

            wait_time = random.randint(15, 30)
            print_log("电脑搜索", f"第{i}次搜索中，等待 {wait_time}s 后继续...")
            time.sleep(wait_time)

            if i % 3 == 0:
                new_dashboard, _ = get_dashboard_data(session)
                if new_dashboard:
                    new_balance = new_dashboard.get("userStatus", {}).get(
                        "availablePoints", old_balance
                    )
                    print_log(
                        f"电脑搜索第{i}次后",
                        f"当前积分: {new_balance} (较上次增加: {new_balance - old_balance})",
                    )
                    if new_balance <= old_balance:
                        print_log("任务检测", "积分未增长，提前结束电脑搜索。")
                        break
                    old_balance = new_balance
                else:
                    print_log("提示", "未能获取最新数据，继续执行搜索...")

        print_log("任务结束", "--- 电脑搜索完成 ---")
    else:
        print_log("任务跳过", "电脑搜索已完成。")

    time.sleep(random.uniform(2, 4))

    # 2. 执行每日任务
    request_token = get_request_verification_token(session)
    latest_dashboard, _ = get_dashboard_data(session)
    if request_token and latest_dashboard:
        complete_daily_set_tasks(session, latest_dashboard, request_token)
    else:
        print_log("任务跳过", "未能获取每日任务所需信息，跳过此部分。")

    # 3. 获取最终积分并生成摘要
    time.sleep(random.uniform(2, 4))
    final_dashboard, _ = get_dashboard_data(session)
    if final_dashboard:
        final_balance = final_dashboard.get("userStatus", {}).get(
            "availablePoints", start_balance
        )
        points_earned = final_balance - start_balance
        print_log(
            "本轮总结",
            f"初始: {start_balance}, 最终: {final_balance}, 获得: {points_earned}",
        )

        # --- [修改] 计算总计积分并更新推送内容 ---
        summary_line = f"账号: {email}\n状态: {start_balance} -> {final_balance} (本轮+{points_earned})"  # 默认值
        try:
            final_user_status = final_dashboard.get("userStatus", {})
            final_counters = final_user_status.get("counters", {})

            # 电脑搜索积分
            pc_info = next(iter(final_counters.get("pcSearch", [])), {})
            pc_points = pc_info.get("pointProgress", 0)

            # 每日任务积分
            daily_set_completed_points = 0
            today_str = datetime.date.today().strftime("%m/%d/%Y")
            daily_promos = final_dashboard.get("dailySetPromotions", {}).get(
                today_str, []
            )
            if daily_promos:
                for task in daily_promos:
                    if task.get("complete") is True:
                        daily_set_completed_points += task.get("pointProgress", 0)

            # 计算总和
            total_daily_points_earned = pc_points + daily_set_completed_points
            print_log(
                "今日总计", f"已获得 {total_daily_points_earned} 积分 (基于当前状态)"
            )

            # 更新推送内容，加入总计
            summary_line = (
                f"账号: {email}\n"
                f"状态: {start_balance} -> {final_balance} (本轮+{points_earned})\n"
                f"今日总计: {total_daily_points_earned} 积分"
            )

        except Exception as e:
            print_log("提示", f"计算最终积分汇总时出错: {e}")

        return summary_line
    else:
        print_log("本轮总结", "未能获取最终积分，无法生成摘要。")
        return f"账号: {email}\n状态: 未能获取最终状态"


if __name__ == "__main__":
    BING_COOKIE = os.getenv("BING_COOKIE")

    if not BING_COOKIE:
        BING_COOKIE = """
        请在这里粘贴你的Cookie
        """.strip()

    if not BING_COOKIE or "请在这里粘贴" in BING_COOKIE:
        print_log(
            "错误", "未配置有效 Cookie。请设置 BING_COOKIE 环境变量或在脚本中修改。"
        )
    else:
        all_cookies = [
            ck.strip() for ck in BING_COOKIE.strip().split("\n") if ck.strip()
        ]
        print_log("初始化", f"检测到 {len(all_cookies)} 个账号，即将开始...")

        all_summaries = []

        for i, ck in enumerate(all_cookies, 1):
            print_log("账号任务", f"----- [账号 {i}/{len(all_cookies)}] -----")
            summary = start_main(ck)
            if summary:
                all_summaries.append(summary)

            if i < len(all_cookies):
                wait_time = random.randint(15, 40)
                print_log("账号切换", f"等待 {wait_time}s 后进行下一个账号...")
                time.sleep(wait_time)

        print(
            f"\n{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} [任务完成]: 所有账号执行完毕。"
        )

        # 统一推送总结报告
        if all_summaries:
            print_log("统一推送", "准备发送总结报告...")
            try:
                today = datetime.date.today().strftime("%Y-%m-%d")
                title = f"Bing 任务总结 ({today})"
                content = "\n\n".join(all_summaries)
                QLAPI.notify(title, content)
                print_log("推送成功", "总结报告已发送。")
            except Exception as e:
                print_log("推送失败", f"发送总结报告时出错: {e}")
        else:
            print_log("统一推送", "无任何账号信息可供推送。")
