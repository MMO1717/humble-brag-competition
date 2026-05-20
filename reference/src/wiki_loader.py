from __future__ import annotations

from pathlib import Path


WIKI_FILES = {
    "label_schema": "label_schema.md",
    "bragging_mechanism_guide": "bragging_mechanism_guide.md",
    "response_strategy_guide": "response_strategy_guide.md",
    "risk_policy": "risk_policy.md",
    "platform_relationship_style": "platform_relationship_style.md",
}

ENGLISH_SECTION_TITLE = "## English Prompt Notes"


def _extract_english_prompt_notes(text: str) -> str:
    """只抽取 Wiki 中可注入英文 prompt 的段落。"""
    start = text.find(ENGLISH_SECTION_TITLE)
    if start == -1:
        return ""
    body = text[start + len(ENGLISH_SECTION_TITLE) :]
    next_heading = body.find("\n## ")
    if next_heading != -1:
        body = body[:next_heading]
    return body.strip()


def load_agent_wiki(wiki_dir: Path, enabled: bool = True) -> dict[str, str]:
    """读取 agent_wiki 文档；缺失文件返回空字符串，不中断 pipeline。"""
    wiki = {key: "" for key in WIKI_FILES}
    if not enabled:
        return wiki

    for key, filename in WIKI_FILES.items():
        path = wiki_dir / filename
        try:
            text = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            print(f"Wiki 文件不存在，跳过: {path}")
            continue
        except OSError as exc:
            print(f"Wiki 文件读取失败，跳过: {path} ({exc})")
            continue
        wiki[key] = _extract_english_prompt_notes(text)
    return wiki
