import json
import re
from typing import Dict, List

from helpers import resolve_region_id
from tools import Billing, ECS, call_llm
from agents import general_assistant, spec_assistant

RESOURCE_AGENT_NAMES = [
    "AliyunInfoAssistant",
    "InstanceTypeDetailAssistant",
    "ChatAssistant",
]


def _format_balance(data: Dict[str, str]) -> str:
    return (
        "余额信息：\n"
        f"- 可用金额：{data.get('available_amount')}\n"
        f"- 可用现金：{data.get('available_cash_amount')}\n"
        f"- 授信额度：{data.get('credit_amount')}\n"
        f"- 网商贷额度：{data.get('mybank_credit_amount')}\n"
        f"- 币种：{data.get('currency')}"
    )


def _format_instances(instances: List[Dict[str, str]]) -> str:
    if not instances:
        return "未查询到 ECS 实例。"
    lines = ["ECS 实例列表（最多 10 条）："]
    for item in instances:
        lines.append(
            f"- {item.get('instance_id')} | {item.get('instance_type')} | "
            f"{item.get('status')} | {item.get('zone_id')}"
        )
    return "\n".join(lines)


def resource_assistant(question: str) -> str:
    lowered = question.lower()
    wants_balance = "余额" in question or "账户" in question or "账单" in question
    wants_instances = "实例" in question or "ecs" in lowered
    if not wants_balance and not wants_instances:
        return "未识别到资源查询意图，请说明是查询余额还是 ECS 实例。"
    replies: List[str] = []
    try:
        if wants_balance:
            replies.append(_format_balance(Billing.get_balance()))
        if wants_instances:
            region_id = resolve_region_id(question)
            if not region_id:
                return "请提供地域（例如 cn-hangzhou），或设置 DEFAULT_REGION_ID。"
            replies.append(_format_instances(ECS.query_instances(region_id)))
    except RuntimeError as exc:
        return f"{exc}\n如需查询账号/实例信息，请配置 ALIBABA_CLOUD_ACCESS_KEY_ID/SECRET。"
    return "\n\n".join(replies)


def _parse_agent_list(text: str) -> List[str]:
    if not text:
        return []
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return [str(item) for item in data]
    except Exception:
        pass
    match = re.search(r"\[.*?\]", text, re.S)
    if match:
        try:
            data = json.loads(match.group(0))
            if isinstance(data, list):
                return [str(item) for item in data]
        except Exception:
            pass
    ordered: List[str] = []
    for name in RESOURCE_AGENT_NAMES:
        if name in text:
            ordered.append(name)
    return ordered


def _heuristic_agent_order(question: str) -> List[str]:
    lowered = question.lower()
    wants_spec = "ecs." in lowered or "规格" in question or "参数" in question or "详情" in question
    wants_resource = "余额" in question or "实例" in question or "ecs" in lowered
    order: List[str] = []
    if wants_resource:
        order.append("AliyunInfoAssistant")
    if wants_spec:
        order.append("InstanceTypeDetailAssistant")
    if not order:
        order.append("ChatAssistant")
    return order


def plan_resource_agents(question: str, history: List[Dict[str, str]]) -> List[str]:
    system_prompt = (
        "你是资源查询的 Planner，需要决定要依次调用哪些 assistant。\n"
        "只允许输出 JSON 数组，元素必须是以下之一：\n"
        "- AliyunInfoAssistant\n"
        "- InstanceTypeDetailAssistant\n"
        "- ChatAssistant\n"
        "只输出数组本身，不要输出其他文字。"
    )
    payload = {"question": question}
    try:
        text = call_llm(system_prompt, json.dumps(payload, ensure_ascii=False), history=history)
        order = _parse_agent_list(text)
        order = [name for name in order if name in RESOURCE_AGENT_NAMES]
        return order or _heuristic_agent_order(question)
    except Exception:
        return _heuristic_agent_order(question)


def _summarize_resource_answer(
    question: str,
    agent_messages: List[Dict[str, str]],
    history: List[Dict[str, str]],
) -> str:
    system_prompt = "你是 SummaryAssistant，请基于已知信息简洁、准确地回答用户问题。"
    chunks = "\n\n".join(
        f"{item['agent']}：\n{item['response']}" for item in agent_messages
    )
    user_prompt = f"用户问题：{question}\n\n已知信息：\n{chunks}"
    return call_llm(system_prompt, user_prompt, history=history)


def run_resource_flow(question: str, history: List[Dict[str, str]]) -> str:
    order = plan_resource_agents(question, history)
    if not order:
        return general_assistant(question, history)
    current_query = question
    agent_messages: List[Dict[str, str]] = []
    for idx, agent in enumerate(order):
        if agent == "AliyunInfoAssistant":
            response = resource_assistant(current_query)
        elif agent == "InstanceTypeDetailAssistant":
            response = spec_assistant(current_query, history)
        else:
            response = general_assistant(current_query, history)
        agent_messages.append({"agent": agent, "response": response})
        if idx < len(order) - 1:
            current_query = f"你可以参考已知信息：{response}\n用户问题：{question}"
    if len(agent_messages) == 1:
        return agent_messages[0]["response"]
    return _summarize_resource_answer(question, agent_messages, history)
