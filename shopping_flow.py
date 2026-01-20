import json
import os
import re
from typing import Dict, List, Tuple

from helpers import resolve_region_id
from tools import call_llm, call_rag_app
from agents import general_assistant

REQUIRED_FIELDS = ["场景", "vCPU", "内存", "预算", "地域"]
OPTIONAL_FIELDS = ["架构"]
FIELD_QUESTIONS = {
    "场景": "您主要的业务场景是什么？例如 Web/数据库/AI 推理/通用计算。",
    "vCPU": "您期望的 vCPU 核数或范围是多少？例如 2-4 核。",
    "内存": "您期望的内存大小或范围是多少？例如 8-16 GB。",
    "预算": "您的预算区间是多少？例如每月 200-500 元。",
    "地域": "希望部署在哪个地域？例如 cn-hangzhou。",
}
EXTRACTION_FIELDS = REQUIRED_FIELDS + OPTIONAL_FIELDS


def _is_filled(value: object) -> bool:
    if value is None:
        return False
    text = str(value).strip()
    if not text:
        return False
    return text not in {"未知", "不确定", "不知道", "无", "n/a", "N/A"}


def _requirements_complete(requirements: Dict[str, str]) -> bool:
    return all(_is_filled(requirements.get(field)) for field in REQUIRED_FIELDS)


def _should_reuse_requirements(question: str) -> bool:
    text = (question or "").strip()
    if not text:
        return False
    lowered = text.lower()
    carry_over_hints = {
        "沿用",
        "继续",
        "基于",
        "在之前基础上",
        "在刚才基础上",
        "之前",
        "上次",
        "刚才",
        "同样",
        "不变",
        "其余不变",
        "照旧",
    }
    if any(hint in text for hint in carry_over_hints):
        return True
    modify_hints = {
        "改为",
        "改成",
        "改到",
        "调整",
        "变为",
        "换成",
        "提高",
        "降低",
        "上调",
        "下调",
        "更新",
    }
    requirement_keywords = {"场景", "业务", "用途", "预算", "内存", "vcpu", "cpu", "核", "地域", "区域"}
    if any(hint in text for hint in modify_hints) and any(key in lowered or key in text for key in requirement_keywords):
        return True
    return False


def _parse_json(text: str) -> Dict[str, str]:
    try:
        return json.loads(text)
    except Exception:
        match = re.search(r"\{.*\}", text or "", re.S)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                return {}
    return {}


def _extract_requirements(
    question: str,
    history: List[Dict[str, str]],
    requirements: Dict[str, str],
) -> Dict[str, str]:
    system_prompt = (
        "你是信息抽取器。请从用户输入中抽取导购所需信息，并输出 JSON。\n"
        f"必须包含字段：{', '.join(EXTRACTION_FIELDS)}。\n"
        "未提到的字段输出空字符串，不要编造。只输出 JSON。"
    )
    payload = {"已收集需求": requirements, "用户输入": question}
    text = call_llm(system_prompt, json.dumps(payload, ensure_ascii=False), history=history)
    data = _parse_json(text)
    result: Dict[str, str] = {}
    for key in EXTRACTION_FIELDS:
        value = data.get(key)
        if isinstance(value, (str, int, float)):
            result[key] = str(value).strip()
    return result


def _merge_requirements(requirements: Dict[str, str], extracted: Dict[str, str]) -> Dict[str, str]:
    merged = dict(requirements)
    for key, value in extracted.items():
        if _is_filled(value):
            merged[key] = value
    return merged


def guide_assistant(
    question: str,
    history: List[Dict[str, str]],
    requirements: Dict[str, str],
) -> Tuple[str, Dict[str, str], bool]:
    reuse_existing = not _requirements_complete(requirements) or _should_reuse_requirements(question)
    extraction_requirements = requirements if reuse_existing else {}
    extracted = _extract_requirements(question, history, extraction_requirements)
    base_requirements = requirements if reuse_existing else {}
    updated = _merge_requirements(base_requirements, extracted)
    if not _is_filled(updated.get("地域")):
        region_id = resolve_region_id(question)
        if region_id:
            updated["地域"] = region_id
    missing = [field for field in REQUIRED_FIELDS if not _is_filled(updated.get(field))]
    if missing:
        return FIELD_QUESTIONS[missing[0]], updated, False
    return "", updated, True


def recommend_assistant(requirements: Dict[str, str], history: List[Dict[str, str]]) -> str:
    app_id = os.environ.get("RAG_APP_ID", "")
    if not app_id:
        return "未设置 RAG_APP_ID，无法推荐实例规格。"
    requirement_text = json.dumps(requirements, ensure_ascii=False)
    prompt = (
        "你是 ECS 实例导购，请基于需求推荐合适的实例规格，并给出推荐理由。\n"
        "请从实例规格族知识库中检索信息，输出 3-5 个候选规格（不足可少于 3 个）。\n"
        f"需求：{requirement_text}"
    )
    return call_rag_app(app_id, prompt)


def _route_shopping(
    question: str,
    history: List[Dict[str, str]],
    requirements: Dict[str, str],
) -> str:
    system_prompt = (
        "你是导购路由器，需要判断用户是否进入 ECS 导购流程。\n"
        "只允许输出以下之一：ECSGuideAssistant、Other。"
    )
    payload = {"requirements": requirements, "question": question}
    try:
        text = call_llm(system_prompt, json.dumps(payload, ensure_ascii=False), history=history)
        normalized = (text or "").strip().lower()
        if "ecs" in normalized or "guide" in normalized or "导购" in normalized:
            return "ECSGuideAssistant"
        if "other" in normalized or "其他" in normalized:
            return "Other"
    except Exception:
        pass
    if any(requirements.values()):
        return "ECSGuideAssistant"
    lowered = question.lower()
    if "推荐" in question or "选型" in question or "购买" in question or "导购" in question:
        return "ECSGuideAssistant"
    if re.search(r"\becs\b", lowered):
        return "ECSGuideAssistant"
    return "Other"


def run_shopping_flow(
    question: str,
    history: List[Dict[str, str]],
    requirements: Dict[str, str],
) -> Tuple[str, Dict[str, str]]:
    route = _route_shopping(question, history, requirements)
    if route != "ECSGuideAssistant":
        return general_assistant(question, history), requirements
    reply, updated, ready = guide_assistant(question, history, requirements)
    if ready:
        reply = recommend_assistant(updated, history)
    return reply, updated
