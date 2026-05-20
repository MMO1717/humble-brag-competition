from pathlib import Path


# ===== 基础运行 =====

# 主运行模式。开发调试用 "dev"，最终生成测试集提交用 "test"。
MODE = "dev"

# 调试时设为一个小整数，例如 3；设为 None 时处理当前 split 的全部样本。
# 推荐日常开发：先 3 条冒烟，确认链路后改成 None 跑完整 dev。
# MAX_ITEMS = 3
MAX_ITEMS = None

# ===== 模型调用 =====

# 所有 LLM 调用共用的生成参数。
TEMPERATURE = 0.3
MAX_TOKENS = 256

RETRY_TIMES = 3
RETRY_SLEEP_SECONDS = 5.0

# ===== 远程 API 限速 =====

# 本地模型通常不需要限速，保持 False。
# 使用 SiliconFlow 等远程 API 时建议打开，避免超过 RPM/TPM 后触发失败重试。
ENABLE_API_RATE_LIMIT = True

# 远程服务的每分钟请求数限制。例：SiliconFlow L0 某些模型可填 500 或 1000。
API_REQUESTS_PER_MINUTE = 500
# 远程服务的每分钟 token 限制。例：L0 可能是 40000 或 2000000，请按模型额度填写。
API_TOKENS_PER_MINUTE = 2000000

# 安全系数。0.8 表示最多按官方额度的 80% 使用，减少网络抖动和估算误差导致的超限。
API_RATE_LIMIT_SAFETY_MARGIN = 0.8

# 启动时先做一次极小的 LLM 连通性检查。若 base_url/model/API key 配错，
# 直接停止运行，避免生成一整份看似合法但实际全是兜底值的 submission。
RUN_LLM_HEALTH_CHECK = True

# ===== SkillFlow 主线 =====

# v2 主流程开关。当前版本以 SkillFlow 为主线，请保持为 True。
USE_SKILLFLOW = True

# ===== Agent Memory =====

# 是否启用动态 Agent Memory 检索。静态知识始终从 agent_memory/static 读取。
USE_AGENT_MEMORY = True

# Memory 注入策略：no_memory / active / active_plus_candidate。
# 当前默认用 no_memory 保住稳定基线；做 memory 消融实验时再改成 active。
MEMORY_MODE = "active"

# 每个 Skill 最多注入几条 memory，避免 prompt 过长。
MEMORY_TOP_K_PER_SKILL = 3
MEMORY_MAX_CHARS_PER_SKILL = 1800

# 默认只让 memory 影响机制、策略、回复三个关键环节。
MEMORY_TARGET_SKILLS = ["MechanismSkill", "StrategySkill", "ResponseSkill"]

# 是否读取 agent_memory/static/ 下的静态知识。文档可中英双语，
# 但实际注入 prompt 时只使用 English Prompt Notes 段。
USE_STATIC_MEMORY = True

# ===== Few-shot =====

# 是否启用 few-shot 示例检索。第一版默认只把 few-shot 注入
# MechanismSkill 和 ResponseSkill，避免所有 prompt 都变长。
USE_FEWSHOT = True
FEWSHOT_K = 2
FEWSHOT_MIN_SCORE = 0.0
FEWSHOT_INCLUDE_FIELDS = True

# ===== Debug / 日志 =====

# 是否在终端打印每个样本经过的 skill trace，调试时可以打开。
DEBUG_SKILL_TRACE = False

# 是否保存每条样本的 Agent 链路调试信息，便于分析机制、风险、策略和回复错误。
SAVE_DEBUG_TRACE = True

# 是否保存 LLM 调用日志。只记录已有调用，不会增加 API 请求。文件较大，默认关闭；
# 需要调 prompt 时再打开。
SAVE_LLM_CALL_LOGS = False
# 调用日志中是否保存完整 prompt messages。关闭后只保存长度、耗时和结果摘要。
SAVE_PROMPT_TEXT = True
# 调用日志中是否保存模型原始输出。建议调 prompt 时保持 True。
SAVE_RAW_LLM_OUTPUT = True

# ===== 评估与错误分析 =====

# 是否在 dev 评分后额外调用独立错误分析模块。打开后会读取本次
# submission 和 dev_gold，输出 error_analysis/ 下的错例与总结。
RUN_DEV_ERROR_ANALYSIS = False
ERROR_ANALYSIS_TOP_K = 10
ERROR_ANALYSIS_USE_LLM = True
ERROR_ANALYSIS_MAX_CASES_PER_CALL = 5

