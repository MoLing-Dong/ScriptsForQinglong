"""
Hacker News 早报（评论摘要版）
name: Hacker News早报
cron: 30 8 * * *

功能说明：
- 获取 Hacker News 热门故事
- 提取并总结社区评论
- 生成简洁的早报格式
- 只显示评论摘要和讨论链接
"""

import asyncio
import re
import time
import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional, Tuple, Dict, Any
import utils.pyEnv as env
from openai import OpenAI
import httpx
from loguru import logger

AI_API_KEY = env.get_env("AI_API_KEY")[0]
AI_BASE_URL = env.get_env("AI_BASE_URL")[0]

logger.remove()
logger.add(
    lambda m: print(m, end=""),
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
    level="INFO",
)

TZ_LOCAL = datetime.now().astimezone().tzinfo

HN_TOP_STORIES_URL = "https://hacker-news.firebaseio.com/v0/topstories.json"
HN_NEW_STORIES_URL = "https://hacker-news.firebaseio.com/v0/newstories.json"
HN_ITEM_URL = "https://hacker-news.firebaseio.com/v0/item/{}.json"

# Hacker News API 配置
# 使用官方 Firebase API，无需认证


@dataclass
class HNComment:
    """Hacker News 评论数据结构"""
    id: int
    text: str
    by: str
    time: datetime
    parent: int
    kids: Optional[List[int]] = None


@dataclass
class HNStory:
    """Hacker News 故事数据结构"""
    id: int
    title: str
    url: Optional[str]
    hn_url: str
    score: int
    by: str
    time: datetime
    descendants: int
    text: Optional[str] = None
    category: str = "general"
    comments: Optional[List[HNComment]] = None  # 评论列表
    comment_summary: Optional[str] = None  # AI 总结的评论摘要


def _get_story_category(title: str, url: Optional[str]) -> str:
    """获取故事分类（简化版，统一返回 general）"""
    return "general"


# 内存缓存，避免重复请求
_story_cache: Dict[int, Optional[HNStory]] = {}
_comment_cache: Dict[int, Optional[HNComment]] = {}


async def fetch_comment_details(
    client: httpx.AsyncClient, cid: int
) -> Optional[HNComment]:
    """获取单个评论的详细信息"""
    # 检查缓存
    if cid in _comment_cache:
        logger.debug(f"从缓存获取评论：ID={cid}")
        return _comment_cache[cid]

    try:
        logger.debug(f"正在获取评论：ID={cid}")
        r = await client.get(HN_ITEM_URL.format(cid), timeout=10)
        r.raise_for_status()
        data = r.json()
        
        if not data or data.get("type") != "comment":
            logger.warning(f"评论 {cid} 数据无效或类型错误")
            _comment_cache[cid] = None
            return None

        comment = HNComment(
            id=cid,
            text=data.get("text", ""),
            by=data.get("by", ""),
            time=datetime.fromtimestamp(data.get("time", 0), tz=TZ_LOCAL),
            parent=data.get("parent", 0),
            kids=data.get("kids"),
        )
        _comment_cache[cid] = comment
        logger.debug(f"成功获取评论：ID={cid}, 作者={comment.by}")
        return comment
    except Exception as e:
        logger.warning(f"获取评论 {cid} 失败: {e}")
        _comment_cache[cid] = None
        return None


async def fetch_comments_for_story(
    client: httpx.AsyncClient,
    story_id: int,
    comment_ids: List[int],
    max_comments: int = 10,
) -> List[HNComment]:
    """获取故事的评论列表，包括部分子评论"""
    comments: List[HNComment] = []
    if not comment_ids:
        logger.info(f"故事 {story_id} 无评论")
        return comments

    # 限制获取的评论数量，避免过多请求
    limited_ids = comment_ids[:max_comments]
    logger.info(f"故事 {story_id} 开始获取 {len(limited_ids)} 条评论")

    sem = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

    async def fetch(cid):
        async with sem:
            await asyncio.sleep(random.uniform(0.1, 0.3))  # 避免请求过快
            return await fetch_comment_details(client, cid)

    tasks = [fetch(cid) for cid in limited_ids]
    results = await asyncio.gather(*tasks)

    for res in results:
        if isinstance(res, HNComment):
            comments.append(res)
            # 如果有子评论，也获取一部分
            if res.kids and len(comments) < max_comments:
                child_comments = await fetch_comments_for_story(
                    client, story_id, res.kids, max_comments - len(comments)
                )
                comments.extend(child_comments)

    logger.info(f"故事 {story_id} 成功获取 {len(comments)} 条评论")
    return comments[:max_comments]


