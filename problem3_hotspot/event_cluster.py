import re
from datetime import datetime

# 来源类型 → 权威分（可量化字典，可自行增删）
SOURCE_TYPE_SCORE = {
    "官方机构/企业官网/政务": 0.95,
    "权威媒体(TheVerge/彭博/路透/央视/新华社)": 0.85,
    "科技媒体(机器之心/36氪/IT之家)": 0.75,
    "社区论坛(Reddit/HN)": 0.55,
    "个人博客/自媒体": 0.45,
    "未知": 0.40,
}

# 关键词停用词（聚类时忽略）
STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "for", "on", "with",
    "at", "by", "from", "as", "is", "are", "was", "were", "be", "been",
    "it", "its", "this", "that", "these", "those", "new", "news", "how",
    "what", "why", "who", "2026", "2025", "ai", "用", "的", "了", "和",
}


def _tokenize(title: str) -> set:
    """从标题提取关键词集合（英文按空格切分并去停用词，中文按2字以上词）"""
    title = (title or "").lower()
    en_words = {w for w in re.findall(r"[a-z]+", title) if w not in STOPWORDS and len(w) > 2}
    cn_chars = re.findall(r"[\u4e00-\u9fff]+", title)
    cn_words = set()
    for seg in cn_chars:
        for i in range(len(seg) - 1):
            cn_words.add(seg[i:i + 2])
    return en_words | cn_words


def _jaccard(a: set, b: set) -> float:
    """Jaccard 相似度：交集 / 并集"""
    if not a or not b:
        return 0.0
    inter = len(a & b)
    if inter == 0:
        return 0.0
    return inter / len(a | b)


def cluster_by_similarity(items: list, threshold: float = 0.18) -> list:
    """把相似报道聚为同一事件。"""
    tokens = [_tokenize(it.get("title", "")) for it in items]
    n = len(items)
    used = [False] * n
    events = []
    for i in range(n):
        if used[i]:
            continue
        group = [items[i]]
        used[i] = True
        for j in range(i + 1, n):
            if not used[j] and _jaccard(tokens[i], tokens[j]) >= threshold:
                group.append(items[j])
                used[j] = True
        events.append(group)
    return events


def infer_source_type(source: str) -> str:
    """根据来源名推断来源类型（用于查权威分）"""
    s = (source or "").lower().replace(" ", "").replace("-", "")
    if any(k in s for k in ["openai", "google", "microsoft", "meta", "anthropic",
                            "github", "apple", "aws", "gov", "official", "华为", "官方"]):
        return "官方机构/企业官网/政务"
    if any(k in s for k in ["theverge", "bloomberg", "reuters", "bbc", "cnn",
                            "nytimes", "wsj", "央视", "新华社", "汤森"]):
        return "权威媒体(TheVerge/彭博/路透/央视/新华社)"
    if any(k in s for k in ["机器之心", "36氪", "it之家", "量子位", "新智元", "极客公园", "sina", "sohu"]):
        return "科技媒体(机器之心/36氪/IT之家)"
    if any(k in s for k in ["reddit", "hackernews", "hn", "论坛", "社区"]):
        return "社区论坛(Reddit/HN)"
    if any(k in s for k in ["博客", "blog", "medium", "substack", "个人"]):
        return "个人博客/自媒体"
    return "未知"


def source_authority_score(source: str) -> float:
    """来源权威分（查字典）"""
    return SOURCE_TYPE_SCORE.get(infer_source_type(source), 0.40)


def cross_validation_factor(event_len: int) -> float:
    """交叉印证系数：同一事件被 N 家独立来源报道，可信度随 N 提升（封顶 1.3）"""
    if event_len <= 1:
        return 1.0
    return min(1.0 + 0.1 * (event_len - 1), 1.3)


def _freshness_factor(published: str) -> float:
    """时效系数：今天报道=1.0，越旧越低（最低 0.7）"""
    if not published:
        return 1.0
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", published)
    if not m:
        return 1.0
    try:
        dt = datetime.strptime(m.group(0), "%Y-%m-%d")
        days_old = (datetime.now() - dt).days
        if days_old <= 0:
            return 1.0
        return max(1.0 - 0.05 * days_old, 0.7)
    except Exception:
        return 1.0


def compute_credibility(event: list) -> dict:
    """计算一个事件的综合可信度（可量化）。"""
    if not event:
        return {"score": 0, "explain": "无数据"}
    authority = sum(source_authority_score(it.get("source", "")) for it in event) / len(event)
    cross = cross_validation_factor(len(event))
    freshness = max(_freshness_factor(it.get("published", "")) for it in event)
    raw = authority * cross * freshness
    score = round(raw * 10, 1)
    explain = (
        f"来源权威 {authority:.2f} × 交叉印证×{cross:.2f}（{len(event)}家来源）"
        f" × 时效×{freshness:.2f} = {score:.1f}/10"
    )
    return {
        "score": score,
        "authority": round(authority, 2),
        "cross_factor": round(cross, 2),
        "freshness": round(freshness, 2),
        "sources_count": len(event),
        "explain": explain,
    }


def represent_event(event: list) -> dict:
    """把聚类后的事件转为统一表示（取主报道 + 可信度）。"""
    if not event:
        return None
    main = event[0]
    cred = compute_credibility(event)
    return {
        "title": main.get("title", ""),
        "url": main.get("url", ""),
        "source": main.get("source", ""),
        "summary": main.get("summary", ""),
        "published": main.get("published", ""),
        "related": [it.get("url", "") for it in event[1:]],
        "sources_count": len(event),
        "all_sources": sorted({it.get("source", "") for it in event}),
        "credibility": cred,
    }


def merge_events(items: list, threshold: float = 0.18) -> list:
    """完整流程：抓取条目 → 聚类 → 返回事件表示（含可信度）。"""
    events = cluster_by_similarity(items, threshold=threshold)
    result = []
    for ev in events:
        rep = represent_event(ev)
        if rep:
            result.append(rep)
    return result
