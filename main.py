import argparse

from workflow import run

# CLI 入口：解析问题并触发多智能体流程


def main() -> int:
    """解析命令行参数/交互输入，并调用工作流返回结果。"""
    parser = argparse.ArgumentParser(description="LangGraph 多智能体阿里云示例。")
    parser.add_argument("question", nargs="?", help="输入给系统的问题。")
    args = parser.parse_args()

    # 优先使用命令行参数，否则进入交互式输入
    question = args.question or input("请输入问题：").strip()
    if not question:
        raise SystemExit("必须提供问题。")

    # 执行多智能体工作流并输出最终结果
    print(run(question))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
