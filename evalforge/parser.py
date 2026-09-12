"""SKILL.md 解析。"""

from dataclasses import asdict, dataclass, field
from pathlib import Path
import re

import yaml


class SkillNotFoundError(FileNotFoundError):
    """目标目录不含 SKILL.md。"""


@dataclass
class SkillSpec:
    name: str
    description: str
    path: str
    sections: dict[str, str] = field(default_factory=dict)
    target: str = ""
    inputs: str = ""
    outputs: str = ""
    rules: str = ""
    constraints: str = ""
    prohibitions: str = ""
    examples: str = ""

    def to_dict(self):
        return asdict(self)


def _front_matter(text):
    if not text.startswith("---"):
        return {}, text
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", text, re.DOTALL)
    if not match:
        return {}, text
    return yaml.safe_load(match.group(1)) or {}, match.group(2)


def _sections(text):
    matches = list(re.finditer(r"^#{1,3}\s+(.+?)\s*$", text, re.MULTILINE))
    result = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        result[match.group(1).strip()] = text[match.end():end].strip()
    return result


def _find_section(sections, keywords):
    for title, content in sections.items():
        if any(keyword.lower() in title.lower() for keyword in keywords):
            return content
    return ""


def parse_skill(skill_path):
    """读取 Skill 目录并归纳常见说明区块。"""
    root = Path(skill_path)
    skill_file = root / "SKILL.md"
    if not skill_file.is_file():
        raise SkillNotFoundError(f"未找到 SKILL.md：{skill_file}")

    metadata, body = _front_matter(skill_file.read_text(encoding="utf-8"))
    sections = _sections(body)
    name = str(metadata.get("name") or _find_section(sections, ["evalforge"]) or root.name)
    if name == root.name:
        heading = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
        name = heading.group(1).strip() if heading else root.name
    return SkillSpec(
        name=name,
        description=str(metadata.get("description") or _find_section(sections, ["简介", "description", "目标"])),
        path=str(root),
        sections=sections,
        target=_find_section(sections, ["目标", "purpose"]),
        inputs=_find_section(sections, ["输入", "input"]),
        outputs=_find_section(sections, ["输出", "output"]),
        rules=_find_section(sections, ["规则", "rule"]),
        constraints=_find_section(sections, ["约束", "constraint"]),
        prohibitions=_find_section(sections, ["禁止", "prohibit", "不允许"]),
        examples=_find_section(sections, ["示例", "example"]),
    )
