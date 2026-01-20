from typing import Dict, List, Tuple, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from agents import general_assistant
from helpers import is_reset_command, trim_history
from planning import route_task
from resource_flow import run_resource_flow
from shopping_flow import run_shopping_flow

History = List[Dict[str, str]]


class ConversationState(TypedDict, total=False):
    question: str
    history: History
    requirements: Dict[str, str]
    reply: str


def run_turn(
    question: str,
    history: History,
    requirements: Dict[str, str],
) -> Tuple[str, History, Dict[str, str]]:
    if is_reset_command(question):
        return "已重置导购状态，请重新描述您的需求。", [], {}
    history_for_model = trim_history(history)
    route = route_task(question, history_for_model, requirements)
    if route == "ShoppingFlow":
        reply, requirements = run_shopping_flow(question, history_for_model, requirements)
    elif route == "ResourceFlow":
        reply = run_resource_flow(question, history_for_model)
    else:
        reply = general_assistant(question, history_for_model)
    new_history = list(history)
    new_history.append({"role": "user", "content": question})
    new_history.append({"role": "assistant", "content": reply})
    new_history = trim_history(new_history, max_messages=20)
    return reply, new_history, requirements


def _run_turn_node(state: ConversationState) -> ConversationState:
    question = state.get("question", "")
    history = state.get("history", [])
    requirements = state.get("requirements", {})
    reply, new_history, new_requirements = run_turn(question, history, requirements)
    return {
        "question": question,
        "history": new_history,
        "requirements": new_requirements,
        "reply": reply,
    }


def build_app():
    graph = StateGraph(ConversationState)
    graph.add_node("turn", _run_turn_node)
    graph.set_entry_point("turn")
    graph.add_edge("turn", END)
    return graph.compile(checkpointer=MemorySaver())
