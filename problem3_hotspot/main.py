"""
题三：热点发现 Agent（Hot Topic Discovery Agent）

完整工作流：
    监控数据源 → 合并同一事件(聚类) → AI 筛选/总结观点/价值判断 + 可信度评估
    → 人工审核 → 多渠道推送(飞书/邮件，企业微信默认不发)

覆盖题目要求 + 加分项：
    - 自动发现热点 / AI 筛选 / 摘要 / 推送
    - 合并同一事件（关键词相似度聚类）
    - 总结不同观点 / 评估可信度（可量化：来源权威 × 交叉印证 × 时效）
    - 多渠道推送（飞书 + SMTP 邮件，企业微信默认不发）

运行方式：
    python problem3_hotspot/main.py
"""
import os
import sys
import json
from datetime import datetime

# 允许从项目根目录导入 common
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common import llm
from review_items import review_items
from sources import fetch_all
from event_cluster import merge_events


def ai_filter_and_summarize(events: list, top_n: int = 5) -> list:
    """用 AI 对事件聚类后的热点进行筛选、观点总结与价值判断。

    每个事件已含可量化可信度(credibility)，本函数补充：
        summary(整合摘要)、viewpoints(不同观点)、value(价值分)、reason(理由)

    Args:
        events: 事件列表，每个含 title/url/source/sources_count/all_sources/credibility
        top_n: 保留的热点数

    Returns:
        增强后的事件列表
    """
    # 构造输入给 LLM 的候选列表（含各来源与可信度）
    # 给每个候选分配序号(idx)，方便 AI 输出后精确匹配回原始事件
    candidates = []
    for idx, ev in enumerate(events):
        cred = ev.get("credibility", {})
        candidates.append({
            "idx": idx,
            "title": ev.get("title", ""),
            "source": ev.get("source", ""),
            "all_sources": ev.get("all_sources", []),
            "sources_count": ev.get("sources_count", 1),
            "credibility": cred.get("score", 0),
            "summary": ev.get("summary", ""),
        })

    messages = [
        {
            "role": "system",
            "content": (
                "你是海外 AI 产品增长运营专家。请从候选热点中挑选出对"
                "「AI 产品出海增长、内容运营、财经科技趋势」最有价值的 TOP 热点。"
                "对每个热点输出：idx(原样回填候选序号)、title(标题)、source(原样回填来源名)、"
                "summary(1-2句中文整合摘要)、"
                "viewpoints(数组，列出不同来源/立场的观点，每项含 source 与 view)、"
                "value(0-10 价值分)、reason(入选理由)。"
                "注意：idx 和 source 必须原样回填，不要修改。只输出 JSON 数组。"
            ),
        },
        {
            "role": "user",
            "content": f"以下为今日抓取并聚类后的候选热点（含可信度评分），请筛选最有价值的 {top_n} 条：\n"
            + json.dumps(candidates, ensure_ascii=False, indent=2),
        },
    ]

    try:
        result = llm.chat_json(messages, temperature=0.2, max_tokens=3000)
        if isinstance(result, dict):
            result = result.get("hotspots") or result.get("items") or []
        # 把 LLM 输出与原始事件合并（用 idx 精确匹配，补回 source/url/credibility）
        by_idx = {i: ev for i, ev in enumerate(events)}
        by_title = {ev.get("title", ""): ev for ev in events}
        enriched = []
        for r in result[:top_n]:
            # 优先用 idx 匹配，回退到标题匹配
            ev = {}
            if r.get("idx") is not None and r["idx"] in by_idx:
                ev = by_idx[r["idx"]]
            else:
                ev = by_title.get(r.get("title", ""), {})
            # 强制补回原始事件的字段（AI 可能丢失或改写）
            r["source"] = r.get("source") or ev.get("source", "")
            r["url"] = r.get("url") or ev.get("url", "")
            r["credibility"] = ev.get("credibility", {})
            r["sources_count"] = ev.get("sources_count", 1)
            r["all_sources"] = ev.get("all_sources", [])
            r["related"] = ev.get("related", [])
            enriched.append(r)
        return enriched
    except Exception as e:
        print(f"[错误] AI 筛选失败: {e}")
        # 兜底：直接返回前几条事件数据（附可信度）
        return [
            {
                "title": ev.get("title", ""),
                "url": ev.get("url", ""),
                "source": ev.get("source", ""),
                "summary": ev.get("summary", ""),
                "viewpoints": [],
                "value": 5,
                "reason": "AI 筛选失败，原始数据兜底",
                "credibility": ev.get("credibility", {}),
                "sources_count": ev.get("sources_count", 1),
                "all_sources": ev.get("all_sources", []),
                "related": ev.get("related", []),
            }
            for ev in events[:top_n]
        ]


