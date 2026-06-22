from pathlib import Path

import config
from src.llm_client import load_env
from src.pipeline import run_pipeline


def main() -> None:
    """加载 API 配置并执行当前运行模式。"""
    load_env(Path(__file__).resolve().parent / ".env")
    run_pipeline(config)


if __name__ == "__main__":
    main()
