"""
AI早报
name: AI早报
定时规则
cron: 0 7,20 * * *
"""

import asyncio
import re
import time
import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional, Tuple, Dict, Union, Any
import utils.pyEnv as env
from openai import OpenAI
import QLAPI
import aiohttp
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from loguru import logger
# 导入配置
ZHIPU_API_KEY = env.get_env("ZHIPU_API_KEY")[0]
ZHIPU_BASE_URL = env.get_env("ZHIPU_BASE_URL")[0]
# 设置日志
logger.remove()  # 移除默认处理器
logger.add(
    sink=lambda msg: print(msg, end=""),
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
    level="INFO"
)
# 时区和配置
TZ_SG = datetime.now().astimezone().tzinfo  # 本地时区（替代新加坡时区）
AIBASE_LIST = "https://www.aibase.com/zh/news/"  # AIBase 新闻列表页

# AIBase 文章 ID 匹配规则（用于提取最新文章ID）
AIBASE_ARTICLE_PATTERNS = [
    re.compile(r"/zh/news/(\d+)"),
    re.compile(r"/zh/news/detail/(\d+)"),
    re.compile(r"/news/(\d+)"),
    re.compile(r"/zh/news/(\d+)\.html"),
    re.compile(r"/zh/news/detail/(\d+)\.html"),
]


@dataclass
class Article:
    """文章数据结构（含爬取和总结所需全部字段）"""

    id: int  # 文章ID（AIBase 唯一标识）
    url: str  # 文章链接
    title: str  # 文章标题
    published_at: datetime  # 发布时间（用于时间筛选）
    content: str  # 文章正文（用于 AI 总结）


def _get_common_headers() -> Dict[str, str]:
    """获取通用请求头"""
    ua = UserAgent()
    return {
        "User-Agent": ua.random,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Referer": AIBASE_LIST,
        "Connection": "keep-alive",
    }


def _log_crawl_stats(
    start_time: float, total_articles: int, success_articles: int
) -> None:
    """记录爬取统计信息"""
    duration = time.time() - start_time
    success_rate = (
        (success_articles / total_articles * 100) if total_articles > 0 else 0
    )
    logger.info(
        f"爬取统计：耗时 {duration:.1f}秒，成功率 {success_rate:.1f}% ({success_articles}/{total_articles})"
    )


