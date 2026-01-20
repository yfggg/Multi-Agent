import os
from typing import Dict, List

REGION_ALIASES = {
    "hangzhou": "cn-hangzhou",
    "beijing": "cn-beijing",
    "shanghai": "cn-shanghai",
    "shenzhen": "cn-shenzhen",
    "hongkong": "cn-hongkong",
    "singapore": "ap-southeast-1",
    "tokyo": "ap-northeast-1",
    "杭州": "cn-hangzhou",
    "北京": "cn-beijing",
    "上海": "cn-shanghai",
    "深圳": "cn-shenzhen",
    "香港": "cn-hongkong",
    "新加坡": "ap-southeast-1",
    "东京": "ap-northeast-1",
}

HISTORY_MAX_MESSAGES = 12
EXIT_COMMANDS = {"exit", "quit", "bye", "退出", "再见", "结束"}
RESET_COMMANDS = {"reset", "restart", "重置", "重新开始", "清空"}


def resolve_region_id(question: str) -> str:
    """从问题中解析 region id，未命中返回默认地域。"""
    default_region = os.environ.get("DEFAULT_REGION_ID", "")
    lowered = question.lower()
    for alias, region_id in REGION_ALIASES.items():
        if alias in lowered:
            return region_id
    for region_id in REGION_ALIASES.values():
        if region_id in lowered:
            return region_id
    return default_region


def trim_history(history: List[Dict[str, str]], max_messages: int = HISTORY_MAX_MESSAGES) -> List[Dict[str, str]]:
    """保留最近的对话消息。"""
    if not history or max_messages <= 0:
        return []
    return history[-max_messages:]


def is_exit_command(text: str) -> bool:
    """判断是否为退出指令。"""
    return text.strip().lower() in EXIT_COMMANDS


def is_reset_command(text: str) -> bool:
    """判断是否为重置指令。"""
    return text.strip().lower() in RESET_COMMANDS