async def fetch_story_details(client: httpx.AsyncClient, sid: int) -> Optional[HNStory]:
    """获取单个故事的详细信息，包括评论"""
    # 检查缓存
    if sid in _story_cache:
        logger.debug(f"从缓存获取故事：ID={sid}")
        return _story_cache[sid]

    try:
        logger.debug(f"正在获取故事：ID={sid}")
        r = await client.get(HN_ITEM_URL.format(sid), timeout=10)
        r.raise_for_status()
        data = r.json()
        
        if not data or data.get("type") != "story":
            logger.warning(f"故事 {sid} 数据无效或类型错误")
            _story_cache[sid] = None
            return None

        story = HNStory(
            id=sid,
            title=data.get("title", ""),
            url=data.get("url"),
            hn_url=f"https://news.ycombinator.com/item?id={sid}",
            score=data.get("score", 0),
            by=data.get("by", ""),
            time=datetime.fromtimestamp(data.get("time", 0), tz=TZ_LOCAL),
            descendants=data.get("descendants", 0),
            text=data.get("text"),
            category=_get_story_category(data.get("title", ""), data.get("url")),
            comments=None,
            comment_summary=None,
        )

        # 获取评论
        if data.get("kids") and len(data.get("kids", [])) > 0:
            logger.info(f"故事 {sid} 有 {len(data.get('kids', []))} 条评论，开始获取")
            story.comments = await fetch_comments_for_story(
                client, sid, data.get("kids", []), max_comments=10
            )
        else:
            logger.info(f"故事 {sid} 无评论")

        _story_cache[sid] = story
        logger.info(f"成功获取故事：ID={sid}, 标题={story.title[:50]}...")
        return story
    except Exception as e:
        logger.warning(f"获取故事 {sid} 失败: {e}")
        _story_cache[sid] = None
        return None


async def fetch_story_ids(story_type: str = "top") -> List[int]:
    """获取故事 ID 列表"""
    url = {"top": HN_TOP_STORIES_URL, "new": HN_NEW_STORIES_URL}[story_type]
    logger.info(f"正在获取 {story_type} 故事列表...")
    
    async with httpx.AsyncClient() as c:
        r = await c.get(url, timeout=10)
        r.raise_for_status()
        ids = r.json()
        logger.info(f"成功获取 {len(ids)} 个故事 ID")
        return ids


async def collect_recent_stories_async(
    hours: int, max_stories: int, story_type: str = "top", min_score: int = 10
) -> List[HNStory]:
    """
    收集指定时间范围内的热门故事
    """
    start = time.time()
    cutoff = datetime.now(TZ_LOCAL) - timedelta(hours=hours)
    logger.info(f"时间筛选：获取 {hours} 小时内的故事（截止时间：{cutoff:%F %T}）")
    logger.info(f"最低分数要求：{min_score}")

    ids = await fetch_story_ids(story_type)
    if not ids:
        logger.warning("未获取到任何故事 ID")
        return []

    # 并发拉取，控制并发数量
    sem = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

    async def fetch(sid):
        async with sem:
            await asyncio.sleep(random.uniform(0.1, 0.3))  # 避免请求过快
            return await fetch_story_details(session, sid)

    stories: List[HNStory] = []
    async with httpx.AsyncClient() as session:
        for i in range(0, len(ids), 50):  # 每批处理 50 个
            batch = ids[i : i + 50]
            logger.info(f"处理批次 {i//50 + 1}：故事 ID {batch[0]} - {batch[-1]}")
            
            tasks = [fetch(sid) for sid in batch]
            for res in await asyncio.gather(*tasks):
                if (
                    isinstance(res, HNStory)
                    and res.time >= cutoff
                    and res.score >= min_score
                ):
                    stories.append(res)
                    logger.info(f"符合条件的故事：{res.title[:50]}... (分数: {res.score})")
            
            if len(stories) >= max_stories:
                logger.info(f"已收集到 {len(stories)} 个故事，达到目标数量")
                break
            await asyncio.sleep(random.uniform(0.5, 1.0))  # 批次间延迟

    stories.sort(key=lambda s: s.score, reverse=True)
    final_stories = stories[:max_stories]
    logger.info(f"收集完成：{len(final_stories)} 个故事，耗时 {time.time()-start:.1f} 秒")
    return final_stories


