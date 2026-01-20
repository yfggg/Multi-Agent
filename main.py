import argparse

from helpers import is_exit_command
from workflow import build_app


def _print_tip() -> None:
    print("已进入客服模式，可多轮对话。输入 exit/quit/退出 结束，输入 reset 重置导购状态。")


def main() -> int:
    parser = argparse.ArgumentParser(description="多智能体客服（资源查询 + 智能导购）")
    parser.add_argument("question", nargs="?", help="输入给系统的问题")
    parser.add_argument(
        "--session-id",
        dest="session_id",
        default=None,
        help="会话 ID（用于区分不同用户的记忆）",
    )
    args = parser.parse_args()

    app = build_app()
    session_id = args.session_id or "cli"
    _print_tip()

    if args.question:
        result = app.invoke(
            {"question": args.question},
            config={"configurable": {"thread_id": session_id}},
        )
        reply = result.get("reply", "")
        if reply:
            print(reply)

    while True:
        question = input("你：").strip()
        if not question:
            continue
        if is_exit_command(question):
            print("已结束本次对话。")
            break
        result = app.invoke(
            {"question": question},
            config={"configurable": {"thread_id": session_id}},
        )
        reply = result.get("reply", "")
        if reply:
            print(reply)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