def _filter_articles_by_time(
    articles: List[Article], cutoff_time: datetime
) -> List[Article]:
    """根据时间筛选文章"""
    filtered_articles = []
    logger.info(f"时间筛选截止时间：{cutoff_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    for article in articles:
        logger.info(f"文章 ID={article.id} 发布时间：{article.published_at.strftime('%Y-%m-%d %H:%M:%S')}，是否 >= 截止时间：{article.published_at >= cutoff_time}")
        if article.published_at >= cutoff_time:
            filtered_articles.append(article)
            logger.info(
                f"筛选通过：文章 ID={article.id}（发布时间：{article.published_at.strftime('%Y-%m-%d %H:%M')}）"
            )
        else:
            logger.debug(f"筛选跳过：文章 ID={article.id}（发布时间早于截止时间）")
    return filtered_articles


def _deduplicate_and_sort_articles(
    articles: List[Article], max_articles: int
) -> List[Article]:
    """去重并排序文章"""
    # 去重
    dedup_dict: Dict[int, Article] = {art.id: art for art in articles}
    # 按发布时间倒序排序
    sorted_articles = sorted(
        dedup_dict.values(), key=lambda x: x.published_at, reverse=True
    )
    # 截取指定数量
    return sorted_articles[:max_articles]


def _parse_article_html(
    html: str, article_id: int, article_url: str
) -> Optional[Article]:
    """解析文章HTML的通用逻辑"""
    try:
        soup = BeautifulSoup(html, "html.parser")

        # 提取标题
        title_elem = soup.find("h1")
        title = title_elem.get_text().strip() if title_elem else ""
        if not title:
            logger.warning(f"解析失败：文章 ID={article_id} 无标题")
            return None

        # 提取发布时间
        date_text = ""
        date_match = re.search(r"([A-Za-z]{3}\s+\d{1,2},\s+\d{4})", html)
        if date_match:
            date_text = date_match.group(1)
        else:
            date_elem = soup.find("div", class_="text-surface-500")
            if date_elem:
                date_text = date_elem.get_text().strip()

        pub_dt = parse_chinese_datetime(date_text)
        if not pub_dt:
            logger.warning(f"解析失败：文章 ID={article_id} 无法获取发布时间")
            return None

        # 提取正文
        content_elem = soup.find("div", class_="post-content")
        content = content_elem.get_text().strip() if content_elem else ""
        content = re.sub(r"\n{3,}", "\n\n", content)
        content = re.sub(r"\s+", " ", content)

        if len(content) < 50:
            logger.warning(f"解析失败：文章 ID={article_id} 正文过短（{len(content)}字）")
            return None

        return Article(
            id=article_id,
            url=article_url,
            title=title,
            published_at=pub_dt,
            content=content,
        )
    except Exception as e:
        logger.error(f"解析文章时发生异常：ID={article_id}, 错误={str(e)}")
        return None


async def safe_get_async(
    url: str, session: aiohttp.ClientSession, timeout: int = 15
) -> Optional[str]:
    """异步安全 HTTP GET 请求（模拟浏览器，避免反爬，核心爬取工具）"""
    headers = _get_common_headers()

    try:
        async with session.get(url, headers=headers, timeout=timeout) as resp:
            if resp.status != 200:
                logger.warning(f"请求失败：{url}, 状态码 {resp.status}")
                return None
            text = await resp.text()
            return text
    except asyncio.TimeoutError:
        logger.warning(f"请求超时：{url}")
        return None
    except aiohttp.ClientError as e:
        logger.error(f"网络错误：{url}, 错误={str(e)[:50]}")
        return None
    except Exception as e:
        logger.error(f"未知错误：{url}, 错误={str(e)[:50]}")
        return None


def safe_get(url: str, timeout: int = 15) -> Optional[str]:
    """同步安全 HTTP GET 请求（保持向后兼容）"""
    headers = _get_common_headers()

    try:
        resp = requests.get(url, headers=headers, timeout=timeout)
        if resp.status_code != 200:
            logger.warning(f"请求失败：{url}, 状态码 {resp.status_code}")
            return None
        resp.encoding = "utf-8"  # 强制 UTF-8 编码，避免中文乱码
        return resp.text
    except requests.Timeout:
        logger.warning(f"请求超时：{url}")
        return None
    except requests.RequestException as e:
        logger.error(f"网络错误：{url}, 错误={str(e)[:50]}")
        return None
    except Exception as e:
        logger.error(f"未知错误：{url}, 错误={str(e)[:50]}")
        return None


def parse_chinese_datetime(text: str) -> Optional[datetime]:
    """解析 AIBase 文章发布时间（支持多种格式，核心时间处理工具）"""
    if not text:
        return None
    text = re.sub(r"\s+", " ", text.strip())  # 清理多余空格
    
    # 添加调试打印
    logger.info(f"开始解析时间：'{text}'")

    # 格式1：2024年10月18日 11:54（中文日期）
    pattern1 = re.search(
        r"(\d{4})年(\d{1,2})月(\d{1,2})日(?:\s+(\d{1,2}):(\d{2}))?", text
    )
    if pattern1:
        try:
            result = datetime(
                year=int(pattern1.group(1)),
                month=int(pattern1.group(2)),
                day=int(pattern1.group(3)),
                hour=int(pattern1.group(4) or 0),
                minute=int(pattern1.group(5) or 0),
                tzinfo=TZ_SG,
            )
            logger.info(f"成功解析中文日期格式：'{text}' → {result}")
            return result
        except Exception as e:
            logger.info(f"解析日期格式1失败：{text} → {e}")

    # 格式2：Aug 26, 2025（英文日期，AIBase 部分页面使用）
    pattern2 = re.search(r"([A-Za-z]{3})\s+(\d{1,2}),\s+(\d{4})", text)
    if pattern2:
        month_map = {
            "Jan": 1,
            "Feb": 2,
            "Mar": 3,
            "Apr": 4,
            "May": 5,
            "Jun": 6,
            "Jul": 7,
            "Aug": 8,
            "Sep": 9,
            "Oct": 10,
            "Nov": 11,
            "Dec": 12,
        }
        try:
            result = datetime(
                year=int(pattern2.group(3)),
                month=month_map[pattern2.group(1)],
                day=int(pattern2.group(2)),
                tzinfo=TZ_SG,
            )
            logger.info(f"成功解析英文日期格式：'{text}' → {result}")
            return result
        except Exception as e:
            logger.info(f"解析日期格式2失败：{text} → {e}")

    logger.info(f"无法解析日期：'{text}'")
    return None


async def fetch_single_article_async(
    article_id: int, session: aiohttp.ClientSession
) -> Optional[Article]:
    """异步爬取单篇 AIBase 文章（核心爬取逻辑，含内容/标题/时间提取）"""
    # 检查缓存
    async with _cache_lock:
        if article_id in _article_cache:
            logger.debug(f"从缓存获取文章：ID={article_id}")
            return _article_cache[article_id]

    article_url = f"https://www.aibase.com/zh/news/{article_id}"
    logger.info(f"正在爬取文章：ID={article_id} → {article_url}")

    # 获取文章页面 HTML
    html = await safe_get_async(article_url, session)
    if not html:
        logger.warning(f"爬取失败：文章 ID={article_id} 页面为空")
        async with _cache_lock:
            _article_cache[article_id] = None
        return None

    # 解析 HTML
    result = _parse_article_html(html, article_id, article_url)

    # 缓存结果
    async with _cache_lock:
        _article_cache[article_id] = result

    return result


def fetch_single_article(article_id: int) -> Optional[Article]:
    """同步爬取单篇 AIBase 文章（保持向后兼容）"""
    # 检查缓存
    if article_id in _article_cache:
        logger.debug(f"从缓存获取文章：ID={article_id}")
        return _article_cache[article_id]

    article_url = f"https://www.aibase.com/zh/news/{article_id}"
    logger.info(f"正在爬取文章：ID={article_id} → {article_url}")

    # 获取文章页面 HTML
    html = safe_get(article_url)
    if not html:
        logger.warning(f"爬取失败：文章 ID={article_id} 页面为空")
        _article_cache[article_id] = None
        return None

    # 解析 HTML
    result = _parse_article_html(html, article_id, article_url)

    # 缓存结果
    _article_cache[article_id] = result

    return result


def discover_latest_article_id() -> Optional[int]:
    """发现 AIBase 最新文章 ID（从列表页提取，避免盲目爬取）"""
    logger.info("开始获取 AIBase 最新文章 ID...")
    # 爬取新闻列表页
    list_html = safe_get(AIBASE_LIST)
    if not list_html:
        logger.error("失败：无法获取 AIBase 新闻列表页")
        return None

    # 从列表页 HTML 中匹配所有文章 ID
    all_article_ids = []
    for pattern in AIBASE_ARTICLE_PATTERNS:
        matches = pattern.findall(list_html)
        all_article_ids.extend([int(m) for m in matches if m.isdigit()])

    if not all_article_ids:
        logger.error("失败：未从列表页提取到任何文章 ID")
        return None

    # 返回最大 ID（即最新文章）
    latest_id = max(all_article_ids)
    logger.info(
        f"成功：获取到最新文章 ID={latest_id}（共提取 {len(all_article_ids)} 个 ID）"
    )
    return latest_id


async def _fetch_batch_async(
    batch_ids: List[int], session: aiohttp.ClientSession
) -> List[Article]:
    """异步批量获取文章"""
    max_concurrent = MAX_CONCURRENT_REQUESTS
    semaphore = asyncio.Semaphore(max_concurrent)

    async def fetch_with_semaphore(article_id):
        async with semaphore:
            # 随机延迟（0.5-1.5 秒，模拟人工浏览，降低反爬风险）
            await asyncio.sleep(random.uniform(0.5, 1.5))
            return await fetch_single_article_async(article_id, session)

    tasks = [fetch_with_semaphore(aid) for aid in batch_ids]
    batch_results = await asyncio.gather(*tasks, return_exceptions=True)

    batch_articles = []
    for result in batch_results:
        if isinstance(result, Article):
            batch_articles.append(result)
        elif isinstance(result, Exception):
            logger.error(f"获取文章失败：{str(result)}")

    return batch_articles


async def collect_recent_articles_async(hours: int, max_articles: int) -> List[Article]:
    """异步批量爬取指定时间范围内的文章（并发批量爬取逻辑）"""
    start_time = time.time()

    # 1. 确定时间范围（仅保留 "hours" 小时内的文章）
    cutoff_time = datetime.now(TZ_SG) - timedelta(hours=hours)
    logger.info(f"当前系统时间：{datetime.now(TZ_SG).strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(
        f"开始爬取 {hours} 小时内的文章（截止时间：{cutoff_time.strftime('%Y-%m-%d %H:%M:%S')}）"
    )

    # 2. 获取最新文章 ID（避免从 0 开始盲目爬取）
    latest_id = discover_latest_article_id()
    if not latest_id:
        logger.warning("使用默认 ID=20805 作为起始爬取点（最新 ID 获取失败）")
        latest_id = 20805

    # 3. 反向爬取（从最新 ID 往旧 ID 爬，确保优先获取最新文章）
    collected_articles: List[Article] = []
    current_id = latest_id
    no_new_count = 0  # 连续无新文章的次数（超过 3 次则停止爬取）
    batch_step = BATCH_STEP  # 每批爬取数量

    async with aiohttp.ClientSession() as session:
        while (
            current_id > 0
            and len(collected_articles) < max_articles
            and no_new_count < 3
        ):
            # 本次批次的文章 ID 列表（从 current_id 往回取 batch_step 个）
            batch_ids = list(range(current_id, max(current_id - batch_step, 0), -1))
            logger.info(f"当前批次爬取 ID：{batch_ids}")

            # 并发爬取批次内的文章
            batch_articles = await _fetch_batch_async(batch_ids, session)

            # 筛选批次内符合时间范围的文章
            new_articles = _filter_articles_by_time(batch_articles, cutoff_time)

            # 更新爬取状态
            if new_articles:
                collected_articles.extend(new_articles)
                no_new_count = 0  # 有新文章，重置连续无新计数
            else:
                no_new_count += 1  # 无新文章，计数+1
                logger.info(
                    f"本批次无符合条件的文章，剩余重试次数：{3 - no_new_count}",
                    "warning",
                )

            # 准备下一批次（ID 往前推 batch_step 个）
            current_id -= batch_step
            # 批次间延迟（2-4 秒，进一步降低反爬概率）
            await asyncio.sleep(random.uniform(2, 4))

    # 4. 去重 + 按发布时间倒序排序（确保最新文章在前）
    final_articles = _deduplicate_and_sort_articles(collected_articles, max_articles)

    # 记录统计信息
    _log_crawl_stats(start_time, len(collected_articles), len(final_articles))

    logger.info(
        f"爬取完成：共获取 {len(final_articles)} 篇符合条件的文章（目标 {max_articles} 篇）"
    )
    return final_articles


def _fetch_batch_sync(batch_ids: List[int]) -> List[Article]:
    """同步批量获取文章"""
    batch_articles = []
    for aid in batch_ids:
        article = fetch_single_article(aid)
        if article:
            batch_articles.append(article)
        # 随机延迟（0.5-1.5 秒，模拟人工浏览，降低反爬风险）
        time.sleep(random.uniform(0.5, 1.5))
    return batch_articles


def collect_recent_articles(hours: int, max_articles: int) -> List[Article]:
    """批量爬取指定时间范围内的文章（核心批量爬取逻辑）"""
    start_time = time.time()

    # 1. 确定时间范围（仅保留 "hours" 小时内的文章）
    cutoff_time = datetime.now(TZ_SG) - timedelta(hours=hours)
    logger.info(f"当前系统时间：{datetime.now(TZ_SG).strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(
        f"开始爬取 {hours} 小时内的文章（截止时间：{cutoff_time.strftime('%Y-%m-%d %H:%M:%S')}）"
    )

    # 2. 获取最新文章 ID（避免从 0 开始盲目爬取）
    latest_id = discover_latest_article_id()
    if not latest_id:
        logger.warning("使用默认 ID=20805 作为起始爬取点（最新 ID 获取失败）")
        latest_id = 20805

    # 3. 反向爬取（从最新 ID 往旧 ID 爬，确保优先获取最新文章）
    collected_articles: List[Article] = []
    current_id = latest_id
    no_new_count = 0  # 连续无新文章的次数（超过 3 次则停止爬取）
    batch_step = 5  # 每批爬取 5 篇（避免单次请求过多被反爬）

    while (
        current_id > 0 and len(collected_articles) < max_articles and no_new_count < 3
    ):
        # 本次批次的文章 ID 列表（从 current_id 往回取 batch_step 个）
        batch_ids = list(range(current_id, max(current_id - batch_step, 0), -1))
        logger.info(f"当前批次爬取 ID：{batch_ids}")

        # 逐个爬取批次内的文章
        batch_articles = _fetch_batch_sync(batch_ids)

        # 筛选批次内符合时间范围的文章
        new_articles = _filter_articles_by_time(batch_articles, cutoff_time)

        # 更新爬取状态
        if new_articles:
            collected_articles.extend(new_articles)
            no_new_count = 0  # 有新文章，重置连续无新计数
        else:
            no_new_count += 1  # 无新文章，计数+1
            logger.info(
                f"本批次无符合条件的文章，剩余重试次数：{3 - no_new_count}", "warning"
            )

        # 准备下一批次（ID 往前推 batch_step 个）
        current_id -= batch_step
        # 批次间延迟（2-4 秒，进一步降低反爬概率）
        time.sleep(random.uniform(2, 4))

    # 4. 去重 + 按发布时间倒序排序（确保最新文章在前）
    final_articles = _deduplicate_and_sort_articles(collected_articles, max_articles)

    # 记录统计信息
    _log_crawl_stats(start_time, len(collected_articles), len(final_articles))

    logger.info(
        f"爬取完成：共获取 {len(final_articles)} 篇符合条件的文章（目标 {max_articles} 篇）"
    )
    return final_articles


def openai_client(
    api_key: Optional[str] = None, base_url: Optional[str] = None
) -> Optional[OpenAI]:
    """创建 OpenAI 客户端（AI 总结的前置准备）"""

    # 优先使用传入的 api_key，然后使用配置文件中的，最后使用环境变量
    final_api_key = api_key or ZHIPU_API_KEY
    final_base_url = base_url or ZHIPU_BASE_URL

    if (
        not final_api_key
        or final_api_key.strip() == "your_api_key"
        or len(final_api_key) < 10
    ):
        logger.warning("未提供有效的 OpenAI API 密钥")
        return None

    try:
        return OpenAI(api_key=final_api_key, base_url=final_base_url)
    except ValueError as e:
        logger.error(f"OpenAI客户端配置错误：{str(e)}")
        return None
    except Exception as e:
        logger.error(f"创建 OpenAI 客户端失败：{str(e)[:50]}")
        return None


def generate_local_summary(article: Article) -> str:
    """本地摘要兜底（AI 不可用时使用，避免流程中断）"""
    title = article.title.strip()

    # 优先使用完整标题，除非标题特别短
    if len(title) >= 10:
        return title

    # 如果标题太短，从正文提取有意义的内容
    content = article.content[:200]  # 取前 200 字分析
    sentences = re.split(r"[。！？\n]", content)

    # 寻找第一个有意义的句子（至少10个字）
    for sentence in sentences:
        sentence = sentence.strip()
        if len(sentence) >= 10:
            return sentence

    # 如果没有找到合适的句子，返回标题（即使短）
    if title:
        return title

    # 最后的兜底：取正文前30字
    return content[:30].strip()


def ai_summarize_article(client: OpenAI, model: str, article: Article) -> str:
    """单篇文章 AI 总结（核心 AI 交互逻辑）"""
    # AI 提示词（严格控制总结格式和质量）
    system_prompt = (
        "你是专业的科技文章摘要助手，需满足以下要求："
        "1. 基于文章正文内容进行总结，不要简单重复标题；"
        "2. 提炼文章的核心观点、技术要点或重要事件；"
        "3. 输出15-50字的完整句子，确保语义完整，信息丰富；"
        "4. 严格保留原文含义，不添加主观观点或额外信息；"
        "5. 禁止使用 Markdown 格式、特殊符号、省略号，仅输出纯文本；"
        "6. 输出一个完整的句子，不要截断或使用不完整的表达。"
    )
    # 构造用户输入（只使用正文内容，避免 AI 被标题影响）
    user_content = f"文章正文内容：{article.content[:1000]}"

    # AI 请求参数（降低温度确保摘要准确性）
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "temperature": 0.1,  # 随机性低，摘要更稳定
        "top_p": 0.7,
        "stream": False,
    }

    # 重试机制（应对 API 临时错误，最多重试 2 次）
    for retry in range(2):
        try:
            resp = client.chat.completions.create(**payload)
            summary = resp.choices[0].message.content.strip()
            # 清理摘要（去除多余空格和句号）
            summary = re.sub(r"\s+", " ", summary).strip().rstrip("。")
            return summary if summary else generate_local_summary(article)
        except Exception as e:
            error_msg = str(e)
            if "401" in error_msg or "authentication" in error_msg.lower():
                # 认证错误，直接使用本地摘要，不再重试
                logger.warning(f"API认证失败，使用本地摘要：文章 ID={article.id}")
                return generate_local_summary(article)
            elif "rate limit" in error_msg.lower() or "429" in error_msg:
                # 限流错误，等待更长时间
                wait_time = 5 ** (retry + 1)  # 指数退避（5秒、25秒）
                logger.info(
                    f"AI API限流（重试 {retry+1}/2）：{wait_time}秒后重试", "warning"
                )
                time.sleep(wait_time)
            elif "timeout" in error_msg.lower() or "connection" in error_msg.lower():
                # 网络超时，中等等待时间
                wait_time = 3 ** (retry + 1)  # 指数退避（3秒、9秒）
                logger.warning(f"AI API网络错误（重试 {retry+1}/2）：{wait_time}秒后重试")
                time.sleep(wait_time)
            else:
                # 其他错误，标准等待时间
                wait_time = 2**retry  # 指数退避（1秒、2秒）
                logger.warning(f"AI总结失败（重试 {retry+1}/2）：{error_msg[:50]}，{wait_time}秒后重试")
                time.sleep(wait_time)

    # 多次重试失败，使用本地兜底摘要
    logger.error(f"AI总结多次失败，使用本地兜底：文章 ID={article.id}")
    return generate_local_summary(article)


