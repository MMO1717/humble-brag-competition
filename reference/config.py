from pathlib import Path


# 主运行模式。开发调试用 "dev"，最终生成测试集提交用 "test"。
MODE = "dev"

# 调试时设为一个小整数，例如 3；设为 None 时处理当前 split 的全部样本。
# MAX_ITEMS = 3
MAX_ITEMS = None

# 所有 LLM 调用共用的生成参数。
TEMPERATURE = 0.3
MAX_TOKENS = 256
RETRY_TIMES = 3
RETRY_SLEEP_SECONDS = 2.0

# 启动时先做一次极小的 LLM 连通性检查。若 base_url/model/API key 配错，
# 直接停止运行，避免生成一整份看似合法但实际全是兜底值的 submission。
RUN_LLM_HEALTH_CHECK = True

# 主流程开关。False 时运行 Step 1 的单次调用 BaselineFlow；
# True 时运行 Step 2 之后的固定 SkillFlow。
USE_SKILLFLOW = True

# 是否读取 agent_wiki/ 下的静态知识。Wiki 文档可中英双语，
# 但实际注入 prompt 时只使用英文摘要段。
USE_AGENT_WIKI = True

# 是否启用 few-shot 示例检索。第一版默认只把 few-shot 注入
# MechanismSkill 和 ResponseSkill，避免所有 prompt 都变长。
USE_FEWSHOT = True
FEWSHOT_K = 2
FEWSHOT_MIN_SCORE = 0.0
FEWSHOT_INCLUDE_FIELDS = True

# 是否在终端打印每个样本经过的 skill trace，调试时可以打开。
DEBUG_SKILL_TRACE = False

# 是否保存每条样本的 Agent 链路调试信息，便于分析机制、风险、策略和回复错误。
SAVE_DEBUG_TRACE = True

# 是否保存 LLM 调用日志。只记录已有调用，不会增加 API 请求。文件较大，默认关闭；
# 需要调 prompt 时再打开。
SAVE_LLM_CALL_LOGS = True
# 调用日志中是否保存完整 prompt messages。关闭后只保存长度、耗时和结果摘要。
SAVE_PROMPT_TEXT = True
# 调用日志中是否保存模型原始输出。建议调 prompt 时保持 True。
SAVE_RAW_LLM_OUTPUT = True

# 是否在 dev 评分后额外调用独立错误分析模块。默认关闭；打开后会读取本次
# submission 和 dev_gold，输出 error_analysis/ 下的错例与总结。
RUN_DEV_ERROR_ANALYSIS = True
ERROR_ANALYSIS_TOP_K = 10
ERROR_ANALYSIS_USE_LLM = True
ERROR_ANALYSIS_MAX_CASES_PER_CALL = 5

# 运行完成后自动调用官方格式检查脚本，并把检查结果保存到 outputs/。
RUN_OFFICIAL_FORMAT_CHECK = True

# dev 模式下自动调用官方 dev 评分脚本，并把评分结果保存到 outputs/。
# MAX_ITEMS 非空时会使用本次生成的 input subset 评分；MAX_ITEMS 为 None 时评完整 dev。
RUN_DEV_EVAL = True

# 本工程不使用固定输出文件名。每次运行都会在 outputs/ 下生成一个唯一文件夹：
# 模式 + 时间戳 + 模型名 + 关键参数，避免覆盖历史结果，并方便按时间排序。
RUN_NAME_PREFIX = ""

# 项目路径。本文件位于 brag_pipeline/ 下，官方数据和脚本也放在该目录下。
PIPELINE_DIR = Path(__file__).resolve().parent
PUBLIC_DIR = PIPELINE_DIR / "BRAG-Agent-public"
OUTPUT_DIR = PIPELINE_DIR / "outputs"
WIKI_DIR = PIPELINE_DIR / "agent_wiki"
TRAIN_PATH = PUBLIC_DIR / "data" / "train.jsonl"

INPUT_PATH_BY_MODE = {
    "dev": PUBLIC_DIR / "data" / "dev_input.jsonl",
    "test": PUBLIC_DIR / "data" / "test_input.jsonl",
}

INPUT_PATH = INPUT_PATH_BY_MODE[MODE]

FORMAT_CHECKER_PATH = PUBLIC_DIR / "scripts" / "format_checker.py"
EVALUATE_DEV_PATH = PUBLIC_DIR / "scripts" / "evaluate_dev.py"
DEV_GOLD_PATH = PUBLIC_DIR / "data" / "dev_gold.jsonl"
