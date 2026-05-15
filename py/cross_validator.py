"""
cross_validator.py
交叉验证模块：比对三个模型的判断结果，处理一致性/不一致情况
"""

import json
import re
from typing import Dict, List, Tuple, Optional, Any


# ========================
# 结果解析
# ========================
def parse_json_result(raw_text: str) -> Optional[Dict]:
    """从模型返回的原始文本中提取 JSON"""
    if not raw_text or raw_text.startswith("[调用错误]"):
        return None

    # 尝试直接解析
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        pass

    # 尝试在文本中找 JSON 块
    patterns = [
        r'\{[^{}]*?"是否属于商机"[^\}]*\}',
        r'```json\s*(\{.*?\})\s*```',
        r'\{.*\}',
    ]
    for pattern in patterns:
        matches = re.findall(pattern, raw_text, re.DOTALL)
        for match in matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue
    return None


def extract_field(result: Optional[Dict], field: str) -> str:
    """安全提取 JSON 字段"""
    if result is None:
        return ""
    return str(result.get(field, "") or "").strip()


# ========================
# 一致性判断
# ========================
def check_consistency(results: Dict[str, str]) -> Tuple[bool, Dict[str, Any]]:
    """
    检查三个模型结果的一致性

    返回:
        (is_consistent, detail_dict)
        detail_dict 包含：
            - is_consistent: bool
            - agree_count: int  (一致的数量，3或0)
            - disagree_count: int
            - core_field: str    # 核心判断字段
            - majority_value: str  # 多数值
            - details: {
                "是否属于商机": {model: value},
                "推荐跟进": {model: value},
                "跟进优先级": {model: value},
                "置信度": {model: value},
              }
    """
    # 先全部解析
    parsed = {}
    raw_values = {}

    for model_name, raw_text in results.items():
        parsed[model_name] = parse_json_result(raw_text)
        raw_values[model_name] = raw_text

    # 核心字段
    core_fields = ["是否属于商机", "推荐跟进", "跟进优先级", "置信度"]
    field_values = {f: {} for f in core_fields}

    for model_name, p in parsed.items():
        for field in core_fields:
            field_values[field][model_name] = extract_field(p, field)

    # 判断一致性：只看"是否属于商机"这一核心字段
    core_field = "是否属于商机"
    core_values = field_values[core_field]

    # 统计各值的数量
    value_counts = {}
    for v in core_values.values():
        if v:  # 排除空值
            value_counts[v] = value_counts.get(v, 0) + 1

    # 判断是否一致（3个模型同值 或 2:1 或 1:2:0的情况）
    unique_values = [v for v in core_values.values() if v]

    # 多数值
    majority_value = ""
    if value_counts:
        majority_value = max(value_counts, key=value_counts.get)

    # 一致性判定：所有非空值相同（用 set 去重后长度为1）
    is_consistent = len(set(unique_values)) == 1

    # 统计
    agree_count = value_counts.get(majority_value, 0) if majority_value else 0

    detail = {
        "is_consistent": is_consistent,
        "agree_count": agree_count,
        "disagree_count": 3 - agree_count,
        "core_field": core_field,
        "majority_value": majority_value,
        "value_counts": value_counts,
        "details": field_values,
        "parsed_results": {k: v for k, v in parsed.items() if v is not None},
        "raw_results": raw_values,
    }

    return is_consistent, detail