async def batch_ai_summarize_async(
    articles: List[Article], api_key: str, model: str
) -> List[Tuple[Article, str]]:
    """异步批量文章 AI 总结（并发总结逻辑，提高效率）"""
    if not articles:
        return []

    # 创建 AI 客户端
    ai_client = openai_client(api_key)
    summarized_list = []
    max_concurrent = MAX_CONCURRENT_AI  # AI 接口并发限制，避免触发限流
    semaphore = asyncio.Semaphore(max_concurrent)

    async def summarize_with_semaphore(article, idx):
        async with semaphore:
            logger.info(
                f"正在总结文章 {idx}/{len(articles)}：ID={article.id} → {article.title[:20]}..."
            )
            if ai_client:
                # AI 总结（需要将同步的 AI 调用包装为异步）
                loop = asyncio.get_event_loop()
                summary = await loop.run_in_executor(
                    None, ai_summarize_article, ai_client, model, article
                )
            else:
                # 无 AI 时使用本地兜底
                summary = generate_local_summary(article)

            # 总结间延迟（避免 AI 接口请求过于密集）
            await asyncio.sleep(random.uniform(0.3, 0.8))
            return (article, summary)

    # 创建所有总结任务
    tasks = [
        summarize_with_semaphore(article, idx)
        for idx, article in enumerate(articles, 1)
    ]

    # 并发执行所有总结任务
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # 收集成功的结果
    success_count = 0
    for result in results:
        if isinstance(result, tuple) and len(result) == 2:
            summarized_list.append(result)
            success_count += 1
        elif isinstance(result, Exception):
            logger.error(f"总结任务失败：{str(result)}")

    logger.info(f"AI总结完成：成功 {success_count}/{len(articles)} 篇文章")
    return summarized_list


