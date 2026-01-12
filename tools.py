import os
from http import HTTPStatus
from typing import Any, Dict, List, Optional

from alibabacloud_bssopenapi20171214.client import Client as BssOpenApi20171214Client
from alibabacloud_bssopenapi20171214 import models as bss_models
from alibabacloud_ecs20140526.client import Client as Ecs20140526Client
from alibabacloud_ecs20140526 import models as ecs_models
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_util import models as util_models
from dashscope import Application, Generation


def _require_env(name: str) -> str:
    """读取必须存在的环境变量，缺失时抛错。"""
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"缺少必要的环境变量：{name}")
    return value


def call_llm(system_prompt: str, user_prompt: str, model: Optional[str] = None) -> str:
    """统一封装 DashScope 文本生成调用，并解析成字符串输出。"""
    model_name = model or os.environ.get("DASHSCOPE_MODEL", "qwen-plus")
    # 以对话消息格式调用模型
    response = Generation.call(
        model=model_name,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        result_format="message",
    )
    status_code = getattr(response, "status_code", None)
    if status_code and status_code != HTTPStatus.OK:
        raise RuntimeError(
            f"DashScope 调用失败：{getattr(response, 'code', '')} {getattr(response, 'message', '')}"
        )
    # 兼容多种返回结构，尽量提取 message.content
    output = getattr(response, "output", None)
    if isinstance(output, dict):
        choices = output.get("choices") or []
        if choices:
            message = choices[0].get("message") or {}
            content = message.get("content")
            if content:
                return content
    return str(output or response)


def call_rag_app(app_id: str, prompt: str) -> str:
    """调用 DashScope RAG 应用，并提取常见的文本字段。"""
    response = Application.call(app_id=app_id, prompt=prompt)
    output = getattr(response, "output", None)
    if isinstance(output, dict):
        for key in ("text", "answer", "result"):
            if key in output and output[key]:
                return str(output[key])
    text = getattr(output, "text", None)
    if text:
        return str(text)
    return str(output or response)


class ECS:
    """ECS 相关 OpenAPI 封装。"""

    @staticmethod
    def _client(region_id: str) -> Ecs20140526Client:
        # 使用 AK/SK 构建 ECS 客户端
        access_key_id = _require_env("ALIBABA_CLOUD_ACCESS_KEY_ID")
        access_key_secret = _require_env("ALIBABA_CLOUD_ACCESS_KEY_SECRET")
        config = open_api_models.Config(
            access_key_id=access_key_id,
            access_key_secret=access_key_secret,
            endpoint=f"ecs.{region_id}.aliyuncs.com",
        )
        return Ecs20140526Client(config)

    @staticmethod
    def query_instances(region_id: str, page_size: int = 10) -> List[Dict[str, Any]]:
        """查询指定地域的 ECS 实例信息（简化字段）。"""
        client = ECS._client(region_id)
        request = ecs_models.DescribeInstancesRequest(
            region_id=region_id,
            page_size=page_size,
        )
        # SDK 调用返回 body，需手动提取并规整字段
        response = client.describe_instances_with_options(
            request, util_models.RuntimeOptions()
        )
        instances = []
        body = getattr(response, "body", None)
        instance_list = []
        if body and getattr(body, "instances", None):
            instance_list = body.instances.instance or []
        for item in instance_list:
            instances.append(
                {
                    "instance_id": getattr(item, "instance_id", ""),
                    "instance_type": getattr(item, "instance_type", ""),
                    "status": getattr(item, "status", ""),
                    "zone_id": getattr(item, "zone_id", ""),
                    "region_id": region_id,
                }
            )
        return instances


class Billing:
    """BSS OpenAPI 相关封装，用于查询账户余额。"""

    @staticmethod
    def _client() -> BssOpenApi20171214Client:
        # 使用 AK/SK 构建 BSS 客户端
        access_key_id = _require_env("ALIBABA_CLOUD_ACCESS_KEY_ID")
        access_key_secret = _require_env("ALIBABA_CLOUD_ACCESS_KEY_SECRET")
        config = open_api_models.Config(
            access_key_id=access_key_id,
            access_key_secret=access_key_secret,
            endpoint="business.aliyuncs.com",
        )
        return BssOpenApi20171214Client(config)

    @staticmethod
    def get_balance() -> Dict[str, Any]:
        """查询账户余额并整理为字典输出。"""
        client = Billing._client()
        response = client.query_account_balance_with_options(util_models.RuntimeOptions())
        body = getattr(response, "body", None)
        data = getattr(body, "data", None) if body else None
        return {
            "available_amount": getattr(data, "available_amount", None),
            "currency": getattr(data, "currency", None),
            "credit_amount": getattr(data, "credit_amount", None),
            "mybank_credit_amount": getattr(data, "mybank_credit_amount", None),
            "available_cash_amount": getattr(data, "available_cash_amount", None),
        }
