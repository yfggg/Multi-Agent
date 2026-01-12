import os
from typing import Dict, List

# 常见地域别名映射，便于从用户问题中识别 region id
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


def resolve_region_id(question: str) -> str:
    """从问题中解析 region id；若未命中则返回默认地域。"""
    default_region = os.environ.get("DEFAULT_REGION_ID", "")
    lowered = question.lower()
    # 先匹配别名（中英文）
    for alias, region_id in REGION_ALIASES.items():
        if alias in lowered:
            return region_id
    # 再直接匹配完整 region id
    for region_id in REGION_ALIASES.values():
        if region_id in lowered:
            return region_id
    return default_region


def needs_ecs(question: str) -> bool:
    """判断问题是否涉及 ECS 实例查询。"""
    lowered = question.lower()
    return "ecs" in lowered or "instance" in lowered or "实例" in question


def needs_balance(question: str) -> bool:
    """判断问题是否涉及账号余额/账单查询。"""
    lowered = question.lower()
    return "balance" in lowered or "bill" in lowered or "余额" in question or "账单" in question


def extract_instance_types(instances: List[Dict[str, str]]) -> List[str]:
    """从 ECS 实例列表中提取去重后的规格名称。"""
    seen = set()
    results = []
    for item in instances:
        # 规格名称去重，保持首次出现的顺序
        instance_type = item.get("instance_type")
        if instance_type and instance_type not in seen:
            seen.add(instance_type)
            results.append(instance_type)
    return results