def batch_ai_summarize(
    articles: List[Article], api_key: str, model: str
) -> List[Tuple[Article, str]]:
    """批量文章 AI 总结（遍历单篇总结逻辑，兼顾效率）"""
    if not articles:
        return []

    # 创建 AI 客户端
    ai_client = openai_client(api_key)
    summarized_list = []

    for idx, article in enumerate(articles, 1):
        logger.info(
            f"正在总结文章 {idx}/{len(articles)}：ID={article.id} → {article.title[:20]}..."
        )
        if ai_client:
            # AI 总结
            summary = ai_summarize_article(ai_client, model, article)
        else:
            # 无 AI 时使用本地兜底
            summary = generate_local_summary(article)
        summarized_list.append((article, summary))
        # 总结间延迟（避免 AI 接口请求过于密集）
        time.sleep(random.uniform(0.3, 0.8))

    return summarized_list


def render_markdown_report(
    date_label: str, summarized: List[Tuple[Article, str]]
) -> str:
    """生成 Markdown 格式报告（便于阅读和分享）"""
    if not summarized:
        return f"# AI 文章总结报告（{date_label}）\n\n无符合条件的文章"

    lines = [
        f"# AI 文章总结报告（{date_label}）",
        "",
        "---",
        "",
    ]

    for _, summary in enumerate(summarized, 1):
        lines.append(f"## {summary}")
        lines.append("")

    return "\n".join(lines).strip()


