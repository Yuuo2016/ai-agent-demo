"""热点数据源模块 - 抓取多个真实信息源（RSS/GitHub/Reddit）"""
import feedparser
import requests
from datetime import datetime, timedelta

DEFAULT_RSS_FEEDS = [
    "https://36kr.com/feed",
    "https://www.jiqizhixin.com/rss",
    "https://feeds.feedburner.com/TheHackerNews",
    "https://hnrss.org/frontpage",
    "https://www.reddit.com/r/technology/.rss",
    "https://www.reddit.com/r/artificial/.rss",
]
GITHUB_TRENDING_LANGS = ["python", "javascript", "typescript"]


def fetch_rss(feeds=None, limit_per_feed: int = 5, timeout: int = 8) -> list:
    feeds = feeds or DEFAULT_RSS_FEEDS
    items = []
    for url in feeds:
        try:
            resp = requests.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
            parsed = feedparser.parse(resp.content)
            for entry in parsed.entries[:limit_per_feed]:
                items.append({"title": entry.get("title", "").strip(), "url": entry.get("link", ""), "source": parsed.feed.get("title", url), "summary": (entry.get("summary", "") or "")[:300], "published": entry.get("published", "")})
        except Exception as e:
            print(f"[警告] RSS 抓取失败 {url}: {e}")
    return items


def fetch_github_trending(days: int = 7, limit: int = 10) -> list:
    items = []
    headers = {"Accept": "application/vnd.github+json"}
    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    for lang in GITHUB_TRENDING_LANGS:
        try:
            url = f"https://api.github.com/search/repositories?q=created:>{since}+language:{lang}&sort=stars&order=desc&per_page=5"
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            for repo in resp.json().get("items", [])[:limit]:
                items.append({"title": f"[GitHub] {repo['full_name']}", "url": repo["html_url"], "source": "GitHub Trending", "summary": (repo.get("description") or "")[:300], "published": repo.get("created_at", "")})
        except Exception as e:
            print(f"[警告] GitHub 抓取失败 {lang}: {e}")
    return items


def fetch_all(max_items: int = 30) -> list:
    items = fetch_rss() + fetch_github_trending()
    seen = set()
    result = []
    for it in items:
        key = it["title"].strip().lower()
        if key and key not in seen:
            seen.add(key)
            result.append(it)
    return result[:max_items]
