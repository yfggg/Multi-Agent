import json
import re
from typing import Dict, List

from tools import call_llm

FLOW_NAMES = {"ShoppingFlow", "ResourceFlow", "GeneralFlow"}


def route_task(question: str, history: List[Dict[str, str]], requirements: Dict[str, str]) -> str:
    """Top-level router for shopping vs resource queries."""
    system_prompt = (
        "你是客服任务路由器。根据对话历史、已收集需求和用户输入，判断下一步流程。\n"
        "只允许输出以下之一：ShoppingFlow、ResourceFlow、GeneralFlow。\n"
        "含义：ShoppingFlow=导购/选型/需求收集；"
        "ResourceFlow=资源查询/余额/实例/规格详情；"
        "GeneralFlow=其他常规问题。"
    )
    payload = {"requirements": requirements, "question": question}
    try:
        route_text = call_llm(
            system_prompt,
            json.dumps(payload, ensure_ascii=False),
            history=history,
        )
        route = _normalize_flow(route_text)
        if route in FLOW_NAMES:
            return route
    except Exception:
        pass
    return heuristic_flow(question, requirements)


def _normalize_flow(text: str) -> str:
    lowered = (text or "").strip().lower()
    if "shopping" in lowered or "导购" in lowered or "选型" in lowered or "推荐" in lowered:
        return "ShoppingFlow"
    if "resource" in lowered or "资源" in lowered or "余额" in lowered or "实例" in lowered or "规格" in lowered:
        return "ResourceFlow"
    if "general" in lowered or "其他" in lowered or "通用" in lowered:
        return "GeneralFlow"
    return ""


def heuristic_flow(question: str, requirements: Dict[str, str]) -> str:
    lowered = question.lower()
    has_requirements = any(value for value in requirements.values())
    mentions_spec = "ecs." in lowered or "规格" in question or "参数" in question or "详情" in question
    mentions_resource = "余额" in question or "实例" in question or "账户" in question or "账单" in question
    mentions_buy = "推荐" in question or "购买" in question or "选型" in question or "导购" in question
    if mentions_resource or mentions_spec:
        return "ResourceFlow"
    if has_requirements or mentions_buy:
        return "ShoppingFlow"
    if re.search(r"\becs\b", lowered):
        return "ResourceFlow"
    return "GeneralFlow"
