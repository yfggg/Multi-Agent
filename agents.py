import os
from typing import Dict, List

from tools import call_llm, call_rag_app


def spec_assistant(question: str, history: List[Dict[str, str]]) -> str:
    """Answer instance spec questions via RAG."""
    app_id = os.environ.get("RAG_APP_ID", "")
    if not app_id:
        return "未设置 RAG_APP_ID，无法查询实例规格详情。"
    prompt = (
        "请根据实例规格族知识库回答用户关于实例规格/参数的提问。\n"
        f"用户问题：{question}"
    )
    return call_rag_app(app_id, prompt)


def general_assistant(question: str, history: List[Dict[str, str]]) -> str:
    system_prompt = "你是智能客服助手，请用简洁、礼貌的方式回答问题。"
    return call_llm(system_prompt, question, history=history)
