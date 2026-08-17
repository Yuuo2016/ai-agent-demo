"""
题三：热点发现 Agent — Streamlit Web 界面

运行方式：
    streamlit run app3.py

功能：
    - 一键启动热点发现工作流
    - 抓取数据源 → 事件聚类 → AI 筛选/总结/可信度评估
    - 热点审核（可编辑标题/来源/摘要/理由等）
    - 信息源不满意可重新搜索
    - 发布前确认 + 多渠道推送（飞书 + QQ邮箱）
"""
import sys
import os
from datetime import datetime

import streamlit as st

# 自动加载 .env 环境变量
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
except ImportError:
    pass

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common import push
from problem3_hotspot.sources import fetch_all
from problem3_hotspot.event_cluster import merge_events
from problem3_hotspot.main import ai_filter_and_summarize, format_report


def init_page():
    """初始化页面"""
    st.set_page_config(
        page_title="热点发现 Agent",
        page_icon="🔍",
        layout="wide",
    )
    st.title("🔍 题三：热点发现 Agent")
    st.markdown("---")
    st.markdown("抓取数据源 → 事件聚类 → AI 筛选/总结/可信度评估 → 人工审核 → 多渠道推送")


def init_session_state():
    """初始化 session_state"""
    defaults = {
        "p3_step": 0,
        "raw_items": [],
        "events": [],
        "hotspots": [],
        "final_hotspots": [],
        "pushed": False,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def show_sidebar():
    """侧边栏配置与环境检查"""
    with st.sidebar:
        st.header("⚙️ 配置")

        st.markdown("---")
        st.markdown("### 环境检查")

        api_key = os.getenv("LLM_API_KEY", "")
        if api_key and api_key != "sk-xxxxxxxxxxxxxxxx":
            st.success("✅ LLM API Key 已配置")
        else:
            st.error("❌ LLM API Key 未配置，请在 .env 中设置")

        feishu = os.getenv("FEISHU_WEBHOOK", "")
        if feishu:
            st.success("✅ 飞书 Webhook 已配置")
        else:
            st.warning("⚠️ 飞书 Webhook 未配置")

        email = os.getenv("EMAIL_USER", "")
        if email:
            st.success("✅ QQ 邮箱已配置")
        else:
            st.warning("⚠️ QQ 邮箱未配置")

        st.markdown("---")
        st.caption("题三：热点发现 Agent v1.0")
        st.caption(f"当前步骤: {st.session_state.p3_step}/3")


# ============================================================
# 步骤 0：开始按钮
# ============================================================
def step0_start():
    """开始运行按钮"""
    if st.session_state.p3_step == 0:
        st.header("🚀 准备就绪")
        st.markdown("点击下方按钮启动热点发现工作流")

        steps_display = [
            "1️⃣ 抓取数据源 + 事件聚类（可重新搜索）",
            "2️⃣ AI 筛选/总结/可信度评估 + 人工审核（可编辑）",
            "3️⃣ 发布前确认 + 多渠道推送",
        ]
        for s in steps_display:
            st.markdown(f"  - {s}")

        if st.button("🚀 开始运行", type="primary", width="stretch"):
            st.session_state.p3_step = 1
            st.rerun()


# ============================================================
# 步骤 1：抓取数据源 + 事件聚类
# ============================================================
def step1_fetch_and_cluster():
    """抓取数据源 + 事件聚类

    【新功能】信息源不满意可点击「重新搜索」按钮重新抓取
    """
    # Step 1: 抓取数据源
    st.header("1️⃣ 抓取数据源")
    if not st.session_state.raw_items:
        with st.spinner("正在抓取 Hacker News / TechCrunch / InfoQ / GitHub ..."):
            st.session_state.raw_items = fetch_all(max_items=30)

    st.success(f"共抓取到 {len(st.session_state.raw_items)} 条候选热点")
    if st.session_state.raw_items:
        df_data = []
        for it in st.session_state.raw_items[:15]:
            df_data.append({
                "来源": it.get("source", ""),
                "标题": it.get("title", "")[:50],
            })
        st.dataframe(df_data, width="stretch", hide_index=True)

    # Step 2: 事件聚类
    st.header("2️⃣ 事件聚类（合并同一事件）")
    if not st.session_state.events and st.session_state.raw_items:
        with st.spinner("正在按关键词相似度聚类..."):
            st.session_state.events = merge_events(
                st.session_state.raw_items, threshold=0.18
            )

    st.success(f"聚类后得到 {len(st.session_state.events)} 个独立事件")
    if st.session_state.events:
        df_data = []
        for ev in st.session_state.events[:15]:
            cred = ev.get("credibility", {})
            df_data.append({
                "标题": ev.get("title", "")[:40],
                "来源": ev.get("source", ""),
                "合并数": ev.get("sources_count", 1),
                "可信度": f"{cred.get('score', 0)}/10",
            })
        st.dataframe(df_data, width="stretch", hide_index=True)

    # 【新功能】重新搜索按钮
    st.markdown("---")
    st.markdown("##### 💡 对数据不满意？可重新搜索")
    col_re, col_next = st.columns([1, 2])
    with col_re:
        if st.button("🔄 重新搜索", help="清空当前结果，重新抓取和聚类"):
            st.session_state.raw_items = []
            st.session_state.events = []
            st.rerun()
    with col_next:
        if st.session_state.p3_step == 1:
            if st.button("➡️ AI 筛选与审核", type="primary", width="stretch"):
                st.session_state.p3_step = 2
                st.rerun()


# ============================================================
# 步骤 2：AI 筛选 + 人工审核（可编辑）
# ============================================================
def step2_ai_filter_and_review():
    """AI 筛选/总结/可信度评估 + 人工审核（可编辑）

    【新功能】热点审核改为可编辑：
    - 标题可编辑
    - 来源可编辑
    - 摘要可编辑
    - 理由可编辑
    - 价值分可编辑
    """
    # Step 3: AI 筛选
    st.header("3️⃣ AI 筛选/总结/可信度评估")
    if not st.session_state.hotspots and st.session_state.events:
        with st.spinner("AI 正在筛选热点、总结观点与价值判断..."):
            st.session_state.hotspots = ai_filter_and_summarize(
                st.session_state.events, top_n=5
            )
    st.success(f"筛选出 {len(st.session_state.hotspots)} 条高价值热点")

    # Step 4: 人工审核（可编辑）
    st.header("4️⃣ 热点审核（可编辑）")
    st.markdown("✏️ 可直接修改热点的标题、来源、摘要、理由、价值分等")

    checked_count = 0
    for i, h in enumerate(st.session_state.hotspots):
        with st.expander(f"热点 {i+1}: {h.get('title', '')[:40]}", expanded=True):
            col1, col2 = st.columns([0.3, 4])
            with col1:
                checked = st.checkbox("保留", value=True, key=f"p3_check_{i}")
            with col2:
                if checked:
                    checked_count += 1

            # 可编辑字段
            col_a, col_b = st.columns(2)
            with col_a:
                st.text_input(
                    "标题",
                    value=h.get("title", ""),
                    key=f"p3_edit_title_{i}",
                )
                st.text_input(
                    "来源",
                    value=h.get("source", ""),
                    key=f"p3_edit_source_{i}",
                )
                st.text_input(
                    "价值分(0-10)",
                    value=str(h.get("value", "")),
                    key=f"p3_edit_value_{i}",
                )
            with col_b:
                st.text_input(
                    "摘要",
                    value=h.get("summary", ""),
                    key=f"p3_edit_summary_{i}",
                )
                st.text_area(
                    "理由",
                    value=h.get("reason", ""),
                    key=f"p3_edit_reason_{i}",
                    height=80,
                )

            # 可信度（只读展示）
            cred = h.get("credibility", {})
            if cred.get("score") is not None:
                st.info(f"📊 可信度: {cred.get('score')}/10 — {cred.get('explain', '')}")

            # 不同观点（只读展示）
            if h.get("viewpoints"):
                st.markdown("**不同观点:**")
                for vp in h["viewpoints"]:
                    st.markdown(f"  - ({vp.get('source', '')}) {vp.get('view', '')}")

            # 合并报道
            if h.get("sources_count", 1) > 1:
                st.caption(f"🔀 合并 {h.get('sources_count')} 家来源: {', '.join(h.get('all_sources', []))}")

            if h.get("url"):
                st.caption(f"🔗 链接: {h.get('url', '')}")

    st.info(f"当前保留 {checked_count} 个热点")

    # 下一步按钮
    if checked_count > 0:
        if st.session_state.p3_step == 2:
            if st.button("➡️ 保存并生成报告", type="primary"):
                # 收集勾选的热点，并应用用户的编辑
                final = []
                for i, h in enumerate(st.session_state.hotspots):
                    if st.session_state[f"p3_check_{i}"]:
                        edited = dict(h)
                        edited["title"] = st.session_state[f"p3_edit_title_{i}"]
                        edited["source"] = st.session_state[f"p3_edit_source_{i}"]
                        edited["summary"] = st.session_state[f"p3_edit_summary_{i}"]
                        edited["reason"] = st.session_state[f"p3_edit_reason_{i}"]
                        try:
                            edited["value"] = float(st.session_state[f"p3_edit_value_{i}"])
                        except (ValueError, TypeError):
                            edited["value"] = h.get("value", 5)
                        final.append(edited)
                st.session_state.final_hotspots = final
                st.session_state.p3_step = 3
                st.rerun()
    else:
        st.warning("请至少保留一个热点")


# ============================================================
# 步骤 3：发布前确认 + 推送
# ============================================================
def step3_publish():
    """发布前确认 + 多渠道推送"""
    st.header("5️⃣ 发布前确认 & 推送")

    # 生成报告
    report = format_report(st.session_state.final_hotspots)

    # 报告可编辑
    st.markdown("✏️ 报告内容可在下方文本框中修改")
    edited_report = st.text_area(
        "报告内容（可编辑）",
        value=report,
        height=400,
        key="p3_edit_report",
        label_visibility="collapsed",
    )

    with st.expander("查看完整报告预览", expanded=False):
        st.text(edited_report)

    col1, col2 = st.columns(2)

    with col1:
        if st.button("✅ 确认发布", type="primary"):
            with st.spinner("正在推送（飞书 + QQ邮箱）..."):
                try:
                    results = push.push_all("热点发现报告", edited_report)
                    for channel, res in results.items():
                        if channel == "企业微信":
                            continue
                        status = "✅ 成功" if res.get("ok") else "❌ 失败"
                        st.write(f"**{channel}**: {status} — {res.get('detail')}")
                    st.success("推送完成！")
                    st.session_state.pushed = True
                except Exception as e:
                    st.error(f"推送失败: {e}")

            # 保存到本地文件
            try:
                os.makedirs("output", exist_ok=True)
                out_path = f"output/hotspot_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(edited_report)
                st.success(f"报告已保存: {out_path}")

                # 提供下载
                st.download_button(
                    label="📥 下载报告（TXT）",
                    data=edited_report.encode("utf-8"),
                    file_name=os.path.basename(out_path),
                    mime="text/plain",
                )
            except Exception as e:
                st.error(f"保存失败: {e}")

    with col2:
        if st.button("🔄 重新开始"):
            # 清除题三相关 session_state
            for key in ["p3_step", "raw_items", "events", "hotspots",
                        "final_hotspots", "pushed"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()


# ============================================================
# 主函数
# ============================================================
def main():
    init_page()
    init_session_state()
    show_sidebar()

    if st.session_state.p3_step == 0:
        step0_start()
    elif st.session_state.p3_step == 1:
        step1_fetch_and_cluster()
    elif st.session_state.p3_step == 2:
        step2_ai_filter_and_review()
    elif st.session_state.p3_step == 3:
        step3_publish()


if __name__ == "__main__":
    main()