# ========================
# 不一致处理策略
# ========================
def resolve_disagreement(detail: Dict[str, Any]) -> Dict[str, Any]:
    """
    处理不一致情况，返回处理结果和建议

    策略优先级：
    1. 若2:1，以多数结果为准，在置信度上降级
    2. 若三方各执一词（三值不同），进入人工复核池
    3. 若有模型解析失败（空值），降级为两方比较
    """
    value_counts = detail["value_counts"]
    agree_count = detail["agree_count"]
    disagree_count = detail["disagree_count"]
    majority_value = detail["majority_value"]

    result = {
        "resolved_value": majority_value,
        "strategy": "",
        "confidence_adjustment": "不调整",
        "need_manual_review": False,
        "message": "",
    }

    if agree_count == 3:
        result["strategy"] = "三方一致，直接采用"
        result["message"] = f"三个模型判断一致，均为「{majority_value}」"

    elif agree_count == 2:
        result["strategy"] = "2:1 多数胜出，置信度降级"
        result["confidence_adjustment"] = "降一级（高→中，中→低）"
        result["message"] = (
            f"两方判断为「{majority_value}」，一方持不同意见，"
            f"采用多数结果，置信度降一级"
        )

    elif agree_count == 1 and len(value_counts) == 3:
        # 三方各执一词
        result["strategy"] = "三方意见分歧，进入人工复核池"
        result["need_manual_review"] = True
        result["message"] = (
            f"三个模型判断各不相同（{value_counts}），"
            f"无法自动裁决，进入人工复核"
        )

    else:
        # 2:1 但其中一方为空 或 1:1:1 但有重复
        non_empty = {k: v for k, v in value_counts.items() if k}
        if len(non_empty) == 2:
            result["strategy"] = "2:1 多数胜出，置信度降级"
            result["confidence_adjustment"] = "降一级"
            result["message"] = f"两方判断为「{majority_value}」，采用多数结果，置信度降一级"
        else:
            result["strategy"] = "难以裁决，进入人工复核池"
            result["need_manual_review"] = True
            result["message"] = "模型结果存在歧义，进入人工复核"

    return result


# ========================
# 汇总报告
# ========================
def generate_cross_validation_report(
    title: str,
    model_results: Dict[str, str],
    consistency_detail: Dict[str, Any],
    resolution: Dict[str, Any]
) -> str:
    """生成交叉验证报告"""
    lines = []
    lines.append("\n" + "=" * 80)
    lines.append("【交叉验证报告】")
    lines.append("=" * 80)
    lines.append(f"标题：{title[:60]}{'...' if len(title) > 60 else ''}")

    # 一、一致性检查
    lines.append("\n■ 一致性检查")
    fields = consistency_detail["details"]
    lines.append(f"  核心字段「是否属于商机」：")
    for model, val in fields["是否属于商机"].items():
        status = "[OK]" if val == consistency_detail["majority_value"] else "[X]"
        lines.append(f"    {status} {model}: {val or '(解析失败)'}")

    lines.append(f"  多数值：「{consistency_detail['majority_value']}」")
    lines.append(f"  一致性：{'是' if consistency_detail['is_consistent'] else '否'}")
    lines.append(f"  一致数量：{consistency_detail['agree_count']}/3")

    # 二、不一致处理
    lines.append("\n■ 不一致处理")
    lines.append(f"  采用策略：{resolution['strategy']}")
    lines.append(f"  处理结果：{resolution['resolved_value']}")
    if resolution['confidence_adjustment'] != "不调整":
        lines.append(f"  置信度调整：{resolution['confidence_adjustment']}")

    # 三、各模型详细结果
    lines.append("\n■ 各模型判断详情")
    for model, raw in model_results.items():
        parsed = consistency_detail["parsed_results"].get(model)
        lines.append(f"\n  [{model}]")
        if parsed:
            lines.append(f"    是否属于商机：{parsed.get('是否属于商机', '')}")
            lines.append(f"    推荐跟进：{parsed.get('推荐跟进', '')}")
            lines.append(f"    跟进优先级：{parsed.get('跟进优先级', '')}")
            lines.append(f"    置信度：{parsed.get('置信度', '')}")
            keywords = parsed.get("关键词", [])
            if isinstance(keywords, list):
                lines.append(f"    关键词：{', '.join(keywords[:3])}")
        else:
            lines.append(f"    [解析失败]")

    # 四、最终建议
    lines.append("\n■ 最终建议")
    if resolution["need_manual_review"]:
        lines.append("  [WARNING] 进入人工复核池")
    lines.append(f"  {resolution['message']}")

    lines.append("\n" + "-" * 80)
    return "\n".join(lines)


