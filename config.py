from __future__ import annotations

from pathlib import Path


# ==================== 常用配置 ====================

RUN_MODE = "dev"  # 可选值：smoke、dev、test。

USE_MEMORY = True
USE_FEWSHOT = True
FEWSHOT_RETRIEVAL_MODE = "jaccard"  # embedding / hybrid / jaccard
MEMORY_ROUTER_MODE = "llm_rerank"  # baseline / function / llm_rerank
MEMORY_LLM_ROUTER_CANDIDATE_K = 8
MEMORY_LLM_ROUTER_TOP_K = 3
MEMORY_LLM_ROUTER_MAX_CANDIDATE_CHARS = 6000
MEMORY_LLM_ROUTER_MAX_TOKENS = 128

RUN_ERROR_ANALYSIS = True
SAVE_ERROR_MEMORY = False
USE_GENERATED_MEMORY = False

# Thinking model compatibility (e.g. gemma4, qwen3).
# When True: if content is empty but reasoning is non-empty,
#   try to extract final answer from reasoning (NOT full reasoning).
# When False: empty content stays empty, triggers skill-level fallback.
THINKING_MODEL = True
ALLOW_REASONING_FALLBACK = True
# Thinking models use tokens for both reasoning and answer, so need higher limits.
THINKING_MODEL_MAX_TOKENS_MULTIPLIER = 8


# ==================== 模型参数 ====================

TEMPERATURE = 0.3
MAX_TOKENS = 256
RETRY_TIMES = 3
RETRY_SLEEP_SECONDS = 5.0
RUN_LLM_HEALTH_CHECK = False

# 本地限速用于调用远程API时
ENABLE_API_RATE_LIMIT = True
API_REQUESTS_PER_MINUTE = 500
API_TOKENS_PER_MINUTE = 50000
# API_TOKENS_PER_MINUTE = 2000000

API_RATE_LIMIT_SAFETY_MARGIN = 0.8


# ==================== 检索与流程参数 ====================

FEWSHOT_TASK_K = {
    "mechanism": 0,
    "strategy": 0,
    "response": 2,
}
FEWSHOT_EMBEDDING_BATCH_SIZE = 64

MEMORY_TOP_K_BY_SKILL = {
    "MechanismSkill": 5,
    "UnderstandingSkill": 2,
    "StrategySkill": 5,
    "RiskSkill": 4,
    "ResponseSkill": 5,
}
MEMORY_MAX_CHARS_BY_SKILL = {
    "MechanismSkill": 2200,
    "UnderstandingSkill": 1200,
    "StrategySkill": 2200,
    "RiskSkill": 1600,
    "ResponseSkill": 2400,
}
MEMORY_MIN_SCORE_BY_SKILL = {
    "MechanismSkill": 0.25,
    "UnderstandingSkill": 0.25,
    "StrategySkill": 0.25,
    "RiskSkill": 0.20,
    "ResponseSkill": 0.20,
}

USE_MECHANISM_CALIBRATION = True
USE_RESPONSE_RISK_REVIEW = True
USE_CONCRETE_FALLBACK = True
USE_RESPONSE_CANDIDATE_RERANK = False
RESPONSE_CANDIDATE_K = 5
RESPONSE_CANDIDATE_MIN_DELTA = 0.08
USE_UNDERSTANDING_TEMPLATE_REPAIR = True
UNDERSTANDING_TEMPLATE_REPAIR_FIELDS = ("desired_feedback",)

ERROR_ANALYSIS_TOP_K = 10
ERROR_ANALYSIS_USE_LLM = True
ERROR_ANALYSIS_MAX_CASES_PER_CALL = 5
ERROR_MEMORY_MAX_ITEMS = 10

SAVE_DEBUG_TRACE = True
SAVE_LLM_CALL_LOGS = False
SAVE_PROMPT_TEXT = True
SAVE_RAW_LLM_OUTPUT = True
SAVE_FEWSHOT_LOGS = True
DEBUG_SKILL_TRACE = False


# ==================== 项目路径与模式派生 ====================

PROJECT_DIR = Path(__file__).resolve().parent
DATA_DIR = PROJECT_DIR / "data"
MEMORY_DIR = PROJECT_DIR / "memory"
OUTPUT_DIR = PROJECT_DIR / "outputs"
SCRIPTS_DIR = PROJECT_DIR / "scripts"

TRAIN_PATH = DATA_DIR / "train.jsonl"
DEV_INPUT_PATH = DATA_DIR / "dev_input.jsonl"
DEV_GOLD_PATH = DATA_DIR / "dev_gold.jsonl"
TEST_INPUT_PATH = DATA_DIR / "test_input.jsonl"
MEMORY_PATH = MEMORY_DIR / "memory.jsonl"
GENERATED_MEMORY_PATH = MEMORY_DIR / "generated.jsonl"
FORMAT_CHECKER_PATH = SCRIPTS_DIR / "format_checker.py"
EVALUATE_DEV_PATH = SCRIPTS_DIR / "evaluate_dev.py"

def derive_mode_settings(run_mode: str) -> dict[str, object]:
    """从单一运行模式派生输入、条数和评分行为。"""
    if run_mode not in {"smoke", "dev", "test"}:
        raise ValueError("RUN_MODE 只能是 smoke、dev 或 test")
    return {
        "input_path": TEST_INPUT_PATH if run_mode == "test" else DEV_INPUT_PATH,
        "max_items": 3 if run_mode == "smoke" else None,
        "run_dev_eval": run_mode in {"smoke", "dev"},
        "run_error_analysis": run_mode == "dev" and RUN_ERROR_ANALYSIS,
    }


_MODE_SETTINGS = derive_mode_settings(RUN_MODE)
INPUT_PATH = _MODE_SETTINGS["input_path"]
MAX_ITEMS = _MODE_SETTINGS["max_items"]
RUN_DEV_EVAL = _MODE_SETTINGS["run_dev_eval"]
RUN_OFFICIAL_FORMAT_CHECK = True
EFFECTIVE_ERROR_ANALYSIS = _MODE_SETTINGS["run_error_analysis"]
EFFECTIVE_SAVE_ERROR_MEMORY = (
    EFFECTIVE_ERROR_ANALYSIS and SAVE_ERROR_MEMORY
)
