"""
题三：热点发现 - 信息源抓取模块（稳定版·多源覆盖）

从多个真实信息源抓取热点资讯，确保多来源覆盖：
    - 海外英文 RSS：Hacker News、TechCrunch（已验证可用）
    - 国内中文 RSS：InfoQ中文（已验证可用）
    - 开源趋势：GitHub Trending（已验证可用）
    - 国内备选：澎湃新闻、V2Ex（本地 Windows 通常可访问）
    - 热门话题：RSSHub 多实例轮询（知乎/微博/百度）

降级策略：
    1) RSSHub 不可用 → 轮询备用实例
    2) 全部失败 → Hacker News 官方 API

对外接口：
    fetch_all(max_items=30) -> list[dict]
"""
import time

import requests

# 浏览器级 User-Agent
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
}

# RSSHub 备用实例
RSSHUB_INSTANCES = [
    "https://rsshub.app",
    "https://rsshub.rssforever.com",
    "https://rsshub.feeded.xyz",
]

# 稳定 RSS 源（已逐个验证可用性）
RSS_SOURCES = [
    # 海外英文源（已验证可用）
    {"name": "Hacker News", "url": "https://hnrss.org/frontpage", "source": "Hacker News"},
    {"name": "TechCrunch", "url": "https://techcrunch.com/feed/", "source": "TechCrunch"},
    # 国内中文源（已验证可用）
    {"name": "InfoQ中文", "url": "https://www.infoq.cn/feed", "source": "InfoQ"},
    # 开源趋势（已验证可用）
    {"name": "GitHub Trending", "url": "https://mshibanami.github.io/GitHubTrendingRSS/daily/all.xml", "source": "GitHub"},
    # 国内备选源（本地 Windows 通常可访问，沙箱可能 SSL 受限）
    {"name": "澎湃新闻", "url": "https://feedx.net/rss/pengpai.xml", "source": "澎湃新闻"},
    {"name": "V2Ex", "url": "https://www.v2ex.com/index.xml", "source": "V2Ex"},
]

# 热门话题榜（通过 RSSHub，多实例轮询）
HOT_TOPIC_ROUTES = [
    {"name": "知乎热榜", "route": "/zhihu/hotlist", "source": "知乎"},
    {"name": "微博热搜", "route": "/weibo/search/hot", "source": "微博"},
    {"name": "百度热搜", "route": "/baidu/topwords", "source": "百度"},
]


def _parse_rss(xml_text: str, source: str) -> list:
    """简单解析 RSS/Atom XML"""
    items = []
    try:
        from xml.etree import ElementTree as ET
        root = ET.fromstring(xml_text)

        for item in root.findall(".//item"):
            title = item.findtext("title", default="")
            link = item.findtext("link", default="")
            desc = item.findtext("description", default="")
            items.append({
                "title": title.strip() if title else "",
                "url": link.strip() if link else "",
                "summary": (desc.strip()[:200]) if desc else "",
                "source": source,
            })

        if not items:
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            for entry in root.findall(".//atom:entry", ns):
                title = entry.findtext("atom:title", default="", namespaces=ns)
                link_el = entry.find("atom:link", ns)
                link = link_el.get("href", "") if link_el is not None else ""
                summary = entry.findtext("atom:summary", default="", namespaces=ns)
                items.append({
                    "title": title.strip() if title else "",
                    "url": link.strip() if link else "",
                    "summary": (summary or "")[:200],
                    "source": source,
                })
    except Exception as e:
        print(f"  [RSS解析错误] {source}: {e}")

    return items


def _fetch_rss(url: str, source: str, timeout: int = 10) -> list:
    """抓取单个 RSS 源"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout)
        resp.raise_for_status()
        return _parse_rss(resp.text, source)
    except Exception as e:
        print(f"  [提示] RSS 源 {url} 不可用: {e}")
        return []


def _fetch_rsshub_with_fallback(route: str, source: str, timeout: int = 10) -> list:
    """轮询多个 RSSHub 实例"""
    for base in RSSHUB_INSTANCES:
        url = f"{base}{route}"
        items = _fetch_rss(url, source, timeout=timeout)
        if items:
            return items
    return []


def _fetch_hn_api() -> list:
    """Hacker News 官方 API 降级方案"""
    items = []
    try:
        resp = requests.get(
            "https://hacker-news.firebaseio.com/v0/topstories.json",
            headers=HEADERS, timeout=10
        )
        ids = resp.json()[:15]
        for id in ids:
            r = requests.get(
                f"https://hacker-news.firebaseio.com/v0/item/{id}.json",
                headers=HEADERS, timeout=5
            )
            d = r.json()
            items.append({
                "title": d.get("title", ""),
                "url": d.get("url", f"https://news.ycombinator.com/item?id={id}"),
                "summary": "",
                "source": "Hacker News",
            })
    except Exception as e:
        print(f"  [HN API 降级失败]: {e}")
    return items


def fetch_all(max_items: int = 30) -> list:
    """抓取多个信息源，合并去重后返回。

    优先用多源 RSS（海外+国内），全部失败则降级到 HN 官方 API。
    """
    all_items = []

    # 先抓 RSS 源
    for src in RSS_SOURCES:
        print(f"  正在抓取 {src['name']}...")
        items = _fetch_rss(src["url"], src["source"])
        if items:
            print(f"    ✅ 获取 {len(items)} 条")
        all_items.extend(items)
        time.sleep(0.3)

    # 再抓 RSSHub 热门话题
    for src in HOT_TOPIC_ROUTES:
        print(f"  正在抓取 {src['name']}...")
        items = _fetch_rsshub_with_fallback(src["route"], src["source"])
        if items:
            print(f"    ✅ 获取 {len(items)} 条")
        all_items.extend(items)
        time.sleep(0.3)

    # 降级
    if not all_items:
        print("  RSS 抓取失败，降级到 Hacker News 官方 API...")
        all_items = _fetch_hn_api()

    # 去重
    seen = set()
    unique = []
    for it in all_items:
        key = it["title"][:50]
        if key not in seen:
            seen.add(key)
            unique.append(it)

    # 均分各来源，保证多源覆盖
    from collections import OrderedDict
    by_source = OrderedDict()
    for it in unique:
        by_source.setdefault(it["source"], []).append(it)

    result = []
    queues = list(by_source.values())
    idx = 0
    while len(result) < max_items and queues:
        all_empty = True
        for q in queues:
            if idx < len(q):
                result.append(q[idx])
                all_empty = False
                if len(result) >= max_items:
                    break
        if all_empty:
            break
        idx += 1

    return result