# 配置参数（静态变量）
DEFAULT_HOURS = 48
DEFAULT_MAX_ARTICLES = 20
DEFAULT_MODEL = "glm-4-flash"
DEFAULT_CONCURRENT = True
MAX_CONCURRENT_REQUESTS = 10  # 最大并发请求数
MAX_CONCURRENT_AI = 30  # AI 接口并发限制
BATCH_STEP = 10  # 每批爬取数量


# 简单缓存
_article_cache: Dict[int, Optional[Article]] = {}
_cache_lock = asyncio.Lock()


def main():
    # 使用静态变量配置
    hours = DEFAULT_HOURS
    max_articles = DEFAULT_MAX_ARTICLES
    model = DEFAULT_MODEL
    concurrent = DEFAULT_CONCURRENT

    if concurrent:
        # 使用异步并发模式（默认）
        asyncio.run(main_async(hours, max_articles, model))
    else:
        # 使用同步模式
        # 1. 批量爬取符合条件的文章
        logger.info("=" * 50)
        logger.info("步骤1：开始爬取 AIBase 文章（同步模式）")
        logger.info("=" * 50)
        articles = collect_recent_articles(hours, max_articles)
        if not articles:
            logger.info("警告：未爬取到任何符合条件的文章，程序退出")
            return

        # 2. 批量 AI 总结文章
        logger.info("=" * 50)
        logger.info("步骤2：开始 AI 总结文章（同步模式）")
        logger.info("=" * 50)
        summarized_articles = batch_ai_summarize(articles, ZHIPU_API_KEY, model)

        # 3. 生成 Markdown 报告
        logger.info("=" * 50)
        logger.info("步骤3：生成总结报告")
        logger.info("=" * 50)
        date_label = datetime.now(TZ_SG).strftime("%Y-%m-%d")
        markdown_content = render_markdown_report(date_label, summarized_articles)

        logger.info("程序执行完成！")


