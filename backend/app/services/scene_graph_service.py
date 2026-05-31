from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

import requests


PROJECT_ROOT = Path(__file__).resolve().parents[3]
ENV_PATH = PROJECT_ROOT / ".env"
TEXT_PARSER_API_URL = "https://api.deepseek.com/chat/completions"
TEXT_PARSER_MODEL = os.getenv("TEXT_PARSER_MODEL", "deepseek" + "-v4-flash")
LLM_TIMEOUT = float(os.getenv("SCENE_GRAPH_LLM_TIMEOUT", "30"))


ENTITY_RULES = [
    (("山", "峰", "岭", "峦", "岫"), "山体"),
    (("石", "岩", "崖"), "山石"),
    (("水", "江", "河", "湖", "溪", "泉", "潭", "涧"), "水体"),
    (("云", "雾", "烟", "岚", "霞"), "云雾"),
    (("树", "林", "松", "柏", "柳", "竹"), "树木"),
    (("亭", "阁", "楼", "台", "榭"), "亭台"),
    (("寺", "庙", "钟"), "寺庙"),
    (("舟", "船", "帆"), "舟楫"),
    (("桥",), "桥梁"),
    (("人", "客", "僧", "渔", "樵"), "人物"),
    (("月",), "明月"),
    (("日", "斜阳", "夕阳"), "日光"),
    (("雪",), "积雪"),
    (("雨",), "雨景"),
]

ATTRIBUTE_RULES = [
    (("月", "夜"), "清冷夜景"),
    (("雪", "寒"), "寒林雪意"),
    (("雨",), "湿润雨意"),
    (("秋", "霜"), "秋色萧疏"),
    (("春",), "春山新绿"),
    (("暮", "夕", "斜阳"), "暮色氛围"),
    (("青", "绿"), "青绿设色"),
    (("墨",), "水墨层次"),
]


def analyze_scene_graph(text: str) -> dict[str, Any]:
    if os.getenv("SCENE_GRAPH_USE_LLM", "1") != "0":
        try:
            return _analyze_scene_graph_with_llm(text)
        except Exception:
            pass
    return analyze_scene_graph_by_rules(text)


def analyze_scene_graph_by_rules(text: str) -> dict[str, Any]:
    clean_text = " ".join(text.strip().split())
    entities: list[str] = []
    extracted_terms: list[str] = []

    for keywords, entity in ENTITY_RULES:
        matched = [keyword for keyword in keywords if keyword in clean_text]
        if matched:
            _append_unique(entities, entity)
            for keyword in matched:
                _append_unique(extracted_terms, keyword)

    expanded_entities: list[str] = []
    if not _has_any(entities, ("山体", "山石")):
        _append_unique(expanded_entities, "远山")
    if "水体" not in entities:
        _append_unique(expanded_entities, "溪流")
    if "树木" not in entities:
        _append_unique(expanded_entities, "树木")
    if "云雾" not in entities:
        _append_unique(expanded_entities, "薄雾")
    if "水体" in entities and "山石" not in entities:
        _append_unique(expanded_entities, "岸边山石")
    if "明月" in entities and "树木" not in entities:
        _append_unique(expanded_entities, "松林")
    if "亭台" in entities and "树木" not in entities:
        _append_unique(expanded_entities, "亭旁树木")
    if "舟楫" in entities and "水体" not in entities:
        _append_unique(expanded_entities, "江面")

    attributes = ["远近层次", "虚实留白", "传统笔墨"]
    for keywords, attribute in ATTRIBUTE_RULES:
        if any(keyword in clean_text for keyword in keywords):
            _append_unique(attributes, attribute)

    relations = _build_relations(entities, expanded_entities)
    layout = _build_layout(entities, expanded_entities)

    return {
        "method": "规则关键词抽取 + 山水画常识补全",
        "entities": entities or ["山体", "水体", "云雾", "树木"],
        "expanded_entities": expanded_entities,
        "attributes": attributes,
        "relations": relations,
        "layout": layout,
        "extracted_terms": extracted_terms,
        "note": "当前系统演示版使用确定性规则进行轻量解析和补全，不等同于论文算法的完整训练式场景图扩充。",
    }


def scene_graph_parser_status() -> dict[str, Any]:
    return {
        "llm_enabled": os.getenv("SCENE_GRAPH_USE_LLM", "1") != "0",
        "api_key_configured": bool(_get_env("DEEPSEEK_API_KEY")),
        "fallback": "规则关键词抽取 + 山水画常识补全",
    }


def scene_graph_to_prompt(source_text: str, scene_graph: dict[str, Any]) -> str:
    entities = _join(scene_graph.get("entities", []))
    expanded = _join(scene_graph.get("expanded_entities", []))
    attributes = _join(scene_graph.get("attributes", []))
    relations = _join(scene_graph.get("relations", []))
    layout = _join(scene_graph.get("layout", []))

    parts = [source_text.rstrip("。！？.!?")]
    if entities:
        parts.append(f"显式意象包括：{entities}")
    if expanded:
        parts.append(f"隐含补全意象包括：{expanded}")
    if attributes:
        parts.append(f"画面属性：{attributes}")
    if relations:
        parts.append(f"空间关系：{relations}")
    if layout:
        parts.append(f"布局安排：{layout}")
    return "。".join(part for part in parts if part) + "。"