def openai_client(api_key=None, base_url=None) -> Optional[OpenAI]:
    """创建 OpenAI 客户端"""
    key = api_key or AI_API_KEY
    url = base_url or AI_BASE_URL
    if not key or len(key) < 10:
        logger.warning("API Key 无效或过短")
        return None
    try:
        logger.info("正在创建 OpenAI 客户端...")
        client = OpenAI(api_key=key, base_url=url)
        logger.info("OpenAI 客户端创建成功")
        return client
    except Exception as e:
        logger.error(f"创建 OpenAI 客户端失败: {e}")
        return None


def generate_local_summary(story: HNStory) -> str:
    """生成本地摘要（兜底方案）"""
    return story.title if len(story.title) <= 60 else story.title[:57] + "..."

def ai_summarize_comments(client: OpenAI, model: str, story: HNStory) -> str:
    """使用 AI 总结故事的评论"""
    if not story.comments or len(story.comments) == 0:
        logger.info(f"故事 {story.id} 无评论，跳过总结")
        return "暂无有价值的评论"

    logger.info(f"开始总结故事 {story.id} 的 {len(story.comments)} 条评论")

    # 提取评论文本（去除HTML标签）
    comment_texts = []
    for comment in story.comments:
        if comment.text:
            # 简单去除HTML标签
            clean_text = re.sub(r"<.*?>", "", comment.text)
            comment_texts.append(f"用户{comment.by}：{clean_text}")

    if not comment_texts:
        logger.warning(f"故事 {story.id} 评论文本为空")
        return "暂无有价值的评论"

    system = "你是专业评论摘要助手，请用中文 30 字左右总结以下HN评论的主要观点和讨论焦点，不添加个人观点，不输出markdown，只要重要的观点"
    user = "评论列表：\n" + "\n".join(comment_texts)

    payload = dict(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.3,
        top_p=0.8,
    )

    for retry in range(3):
        try:
            logger.debug(f"故事 {story.id} 评论总结第 {retry+1} 次尝试")
            resp = client.chat.completions.create(**payload)
            summary = re.sub(r"\s+", " ", resp.choices[0].message.content).strip()
            logger.info(f"故事 {story.id} 评论总结成功")
            return summary
        except Exception as e:
            wait = 2**retry
            logger.warning(f"故事 {story.id} 评论总结失败（重试 {retry+1}/3）: {e} -> 等待 {wait}s")
            time.sleep(wait)
    
    logger.error(f"故事 {story.id} 评论总结多次失败")
    return ""


async def batch_ai_summarize_async(
    stories: List[HNStory], api_key: str, model: str
) -> List[HNStory]:
    """批量 AI 总结评论"""
    if not stories:
        logger.warning("无故事需要总结")
        return []
    
    logger.info(f"开始批量总结 {len(stories)} 个故事的评论")
    client = openai_client(api_key)
    if not client:
        logger.error("无法创建 AI 客户端，跳过评论总结")
        return stories
    
    sem = asyncio.Semaphore(MAX_CONCURRENT_AI)

    async def do(story, idx):
        async with sem:
            await asyncio.sleep(random.uniform(0.2, 0.5))  # 避免请求过快
            loop = asyncio.get_event_loop()

            # 只总结评论
            if story.comments and len(story.comments) > 0:
                logger.info(f"正在总结故事 {idx}/{len(stories)}：{story.title[:30]}...")
                comment_summary = await loop.run_in_executor(
                    None, ai_summarize_comments, client, model, story
                )
                story.comment_summary = comment_summary
            else:
                logger.info(f"故事 {idx}/{len(stories)} 无评论，跳过总结")

            return story

    tasks = [do(s, i) for i, s in enumerate(stories, 1)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    ok = [r for r in results if isinstance(r, HNStory)]
    logger.info(f"评论总结完成：成功 {len(ok)}/{len(stories)} 个故事")
    return ok


def render_markdown_report(
    date_label: str, stories: List[HNStory]
) -> str:
    """生成 Markdown 格式的早报"""
    if not stories:
        logger.warning("无故事数据，生成空报告")
        return f"# Hacker News 早报（{date_label}）\n暂无内容"
    
    logger.info(f"开始生成早报，包含 {len(stories)} 个故事")
    lines = [
        f"# Hacker News 早报（{date_label}）",
    ]
    
    for i, story in enumerate(stories, 1):
        # 添加评论总结
        if story.comment_summary:
            lines.append(f"> {story.comment_summary}")
            logger.debug(f"添加故事 {i} 的评论摘要")
        else:
            logger.debug(f"故事 {i} 无评论摘要")
        lines.append(f"讨论：{story.hn_url}")
    
    report = "\n".join(lines)
    logger.info(f"早报生成完成，总长度：{len(report)} 字符")
    return report


# 配置参数
DEFAULT_HOURS = 24  # 默认获取24小时内的故事
DEFAULT_MAX_STORIES = 10  # 默认最多10个故事
DEFAULT_MODEL = "glm-4-flash"  # 默认AI模型
DEFAULT_CONCURRENT = True  # 默认使用并发模式
MAX_CONCURRENT_REQUESTS = 15  # 最大并发请求数
MAX_CONCURRENT_AI = 20  # AI接口最大并发数


async def main_async(
    hours: int = DEFAULT_HOURS,
    max_stories: int = DEFAULT_MAX_STORIES,
    model: str = DEFAULT_MODEL,
    story_type: str = "top",
    min_score: int = 10,
):
    """主异步函数"""
    logger.info("=" * 60)
    logger.info("🚀 开始执行 Hacker News 早报任务")
    logger.info(f"📊 配置：{hours}小时内，最多{max_stories}个故事，最低分数{min_score}")
    logger.info("=" * 60)
    
    # 步骤1：收集故事
    logger.info("【步骤1】开始爬取 Hacker News 故事")
    stories = await collect_recent_stories_async(
        hours, max_stories, story_type, min_score
    )
    if not stories:
        logger.warning("❌ 未获取到任何故事，任务结束")
        return

    logger.info(f"✅ 成功获取 {len(stories)} 个故事")

    # 步骤2：AI 总结评论
    logger.info("=" * 60)
    logger.info("【步骤2】开始 AI 总结评论")
    logger.info("=" * 60)
    summarized_stories = await batch_ai_summarize_async(stories, AI_API_KEY, model)

    # 步骤3：生成报告
    logger.info("=" * 60)
    logger.info("【步骤3】生成早报")
    logger.info("=" * 60)
    date = datetime.now(TZ_LOCAL).strftime("%F")
    md = render_markdown_report(date, summarized_stories)

    # 发送通知
    logger.info("=" * 60)
    logger.info("【步骤4】发送通知")
    logger.info("=" * 60)
    try:
        logger.info("📤 正在发送早报通知...")
        QLAPI.notify("Hacker News 早报", md)
        logger.info("✅ 早报通知发送成功")
    except Exception as e:
        logger.error(f"❌ 发送通知失败: {e}")
    
    logger.info("🎉 Hacker News 早报任务完成！")


def main():
    """主函数入口"""
    logger.info("🎯 启动 Hacker News 早报脚本")
    try:
        asyncio.run(main_async())
    except Exception as e:
        logger.error(f"💥 脚本执行失败: {e}")
        raise


if __name__ == "__main__":
    main()