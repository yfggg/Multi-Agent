import os
from typing import Dict, List, Tuple

from helpers import extract_instance_types, needs_balance, needs_ecs, resolve_region_id
from tools import Billing, ECS, call_llm, call_rag_app


def chat_assistant(question: str) -> str:
    """基础对话 Agent：直接用大模型回答问题。"""
    system_prompt = (
        "你是 ChatAssistant，请简洁清晰地回答问题。"
        "如果问题涉及阿里云资源且缺少地域信息，请主动询问 region id。"
    )
    return call_llm(system_prompt, question)


def aliyun_info_assistant(question: str) -> Tuple[str, List[str]]:
    """资源查询 Agent：按需查询 ECS 实例与账号余额。"""
    parts: List[str] = []
    instance_types: List[str] = []
    region_id = resolve_region_id(question)
    # 按问题判断是否需要查询 ECS
    if needs_ecs(question):
        if not region_id:
            # 缺少地域信息时提示用户补充
            parts.append(
                "需要查询 ECS，但未识别到地域。"
                "请提供如 cn-hangzhou 的 region id，或设置 DEFAULT_REGION_ID。"
            )
        else:
            try:
                instances = ECS.query_instances(region_id)
                if not instances:
                    parts.append(f"{region_id} 未找到 ECS 实例。")
                else:
                    # 提取实例规格，供后续规格详情查询使用
                    instance_types = extract_instance_types(instances)
                    lines = [
                        "ECS 实例：",
                        *[
                            f"- {item['instance_id']} | {item['instance_type']} | {item['status']} | {item['zone_id']}"
                            for item in instances
                        ],
                    ]
                    parts.append("\n".join(lines))
            except Exception as exc:
                parts.append(f"ECS 查询失败：{exc}")
    # 按问题判断是否需要查询余额
    if needs_balance(question):
        try:
            balance = Billing.get_balance()
            parts.append(
                "账户余额：\n"
                f"- 可用余额(available_amount)：{balance.get('available_amount')}\n"
                f"- 币种(currency)：{balance.get('currency')}\n"
                f"- 信用额度(credit_amount)：{balance.get('credit_amount')}\n"
                f"- 网商授信(mybank_credit_amount)：{balance.get('mybank_credit_amount')}\n"
                f"- 可用现金(available_cash_amount)：{balance.get('available_cash_amount')}"
            )
        except Exception as exc:
            parts.append(f"余额查询失败：{exc}")
    # 没有命中任何查询类型时给出兜底提示
    if not parts:
        parts.append("未识别到阿里云资源查询请求。")
    return "\n\n".join(parts), instance_types


def instance_type_detail_assistant(question: str, instance_types: List[str]) -> str:
    """规格详情 Agent：调用 RAG 应用查询实例规格详情。"""
    app_id = os.environ.get("RAG_APP_ID", "")
    if not app_id:
        return "未设置 RAG_APP_ID，无法查询实例规格详情。"
    prompt = question
    if instance_types:
        # 将已识别的规格列表拼入 prompt，提升命中率
        prompt_lines = [
            f"用户问题：{question}",
            "实例规格列表：",
            *[f"- {item}" for item in instance_types],
        ]
        prompt = "\n".join(prompt_lines)
    try:
        return call_rag_app(app_id, prompt)
    except Exception as exc:
        return f"RAG 查询失败：{exc}"


def summary_assistant(question: str, outputs: Dict[str, str]) -> str:
    """汇总 Agent：把多个 Agent 输出合并成最终答案。"""
    system_prompt = (
        "你是 SummaryAssistant，请将各 Agent 的输出合并成最终答案。"
        "如果输出中显示参数缺失，请明确向用户询问。"
    )
    agent_text = "\n\n".join([f"{name} 输出：\n{content}" for name, content in outputs.items()])
    user_prompt = f"用户问题：\n{question}\n\nAgent 输出：\n{agent_text}"
    return call_llm(system_prompt, user_prompt)