def _analyze_scene_graph_with_llm(text: str) -> dict[str, Any]:
    api_key = _get_env("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("缺少文本解析 API Key")

    system_prompt = """
你是中国山水画辅助创作系统中的诗词语义解析模块。请将用户输入解析为严格 JSON。
JSON 必须包含以下字段：
{
  "entities": ["显式出现或强烈指向的山水画意象"],
  "expanded_entities": ["为了完成山水画构图而补全的隐含意象"],
  "attributes": ["画面气氛、笔墨、季节、色彩、空间层次等属性"],
  "relations": ["实体之间的空间、遮挡、环绕、承托、照映等关系"],
  "layout": ["前景、中景、远景或画面左右上下的布局安排"],
  "extracted_terms": ["原文中触发解析的关键词"],
  "style_hints": ["适合图像生成的风格提示短语"]
}
要求：
1. 只输出 JSON，不要解释。
2. 字段值都必须是字符串数组。
3. expanded_entities 应体现合理补全，不能简单重复 entities。
4. 语气自然，词语适合中国山水画生成。
""".strip()
    payload = {
        "model": TEXT_PARSER_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"请解析为 json：{text}"},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.2,
        "max_tokens": 1200,
        "stream": False,
        "thinking": {"type": "disabled"},
    }
    response = requests.post(
        TEXT_PARSER_API_URL,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=payload,
        timeout=LLM_TIMEOUT,
    )
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]
    parsed = _parse_json_content(content)
    normalized = _normalize_llm_scene_graph(parsed, text)
    normalized["method"] = "大语言模型解析 + 山水画常识补全"
    normalized["note"] = "系统使用文本语义解析服务生成结构化场景图；服务不可用时自动回退到规则解析。"
    return normalized


def _normalize_llm_scene_graph(data: dict[str, Any], source_text: str) -> dict[str, Any]:
    base = analyze_scene_graph_by_rules(source_text)
    return {
        "entities": _list_or_default(data.get("entities"), base["entities"]),
        "expanded_entities": _list_or_default(data.get("expanded_entities"), base["expanded_entities"]),
        "attributes": _list_or_default(data.get("attributes"), base["attributes"]),
        "relations": _list_or_default(data.get("relations"), base["relations"]),
        "layout": _list_or_default(data.get("layout"), base["layout"]),
        "extracted_terms": _list_or_default(data.get("extracted_terms"), base["extracted_terms"]),
        "style_hints": _list_or_default(data.get("style_hints"), []),
    }


def _parse_json_content(content: str) -> dict[str, Any]:
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", content, flags=re.S)
        if not match:
            raise
        return json.loads(match.group(0))


def _list_or_default(value: Any, default: list[str]) -> list[str]:
    items = _stringify_list(value)
    return items if items else list(default)


def _stringify_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _get_env(name: str) -> str:
    value = os.getenv(name)
    if value:
        return value
    if not ENV_PATH.exists():
        return ""
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, raw_value = stripped.split("=", 1)
        if key.strip() == name:
            return raw_value.strip().strip('"').strip("'")
    return ""


def _build_relations(entities: list[str], expanded_entities: list[str]) -> list[str]:
    all_entities = set(entities) | set(expanded_entities)
    relations: list[str] = []

    if ("云雾" in all_entities or "薄雾" in all_entities) and ("山体" in all_entities or "远山" in all_entities):
        _append_unique(relations, "云雾环绕远山")
    if "水体" in all_entities and ("山石" in all_entities or "岸边山石" in all_entities):
        _append_unique(relations, "水体沿山石流动")
    if "明月" in all_entities and ("树木" in all_entities or "松林" in all_entities):
        _append_unique(relations, "明月照映松林")
    if "亭台" in all_entities and ("树木" in all_entities or "亭旁树木" in all_entities):
        _append_unique(relations, "亭台掩映于树木")
    if "舟楫" in all_entities and ("水体" in all_entities or "江面" in all_entities):
        _append_unique(relations, "舟楫位于水面")
    if "桥梁" in all_entities and "水体" in all_entities:
        _append_unique(relations, "桥梁横跨水体")

    if not relations:
        relations.append("前景、中景与远景形成递进层次")
    return relations


def _build_layout(entities: list[str], expanded_entities: list[str]) -> list[str]:
    all_entities = set(entities) | set(expanded_entities)
    layout: list[str] = []
    _append_unique(layout, "远景布置远山与云雾")
    if "水体" in all_entities or "溪流" in all_entities or "江面" in all_entities:
        _append_unique(layout, "中景组织水面或溪流")
    if "亭台" in all_entities or "桥梁" in all_entities or "舟楫" in all_entities or "人物" in all_entities:
        _append_unique(layout, "前景放置建筑、舟楫或人物作为视觉锚点")
    else:
        _append_unique(layout, "前景以树木和山石形成遮挡")
    return layout


def _append_unique(items: list[str], item: str) -> None:
    if item and item not in items:
        items.append(item)


def _has_any(items: list[str], candidates: tuple[str, ...]) -> bool:
    return any(candidate in items for candidate in candidates)


def _join(items: Any) -> str:
    if not isinstance(items, list):
        return ""
    return "、".join(str(item) for item in items if item)
