"""
题三专用：逐条人工审核模块

与 common/human_review.py（整段报告审核）不同，本模块对每条热点单独审核：
    支持 按条号编辑 / 按条号拒绝 / 通过完成 / 退出
    编辑(e)与拒绝(r)均不推送，只有最后按 p 完成审核时才整批多渠道推送。
    企业微信默认不推送（题三不发企业微信）。
"""
import sys

from common import push


def _print_item(idx, item, rejected=False):
    """打印单条热点的完整信息（含可信度与观点）"""
    status = " [已拒绝]" if rejected else ""
    cred = item.get("credibility", {})
    print(f"\n{idx}. {item.get('title', '')}{status}")
    print(f"   来源: {item.get('source', '')} | 价值: {item.get('value', '')}/10")
    if cred.get("score") is not None:
        print(f"   可信度: {cred.get('score')}/10 ({cred.get('explain', '')})")
    if item.get("sources_count", 1) > 1:
        print(f"   合并报道: {item.get('sources_count')} 家来源 "
              f"[{', '.join(item.get('all_sources', []))}]")
    if item.get("summary"):
        print(f"   摘要: {item.get('summary', '')}")
    if item.get("viewpoints"):
        print("   观点:")
        for vp in item["viewpoints"]:
            print(f"       - ({vp.get('source', '')}) {vp.get('view', '')}")
    if item.get("reason"):
        print(f"   理由: {item.get('reason', '')}")
    if item.get("url"):
        print(f"   链接: {item.get('url', '')}")


def _edit_item(item):
    """对单条热点逐字段编辑，回车保持原样，返回新 dict"""
    print("\n>>> 进入编辑（每项输入新值后回车；直接回车=保持原样）:")
    fields = ["title", "source", "value", "summary", "reason", "url"]
    labels = {
        "title": "标题",
        "source": "来源",
        "value": "价值(0-10)",
        "summary": "摘要",
        "reason": "理由",
        "url": "链接",
    }
    new_item = dict(item)
    for f in fields:
        prompt = f"    {labels[f]} [{item.get(f, '')}]: "
        val = input(prompt).strip()
        if val:
            if f == "value":
                try:
                    new_item[f] = float(val)
                except ValueError:
                    print("      价值需为数字，忽略本次修改")
            else:
                new_item[f] = val
    print(">>> 已保存对该条的编辑")
    return new_item


def _format_final(items):
    """把最终保留的条目格式化为报告文本（含可信度与观点）"""
    lines = []
    for i, it in enumerate(items, 1):
        cred = it.get("credibility", {})
        lines.append(f"{i}. {it.get('title', '')}")
        lines.append(f"   来源: {it.get('source', '')} | 价值: {it.get('value', '')}/10")
        if cred.get("score") is not None:
            lines.append(f"   可信度: {cred.get('score')}/10")
        if it.get("sources_count", 1) > 1:
            lines.append(f"   合并报道: {it.get('sources_count')} 家来源 "
                         f"[{', '.join(it.get('all_sources', []))}]")
        if it.get("summary"):
            lines.append(f"   摘要: {it.get('summary', '')}")
        if it.get("viewpoints"):
            lines.append("   观点:")
            for vp in it["viewpoints"]:
                lines.append(f"       - ({vp.get('source', '')}) {vp.get('view', '')}")
        if it.get("reason"):
            lines.append(f"   理由: {it.get('reason', '')}")
        if it.get("url"):
            lines.append(f"   链接: {it.get('url', '')}")
        lines.append("")
    return "\n".join(lines)


def review_items(items, title="热点发现报告"):
    """逐条人工审核热点列表。

    Args:
        items: [{title, url, source, summary, value, reason, credibility, viewpoints}]
        title: 推送时的报告标题

    Returns:
        最终保留的条目列表（含被编辑过的）；按 p 完成时整批多渠道推送。
        e/r 操作不推送。企业微信默认不推送。
    """
    wl = [dict(it) for it in items]          # 可修改的工作副本
    active = [True] * len(wl)                 # 是否保留

    print("\n" + "=" * 60)
    print("【人工审核】以下为候选热点，请逐条审阅")
    print("操作说明: [p]完成并推送  [e]输入条号编辑  [r]输入条号拒绝  [q]退出")
    print("提示: 编辑(e)与拒绝(r)均不推送，仅按 p 完成时统一多渠道推送")
    print("=" * 60)

    # 先完整展示每条新闻的内容（含评分、可信度、观点、理由、链接）
    print("\n" + "#" * 60)
    print("📋 当日候选详情（按顺序展示每条完整内容）")
    print("#" * 60)
    for i, it in enumerate(wl, 1):
        _print_item(i, it)
        print()

    # 再按顺序标号输出当日候选清单
    print("\n" + "-" * 60)
    print("📌 当日候选清单（共 %d 条）" % len(wl))
    print("-" * 60)
    for i, it in enumerate(wl, 1):
        print(f"  {i}. {it.get('title', '')[:45]} | 价值: {it.get('value', '')}/10"
              + (" [已拒绝]" if not active[i - 1] else ""))
    print("-" * 60)

    while True:
        # 每次循环都重新展示当前全部状态，并给出操作按钮
        print("\n" + "-" * 60)
        print("当前候选清单：")
        for i, it in enumerate(wl, 1):
            print(f"  {i}. {it.get('title', '')[:45]} | 价值: {it.get('value', '')}/10"
                  + (" [已拒绝]" if not active[i - 1] else ""))
        print("-" * 60)

        choice = input("操作 [p]完成并推送  [e]编辑  [r]拒绝  [q]退出: ").strip().lower()

        if choice == "p":
            # 完成审核：输出所有保留的条目，并整批多渠道推送
            final = [wl[i] for i in range(len(wl)) if active[i]]
            print("\n>>> 审核完成，输出保留的全部热点（含编辑过的）")
            print("=" * 60)
            print(f"📌 最终热点清单（共 {len(final)} 条）")
            print("=" * 60)
            for i, it in enumerate(final, 1):
                _print_item(i, it)
                print()

            # 仅在此处统一多渠道推送（飞书 + 邮件，企业微信默认不发）
            if final:
                print(">>> 正在多渠道推送（飞书 + 邮件）...")
                report = f"📌 {title}\n\n" + _format_final(final)
                results = push.push_all(title, report)
                for channel, res in results.items():
                    # 题三不显示企业微信（即使 push_all 返回了也跳过）
                    if channel == "企业微信":
                        continue
                    status = "✅ 成功" if res.get("ok") else "❌ 失败/跳过"
                    print(f"      [{channel}] {status}  {res.get('detail')}")
            return final

        elif choice == "e":
            num = input(">>> 输入要编辑的条号: ").strip()
            if not num.isdigit() or not (1 <= int(num) <= len(wl)):
                print("      无效条号，请重新操作")
                continue
            idx = int(num) - 1
            _print_item(idx + 1, wl[idx])
            wl[idx] = _edit_item(wl[idx])
            active[idx] = True      # 编辑后视为保留
            # 编辑后回到操作按钮，不推送，让用户继续操作

        elif choice == "r":
            num = input(">>> 输入要拒绝的条号: ").strip()
            if not num.isdigit() or not (1 <= int(num) <= len(wl)):
                print("      无效条号，请重新操作")
                continue
            idx = int(num) - 1
            active[idx] = False
            print(f">>> 已拒绝第 {int(num)} 条")
            # 拒绝后回到操作按钮，不推送，让用户继续操作

        elif choice == "q":
            print(">>> 已退出")
            sys.exit(0)

        else:
            print("无效输入，请重新选择")
