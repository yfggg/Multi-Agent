from typing import Dict, List, TypedDict

from langgraph.graph import END, StateGraph

from agents import (
    aliyun_info_assistant,
    chat_assistant,
    instance_type_detail_assistant,
    summary_assistant,
)
from planning import planner_agent


class AgentState(TypedDict):
    """多智能体执行过程中在图里流转的状态数据。"""

    question: str
    plan: List[str]
    step_index: int
    outputs: Dict[str, str]
    instance_types: List[str]
    final: str


def build_graph():
    """构建 LangGraph 状态图：规划 -> 执行 -> 汇总。"""
    graph = StateGraph(AgentState)

    def planner_node(state: AgentState) -> Dict[str, object]:
        # 规划阶段：生成计划并初始化执行状态
        return {
            "plan": planner_agent(state["question"]),
            "step_index": 0,
            "outputs": {},
            "instance_types": [],
        }

    def execute_node(state: AgentState) -> Dict[str, object]:
        # 执行阶段：按计划逐个调用 Agent
        plan = state.get("plan", [])
        index = state.get("step_index", 0)
        if index >= len(plan):
            return {}
        agent = plan[index]
        instance_types = state.get("instance_types", [])
        # 分发到具体 Agent
        if agent == "ChatAssistant":
            result = chat_assistant(state["question"])
        elif agent == "AliyunInfoAssistant":
            result, instance_types = aliyun_info_assistant(state["question"])
        elif agent == "InstanceTypeDetailAssistant":
            result = instance_type_detail_assistant(state["question"], instance_types)
        else:
            result = f"未知 Agent：{agent}"
        # 记录每个 Agent 的输出，推进执行索引
        outputs = dict(state.get("outputs", {}))
        outputs[agent] = result
        updates: Dict[str, object] = {"outputs": outputs, "step_index": index + 1}
        if agent == "AliyunInfoAssistant":
            updates["instance_types"] = instance_types
        return updates

    def should_continue(state: AgentState) -> str:
        # 决定是继续执行还是进入汇总
        if state.get("step_index", 0) < len(state.get("plan", [])):
            return "continue"
        return "summarize"

    def summarize_node(state: AgentState) -> Dict[str, object]:
        # 汇总阶段：把多个 Agent 的结果整合成最终答案
        final = summary_assistant(state["question"], state.get("outputs", {}))
        return {"final": final}

    # 定义图节点
    graph.add_node("planner", planner_node)
    graph.add_node("execute", execute_node)
    graph.add_node("summarize", summarize_node)

    # 定义执行流程与分支
    graph.set_entry_point("planner")
    graph.add_edge("planner", "execute")
    graph.add_conditional_edges(
        "execute",
        should_continue,
        {"continue": "execute", "summarize": "summarize"},
    )
    graph.add_edge("summarize", END)
    return graph.compile()


def run(question: str) -> str:
    """对外统一入口：执行图并返回最终答案。"""
    graph = build_graph()
    result = graph.invoke({"question": question})
    return result.get("final", "")
