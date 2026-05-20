from __future__ import annotations

from typing import Any


class Skill:
    """SkillFlow 中每一步的最小统一接口。"""

    name = "skill"

    def run(self, state: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError
