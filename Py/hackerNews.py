"""
Hacker News 早报（AI 早报工程风格重构）
name: Hacker News早报
cron: 0 7,20 * * *
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

ZHIPU_API_KEY = env.get_env("ZHIPU_API_KEY")[0]
ZHIPU_BASE_URL = env.get_env("ZHIPU_BASE_URL")[0]

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

# 关键词略，与原 HN 早报保持一致（AI_KEYWORDS / TECH_KEYWORDS 等）
# 为节省篇幅这里省略，实际使用时请把原关键词列表粘进来


@dataclass
class HNStory:
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


def _get_story_category(title: str, url: Optional[str]) -> str:
    # 与原 HN 早报完全一致，省略
    ...


# 缓存（简单 dict）
_story_cache: Dict[int, Optional[HNStory]] = {}


async def fetch_story_details(client: httpx.AsyncClient, sid: int) -> Optional[HNStory]:
    if sid in _story_cache:
        return _story_cache[sid]

    try:
        r = await client.get(HN_ITEM_URL.format(sid), timeout=10)
        r.raise_for_status()
        data = r.json()
        if not data or data.get("type") != "story":
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
        )
        _story_cache[sid] = story
        return story
    except Exception as e:
        logger.warning(f"fetch story {sid} failed: {e}")
        _story_cache[sid] = None
        return None


async def fetch_story_ids(story_type: str = "top") -> List[int]:
    url = {"top": HN_TOP_STORIES_URL, "new": HN_NEW_STORIES_URL}[story_type]
    async with httpx.AsyncClient() as c:
        r = await c.get(url, timeout=10)
        r.raise_for_status()
        return r.json()


async def collect_recent_stories_async(
    hours: int, max_stories: int, story_type: str = "top", min_score: int = 10
) -> List[HNStory]:
    """
    对齐 AI 早报的 collect_recent_articles_async
    """
    start = time.time()
    cutoff = datetime.now(TZ_LOCAL) - timedelta(hours=hours)
    logger.info(f"cutoff: {cutoff:%F %T}")

    ids = await fetch_story_ids(story_type)
    if not ids:
        return []

    # 并发拉取
    sem = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

    async def fetch(sid):
        async with sem:
            await asyncio.sleep(random.uniform(0.1, 0.3))
            return await fetch_story_details(session, sid)

    stories: List[HNStory] = []
    async with httpx.AsyncClient() as session:
        for i in range(0, len(ids), 50):
            batch = ids[i : i + 50]
            tasks = [fetch(sid) for sid in batch]
            for res in await asyncio.gather(*tasks):
                if (
                    isinstance(res, HNStory)
                    and res.time >= cutoff
                    and res.score >= min_score
                ):
                    stories.append(res)
            if len(stories) >= max_stories:
                break
            await asyncio.sleep(random.uniform(0.5, 1.0))

    stories.sort(key=lambda s: s.score, reverse=True)
    logger.info(f"collect done: {len(stories)} stories in {time.time()-start:.1f}s")
    return stories[:max_stories]


def openai_client(api_key=None, base_url=None) -> Optional[OpenAI]:
    key = api_key or ZHIPU_API_KEY
    url = base_url or ZHIPU_BASE_URL
    if not key or len(key) < 10:
        logger.warning("invalid api key")
        return None
    try:
        return OpenAI(api_key=key, base_url=url)
    except Exception as e:
        logger.error(f"openai client error: {e}")
        return None


def generate_local_summary(story: HNStory) -> str:
    return story.title if len(story.title) <= 60 else story.title[:57] + "..."


def ai_summarize_story(client: OpenAI, model: str, story: HNStory) -> str:
    system = "你是专业科技摘要助手，请用中文 10-40 字完整句子总结 HN 故事，不添加观点，不输出 markdown"
    user = f"标题：{story.title}\n分类：{story.category}"
    payload = dict(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.2,
        top_p=0.8,
    )
    for retry in range(3):
        try:
            resp = client.chat.completions.create(**payload)
            summary = re.sub(r"\s+", " ", resp.choices[0].message.content).strip()
            return summary or generate_local_summary(story)
        except Exception as e:
            wait = 2**retry
            logger.warning(f"ai retry {retry+1}: {e} -> sleep {wait}s")
            time.sleep(wait)
    return generate_local_summary(story)


async def batch_ai_summarize_async(
    stories: List[HNStory], api_key: str, model: str
) -> List[Tuple[HNStory, str]]:
    if not stories:
        return []
    client = openai_client(api_key)
    sem = asyncio.Semaphore(MAX_CONCURRENT_AI)

    async def do(story, idx):
        async with sem:
            await asyncio.sleep(random.uniform(0.2, 0.5))
            loop = asyncio.get_event_loop()
            summary = await loop.run_in_executor(
                None, ai_summarize_story, client, model, story
            )
            return (story, summary)

    tasks = [do(s, i) for i, s in enumerate(stories, 1)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    ok = [r for r in results if isinstance(r, tuple)]
    logger.info(f"ai summarize done: {len(ok)}/{len(stories)}")
    return ok


def render_markdown_report(
    date_label: str, summarized: List[Tuple[HNStory, str]]
) -> str:
    if not summarized:
        return f"# Hacker News 早报（{date_label}）\n\n暂无内容"
    lines = [
        f"# Hacker News 早报（{date_label}）",
        f"**本期收录 {len(summarized)} 条热门故事**",
    ]
    for story, summary in summarized:
        lines += [
            f"### {summary}",
            "",
            f"🔺 {story.score}  💬 {story.descendants}  👤 {story.by}  🏷️ {story.category}",
            "",
        ]
        if story.url:
            lines.append(f"原文：[{story.url}]({story.url})")
        lines.append(f"讨论：[Hacker News]({story.hn_url})")
    return "\n".join(lines)


DEFAULT_HOURS = 24
DEFAULT_MAX_STORIES = 15
DEFAULT_MODEL = "glm-4-flash"
DEFAULT_CONCURRENT = True
MAX_CONCURRENT_REQUESTS = 15
MAX_CONCURRENT_AI = 20


async def main_async(
    hours: int = DEFAULT_HOURS,
    max_stories: int = DEFAULT_MAX_STORIES,
    model: str = DEFAULT_MODEL,
    story_type: str = "top",
    min_score: int = 10,
):
    logger.info("=" * 60)
    logger.info("【1】开始爬取 Hacker News")
    logger.info("=" * 60)
    stories = await collect_recent_stories_async(
        hours, max_stories, story_type, min_score
    )
    if not stories:
        logger.warning("未获取到任何故事")
        return

    logger.info("=" * 60)
    logger.info("【2】开始 AI 总结")
    logger.info("=" * 60)
    summarized = await batch_ai_summarize_async(stories, ZHIPU_API_KEY, model)

    logger.info("=" * 60)
    logger.info("【3】生成报告")
    logger.info("=" * 60)
    date = datetime.now(TZ_LOCAL).strftime("%F")
    md = render_markdown_report(date, summarized)

    # 如需发送到通知渠道，可在此处调用 QLAPI.systemNotify(...)
    logger.info(md)
    QLAPI.systemNotify({"title": "AIBase 文章总结报告", "content": md})
    logger.info("done")


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
