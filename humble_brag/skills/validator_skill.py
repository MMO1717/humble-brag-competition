from __future__ import annotations

from typing import Any

from ..output_builder import build_output_row
from ..validators import validate_output
from .base import Skill


class ValidatorSkill(Skill):
    name = "ValidatorSkill"

    def run(self, state: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        output_row = build_output_row(state["input_row"], state)
        state["final_output"] = output_row
        try:
            validate_output(output_row, state["input_row"])
            state["is_valid"] = True
        except Exception as exc:
            state["is_valid"] = False
            state["validation_errors"].append(str(exc))
        return state
