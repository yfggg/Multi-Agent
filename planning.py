import json
from typing import List

from tools import call_llm
from helpers import needs_balance, needs_ecs

# 允许被规划器选择的 Agent 名称集合
AGENT_NAMES = {
    "ChatAssistant",
    "AliyunInfoAssistant",
    "InstanceTypeDetailAssistant",
}


def planner_agent(question: str) -> List[str]:
    """调用 LLM 生成执行计划；失败时回退到启发式策略。"""
    system_prompt = (
        "你是多智能体系统的规划器。"
        "从允许列表中选择 Agent，并且只输出 JSON。\n"
        "允许的 Agent：ChatAssistant, AliyunInfoAssistant, InstanceTypeDetailAssistant。\n"
        "输出格式：{\"agents\": [\"...\"]}，顺序即执行顺序。"
    )
    try:
        # 让 LLM 返回 JSON 计划，并从中筛选合法的 Agent
        plan_text = call_llm(system_prompt, question)
        plan_json = json.loads(plan_text)
        agents = [a for a in plan_json.get("agents", []) if a in AGENT_NAMES]
        if agents:
            return normalize_plan(agents)
    except Exception:
        # 任何解析/调用错误都走回退逻辑，避免阻断整体流程
        pass
    # 回退：用规则判断需要执行的 Agent
    return normalize_plan(heuristic_plan(question))


def heuristic_plan(question: str) -> List[str]:
    """基于关键词的启发式规划，用于 LLM 失败时兜底。"""
    agents: List[str] = []
    # 识别是否需要 ECS/余额查询
    if needs_ecs(question) or needs_balance(question):
        agents.append("AliyunInfoAssistant")
    # 识别是否需要实例规格详情
    if (
        "spec" in question.lower()
        or "cpu" in question.lower()
        or "memory" in question.lower()
        or "规格" in question
        or "内存" in question
    ):
        agents.append("InstanceTypeDetailAssistant")
    # 没有命中任何规则时，走基础对话
    if not agents:
        agents.append("ChatAssistant")
    return agents


def normalize_plan(agents: List[str]) -> List[str]:
    """去重并保证关键执行顺序：先查资源，再查规格。"""
    seen = set()
    deduped = []
    for agent in agents:
        # 按出现顺序去重
        if agent not in seen:
            deduped.append(agent)
            seen.add(agent)
    if (
        "AliyunInfoAssistant" in deduped
        and "InstanceTypeDetailAssistant" in deduped
    ):
        # 若同时包含资源查询与规格查询，则保证先资源后规格
        ordered = ["AliyunInfoAssistant"]
        for agent in deduped:
            if agent in ("AliyunInfoAssistant", "InstanceTypeDetailAssistant"):
                continue
            ordered.append(agent)
        ordered.append("InstanceTypeDetailAssistant")
        return ordered
    return deduped
