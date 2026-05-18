from pathlib import Path


# 主运行模式。开发调试用 "dev"，最终生成测试集提交用 "test"。
MODE = "dev"

# 调试时设为一个小整数，例如 3；设为 None 时处理当前 split 的全部样本。
MAX_ITEMS = 3
# MAX_ITEMS = None

# 所有 LLM 调用共用的生成参数。
TEMPERATURE = 0.3
MAX_TOKENS = 256
RETRY_TIMES = 3
RETRY_SLEEP_SECONDS = 2.0

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

INPUT_PATH_BY_MODE = {
    "dev": PUBLIC_DIR / "data" / "dev_input.jsonl",
    "test": PUBLIC_DIR / "data" / "test_input.jsonl",
}

INPUT_PATH = INPUT_PATH_BY_MODE[MODE]

FORMAT_CHECKER_PATH = PUBLIC_DIR / "scripts" / "format_checker.py"
EVALUATE_DEV_PATH = PUBLIC_DIR / "scripts" / "evaluate_dev.py"
DEV_GOLD_PATH = PUBLIC_DIR / "data" / "dev_gold.jsonl"