# 是否从错误分析生成 candidate memory。
# 这一步是“自动生成候选记忆”，会写入 agent_memory/candidate/memory_candidates.jsonl。
GENERATE_CANDIDATE_MEMORY = False
CANDIDATE_MEMORY_TOP_K_CASES = 10
CANDIDATE_MEMORY_MAX_ITEMS = 10

# 是否把低风险 candidate memory 自动晋级到 active/memory.jsonl。
# 自动晋级只接受：schema_ok=True、置信度达标、无 review warning、类型在白名单内的候选。
# 这样下一次运行在 MEMORY_MODE="active" 下会自动使用这些 active memory。
AUTO_PROMOTE_CANDIDATE_MEMORY = False
AUTO_PROMOTE_MIN_CONFIDENCE = 0.55
AUTO_PROMOTE_REQUIRE_NO_WARNINGS = True
# 自动晋级必须带有 conditions，避免“全局规则”污染所有样本。
AUTO_PROMOTE_REQUIRE_CONDITIONS = False
AUTO_PROMOTE_ALLOWED_MEMORY_TYPES = [
    "label_confusion_memory",
    "implicit_intent_memory",
    "desired_feedback_memory",
    "risk_pattern_memory",
    "strategy_policy_memory",
    "style_adaptation_memory",
    "response_template_memory",
    "negative_memory",
]

# 运行完成后自动调用官方格式检查脚本，并把检查结果保存到 outputs/。
RUN_OFFICIAL_FORMAT_CHECK = True

# dev 模式下自动调用官方 dev 评分脚本，并把评分结果保存到 outputs/。
# MAX_ITEMS 非空时会使用本次生成的 input subset 评分；MAX_ITEMS 为 None 时评完整 dev。
RUN_DEV_EVAL = True

# 本工程不使用固定输出文件名。每次运行都会在 outputs/ 下生成一个唯一文件夹：
# 模式 + 时间戳 + 模型名 + 关键参数，避免覆盖历史结果，并方便按时间排序。
RUN_NAME_PREFIX = ""

# ===== 常用运行组合（只改下面几个开关即可）=====
# 1) 冒烟测试:
#    MODE="dev", MAX_ITEMS=3, MEMORY_MODE="no_memory", RUN_DEV_ERROR_ANALYSIS=False
# 2) 0 记忆 baseline:
#    MODE="dev", MAX_ITEMS=None, MEMORY_MODE="no_memory", USE_STATIC_MEMORY=True,
#    RUN_DEV_EVAL=True, RUN_DEV_ERROR_ANALYSIS=False, GENERATE_CANDIDATE_MEMORY=False
# 3) 全量 dev + 候选 memory 生成:
#    MODE="dev", MAX_ITEMS=None, RUN_DEV_EVAL=True, RUN_DEV_ERROR_ANALYSIS=True,
#    GENERATE_CANDIDATE_MEMORY=True, AUTO_PROMOTE_CANDIDATE_MEMORY=False
# 4) 生成 test 提交:
#    MODE="test", MAX_ITEMS=None, RUN_DEV_EVAL=False, RUN_DEV_ERROR_ANALYSIS=False

# ===== 路径 =====

# 项目路径。本文件位于 brag_pipeline/ 下，官方数据和脚本也放在该目录下。
PIPELINE_DIR = Path(__file__).resolve().parent
PUBLIC_DIR = PIPELINE_DIR / "BRAG-Agent-public"
OUTPUT_DIR = PIPELINE_DIR / "outputs"
MEMORY_DIR = PIPELINE_DIR / "agent_memory"
TRAIN_PATH = PUBLIC_DIR / "data" / "train.jsonl"

# ===== DSPy 可选实验层 =====

# DSPy 不参与主 pipeline。这里仅记录实验目录，真正使用时单独运行
# dspy_optimizer/ 下的脚本。
USE_DSPY_OPTIMIZER = False
DSPY_OPTIMIZER_DIR = PIPELINE_DIR / "dspy_optimizer"

INPUT_PATH_BY_MODE = {
    "dev": PUBLIC_DIR / "data" / "dev_input.jsonl",
    "test": PUBLIC_DIR / "data" / "test_input.jsonl",
}

INPUT_PATH = INPUT_PATH_BY_MODE[MODE]

FORMAT_CHECKER_PATH = PUBLIC_DIR / "scripts" / "format_checker.py"
EVALUATE_DEV_PATH = PUBLIC_DIR / "scripts" / "evaluate_dev.py"
DEV_GOLD_PATH = PUBLIC_DIR / "data" / "dev_gold.jsonl"
