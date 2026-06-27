# Nvidia 环境运行完整 Test 说明

这份说明给使用 Nvidia GPU 的同学运行 `router` 分支。任务是读取完整 `data/test_input.jsonl`，共 409 条，生成最终 `submission.jsonl`。

## 1. 获取代码

```bash
git clone -b router https://github.com/MMO1717/humble-brag-competition.git
cd humble-brag-competition
```

如果已经有仓库：

```bash
git fetch origin
git checkout router
git pull origin router
```

## 2. Python 环境

建议使用 Python 3.10 或更高版本。

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 3. Nvidia/Ollama 模型环境

先确认机器能看到 Nvidia GPU：

```bash
nvidia-smi
```

安装 Ollama 后拉取当前推荐模型：

```bash
ollama pull gemma3:12b
ollama list
```

如果使用远程 OpenAI-compatible 服务，也可以不用本地 Ollama，只要把 `.env` 的地址、Key、模型名改成对应服务即可。

## 4. 配置 `.env`

```bash
cp .env.example .env
```

本地 Ollama 推荐配置：

```env
OPENAI_BASE_URL=http://localhost:11434/v1
OPENAI_API_KEY=ollama
OPENAI_MODEL=gemma3:12b
```

`FEWSHOT_EMBEDDING_*` 保持空即可。当前默认使用 Jaccard few-shot，不依赖 embedding 服务。

## 5. 跑完整 409 条 test

先检查实际配置：

```bash
python scripts/run_final_test.py --dry-run
```

确认输出里有：

```json
{
  "RUN_MODE": "test",
  "INPUT_PATH": "data/test_input.jsonl",
  "MAX_ITEMS": null,
  "RUN_DEV_EVAL": false,
  "RUN_OFFICIAL_FORMAT_CHECK": true
}
```

正式运行：

```bash
python scripts/run_final_test.py
```

## 6. 查看输出

运行完成后结果在：

```text
outputs/test_<时间>_gemma3_12b/
```

重点检查：

```text
outputs/test_<时间>_gemma3_12b/RES.md
outputs/test_<时间>_gemma3_12b/format_report.json
outputs/test_<时间>_gemma3_12b/submission.jsonl
```

`format_report.json` 中应满足：

```json
{
  "valid": true,
  "row_count": 409,
  "error_count": 0
}
```

最终主要使用：

```text
outputs/test_<时间>_gemma3_12b/submission.jsonl
```

## 7. 脚本固定配置

`scripts/run_final_test.py` 会临时应用以下推荐配置，不需要手动改 `config.py`：

```python
RUN_MODE = "test"
MAX_ITEMS = None
USE_MEMORY = True
USE_FEWSHOT = True
FEWSHOT_RETRIEVAL_MODE = "jaccard"
MEMORY_ROUTER_MODE = "llm_rerank"
USE_RESPONSE_CANDIDATE_RERANK = False
USE_UNDERSTANDING_TEMPLATE_REPAIR = True
UNDERSTANDING_TEMPLATE_REPAIR_FIELDS = ("desired_feedback",)
SAVE_ERROR_MEMORY = False
USE_GENERATED_MEMORY = False
```
