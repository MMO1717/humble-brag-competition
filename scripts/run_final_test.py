#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


PROJECT_DIR = Path(__file__).resolve().parents[1]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

import config
from src.llm_client import load_env
from src.pipeline import run_pipeline


def apply_final_test_config(cfg: Any) -> None:
    cfg.RUN_MODE = "test"
    cfg.INPUT_PATH = cfg.TEST_INPUT_PATH
    cfg.MAX_ITEMS = None
    cfg.RUN_DEV_EVAL = False
    cfg.EFFECTIVE_ERROR_ANALYSIS = False
    cfg.EFFECTIVE_SAVE_ERROR_MEMORY = False
    cfg.RUN_OFFICIAL_FORMAT_CHECK = True

    cfg.USE_MEMORY = True
    cfg.USE_FEWSHOT = True
    cfg.FEWSHOT_RETRIEVAL_MODE = "jaccard"
    cfg.MEMORY_ROUTER_MODE = "llm_rerank"
    cfg.USE_RESPONSE_CANDIDATE_RERANK = False
    cfg.USE_UNDERSTANDING_TEMPLATE_REPAIR = True
    cfg.UNDERSTANDING_TEMPLATE_REPAIR_FIELDS = ("desired_feedback",)
    cfg.SAVE_ERROR_MEMORY = False
    cfg.USE_GENERATED_MEMORY = False


def final_test_config_summary(cfg: Any) -> dict[str, Any]:
    return {
        "RUN_MODE": cfg.RUN_MODE,
        "INPUT_PATH": str(cfg.INPUT_PATH),
        "MAX_ITEMS": cfg.MAX_ITEMS,
        "RUN_DEV_EVAL": cfg.RUN_DEV_EVAL,
        "RUN_OFFICIAL_FORMAT_CHECK": cfg.RUN_OFFICIAL_FORMAT_CHECK,
        "EFFECTIVE_ERROR_ANALYSIS": cfg.EFFECTIVE_ERROR_ANALYSIS,
        "USE_MEMORY": cfg.USE_MEMORY,
        "USE_FEWSHOT": cfg.USE_FEWSHOT,
        "FEWSHOT_RETRIEVAL_MODE": cfg.FEWSHOT_RETRIEVAL_MODE,
        "MEMORY_ROUTER_MODE": cfg.MEMORY_ROUTER_MODE,
        "USE_RESPONSE_CANDIDATE_RERANK": cfg.USE_RESPONSE_CANDIDATE_RERANK,
        "USE_UNDERSTANDING_TEMPLATE_REPAIR": cfg.USE_UNDERSTANDING_TEMPLATE_REPAIR,
        "UNDERSTANDING_TEMPLATE_REPAIR_FIELDS": list(
            cfg.UNDERSTANDING_TEMPLATE_REPAIR_FIELDS
        ),
        "SAVE_ERROR_MEMORY": cfg.SAVE_ERROR_MEMORY,
        "USE_GENERATED_MEMORY": cfg.USE_GENERATED_MEMORY,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run final test submission generation with the recommended router config."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the effective final-test config without running the pipeline.",
    )
    args = parser.parse_args()

    apply_final_test_config(config)
    summary = final_test_config_summary(config)
    if args.dry_run:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return

    load_env(PROJECT_DIR / ".env")
    print(json.dumps({"final_test_config": summary}, ensure_ascii=False, indent=2))
    run_pipeline(config)


if __name__ == "__main__":
    main()