def format_report(hotspots: list) -> str:
    """把筛选结果格式化为可推送的报告文本（含可信度与观点）"""
    lines = [f"📌 热点发现报告（{datetime.now().strftime('%Y-%m-%d %H:%M')}）", ""]
    for i, h in enumerate(hotspots, 1):
        cred = h.get("credibility", {})
        lines.append(f"{i}. {h.get('title', '')}")
        lines.append(f"   来源: {h.get('source', '')} | 价值: {h.get('value', '')}/10")
        if h.get("summary"):
            lines.append(f"   摘要: {h.get('summary', '')}")
        # 可信度（可量化）
        if cred.get("score") is not None:
            lines.append(f"   可信度: {cred.get('score')}/10 ({cred.get('explain', '')})")
        if h.get("sources_count", 1) > 1:
            lines.append(f"   合并报道: {h.get('sources_count')} 家来源 "
                         f"[{', '.join(h.get('all_sources', []))}]")
        # 不同观点
        if h.get("viewpoints"):
            lines.append("   观点: ")
            for vp in h["viewpoints"]:
                lines.append(f"       - ({vp.get('source', '')}) {vp.get('view', '')}")
        if h.get("reason"):
            lines.append(f"   理由: {h.get('reason', '')}")
        if h.get("url"):
            lines.append(f"   链接: {h.get('url', '')}")
        lines.append("")
    return "\n".join(lines)


def main():
    print("=" * 60)
    print("题三：热点发现 Agent 启动")
    print("=" * 60)

    # 1. 抓取数据源
    print("\n[1/5] 正在抓取数据源...")
    items = fetch_all(max_items=30)
    print(f"      共抓取到 {len(items)} 条候选热点")
    for it in items[:5]:
        print(f"      - {it['title'][:50]}")

    # 2. 合并同一事件（聚类）
    print("\n[2/5] 合并同一事件（聚类）...")
    events = merge_events(items, threshold=0.18)
    print(f"      聚类后得到 {len(events)} 个独立事件")
    for ev in events:
        cred = ev.get("credibility", {})
        print(f"      - [{ev.get('sources_count')}家] {ev.get('title', '')[:45]} "
              f"可信度 {cred.get('score')}/10")

    # 3. AI 筛选 + 观点总结 + 价值判断
    print("\n[3/5] AI 正在筛选、总结观点与价值判断...")
    hotspots = ai_filter_and_summarize(events, top_n=5)
    print(f"      筛选出 {len(hotspots)} 条高价值热点")

    # 4. 逐条人工审核（风险控制）；按 p 完成时统一多渠道推送，e/r 不推送
    print("\n[4/5] 进入逐条人工审核...")
    final = review_items(hotspots, title="热点发现报告")

    if not final:
        print("所有条目均被拒绝，流程结束。")
        return

    # 5. 保存最终报告到本地（推送已在审核完成时执行）
    print("\n[5/5] 保存最终报告到本地...")
    os.makedirs("output", exist_ok=True)
    out_path = f"output/hotspot_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(format_report(final))
    print(f"✅ 已保存 {len(final)} 条热点至 {out_path}")


if __name__ == "__main__":
    main()