async def main_async(hours, max_articles, model):
    """异步主函数（并发模式）"""
    # 1. 批量爬取符合条件的文章
    logger.info("=" * 50)
    logger.info("步骤1：开始爬取 AIBase 文章（异步并发模式）")
    logger.info("=" * 50)
    articles = await collect_recent_articles_async(hours, max_articles)
    if not articles:
        logger.info("警告：未爬取到任何符合条件的文章，程序退出")
        return

    # 2. 批量 AI 总结文章
    logger.info("=" * 50)
    logger.info("步骤2：开始 AI 总结文章（异步并发模式）")
    logger.info("=" * 50)
    summarized_articles = await batch_ai_summarize_async(articles, ZHIPU_API_KEY, model)

    # 3. 生成 Markdown 报告
    logger.info("=" * 50)
    logger.info("步骤3：生成总结报告")
    logger.info("=" * 50)
    date_label = datetime.now(TZ_SG).strftime("%Y-%m-%d")
    markdown_content = render_markdown_report(date_label, summarized_articles)

    # 发送消息
    try:
        QLAPI.systemNotify(
            {"title": "AIBase 文章总结报告", "content": markdown_content}
        )
    except Exception as e:
        logger.info(f"错误：发送消息失败：{str(e)}")

    logger.info("程序执行完成！")


if __name__ == "__main__":
    main()