# ========================
# 主验证流程
# ========================
def cross_validate(title: str, model_results: Dict[str, str]) -> Dict[str, Any]:
    """
    交叉验证主流程

    参数:
        title: 项目标题
        model_results: {model_name: raw_result_text}

    返回:
        {
            "is_consistent": bool,
            "final_judgment": str,          # 最终判断
            "confidence": str,              # 最终置信度
            "need_manual_review": bool,
            "consistency_detail": {...},
            "resolution": {...},
            "report": str                   # 文本报告
        }
    """
    # 1. 检查一致性
    is_consistent, consistency_detail = check_consistency(model_results)

    # 2. 处理不一致
    resolution = resolve_disagreement(consistency_detail)

    # 3. 构建最终结果
    # 确定最终置信度
    parsed = list(consistency_detail["parsed_results"].values())
    if parsed:
        # 取解析成功的模型中最高的置信度
        conf_values = [p.get("置信度", "") for p in parsed if p.get("置信度")]
        if "高" in conf_values and resolution["confidence_adjustment"] == "降一级":
            final_confidence = "中"
        elif "中" in conf_values and resolution["confidence_adjustment"] == "降一级":
            final_confidence = "低"
        elif resolution["need_manual_review"]:
            final_confidence = "低"
        else:
            # 三方一致，直接用
            conf_raw = parsed[0].get("置信度", "中") if parsed else "中"
            final_confidence = conf_raw
    else:
        final_confidence = "低"

    # 4. 合并关键词（去重，保留所有模型的关键词）
    all_keywords = set()
    for p in parsed:
        kw = p.get("关键词", [])
        if isinstance(kw, list):
            all_keywords.update(kw[:3])  # 每个模型最多取3个
    merged_keywords = list(all_keywords)[:5]

    # 5. 生成报告
    report = generate_cross_validation_report(
        title, model_results, consistency_detail, resolution
    )

    result = {
        "is_consistent": is_consistent,
        "final_judgment": resolution["resolved_value"] or "不确定",
        "final_recommendation": "",  # 后续可根据final_judgment确定
        "final_confidence": final_confidence,
        "need_manual_review": resolution["need_manual_review"],
        "merged_keywords": merged_keywords,
        "consistency_detail": consistency_detail,
        "resolution": resolution,
        "report": report,
    }

    # 推荐跟进由final_judgment决定
    if result["final_judgment"] == "是":
        result["final_recommendation"] = "建议跟进"
    elif result["final_judgment"] == "否":
        result["final_recommendation"] = "不建议跟进"
    else:
        result["final_recommendation"] = "可观察"

    return result


# ========================
# 辅助：打印报告
# ========================
def print_report(result: Dict[str, Any]):
    """打印交叉验证报告"""
    print(result["report"])


if __name__ == "__main__":
    # 测试用例
    test_results = {
        "claude-sonnet-4-6": json.dumps({
            "是否属于商机": "是",
            "推荐跟进": "建议跟进",
            "跟进优先级": "高",
            "置信度": "高",
            "关键词": ["信息化项目审计", "第三方审计", "结算审计"],
        }),
        "gpt-4o": json.dumps({
            "是否属于商机": "是",
            "推荐跟进": "建议跟进",
            "跟进优先级": "高",
            "置信度": "高",
            "关键词": ["信息化审计", "第三方服务", "审计服务"],
        }),
        "gemini-2.0-flash": json.dumps({
            "是否属于商机": "是",
            "推荐跟进": "可观察",
            "跟进优先级": "中",
            "置信度": "中",
            "关键词": ["信息系统审计", "第三方独立审计"],
        }),
    }

    print("测试：三方结果对比")
    result = cross_validate("测试项目：信息化项目第三方审计服务采购公告", test_results)
    print_report(result)

    print("\n\n测试2：三方不一致")
    test_results2 = {
        "claude-sonnet-4-6": json.dumps({
            "是否属于商机": "是",
            "推荐跟进": "建议跟进",
            "跟进优先级": "高",
            "置信度": "高",
            "关键词": ["信息化项目审计"],
        }),
        "gpt-4o": json.dumps({
            "是否属于商机": "否",
            "推荐跟进": "不建议跟进",
            "跟进优先级": "低",
            "置信度": "高",
            "关键词": ["软件开发"],
        }),
        "gemini-2.0-flash": json.dumps({
            "是否属于商机": "不确定",
            "推荐跟进": "可观察",
            "跟进优先级": "低",
            "置信度": "低",
            "关键词": ["数据安全审计"],
        }),
    }
    result2 = cross_validate("测试项目2：系统建设与审计打包", test_results2)
    print_report(result2)