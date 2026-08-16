"""人工审核模块 - 在发布/推送前加入人工确认节点（风险控制硬要求）"""
import sys


def review_report(title: str, content: str, source: str = "") -> str:
    return human_review(title, content, source)


def human_review(title: str, content: str, source: str = "") -> str:
    print("\n" + "=" * 60)
    print("【人工审核】请确认以下内容是否允许推送/发布")
    print("=" * 60)
    if source:
        print(f"信息来源: {source}")
    print(f"标题: {title}")
    print("-" * 60)
    print(content)
    print("-" * 60)
    while True:
        choice = input("操作 [p]通过  [e]编辑  [r]拒绝  [q]退出: ").strip().lower()
        if choice == "p":
            print(">>> 已通过审核，准备推送\n")
            return content
        elif choice == "e":
            print(">>> 请输入修改后的完整内容（输入 END 单独一行结束）：")
            lines = []
            while True:
                line = input()
                if line.strip() == "END":
                    break
                lines.append(line)
            print(">>> 已保存编辑后的内容，准备推送\n")
            return "\n".join(lines)
        elif choice == "r":
            print(">>> 已拒绝推送\n")
            return ""
        elif choice == "q":
            print(">>> 已退出")
            sys.exit(0)
        else:
            print("无效输入，请重新选择")
