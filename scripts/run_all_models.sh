#!/bin/bash
# 批量运行所有 ollama 模型的 dev baseline
set -e

MODELS=("qwen3:8b" "glm4:9b" "gemma3:12b")

for model in "${MODELS[@]}"; do
    echo "=========================================="
    echo "Running dev with model: $model"
    echo "=========================================="
    
    # 更新 .env
    cat > .env << EOF
OPENAI_BASE_URL=http://localhost:11434/v1
OPENAI_API_KEY=ollama
OPENAI_MODEL=$model

FEWSHOT_EMBEDDING_BASE_URL=
FEWSHOT_EMBEDDING_API_KEY=
FEWSHOT_EMBEDDING_MODEL=
EOF
    
    # 更新 config.py 的 RUN_MODE 为 dev
    sed -i '' 's/RUN_MODE = ".*"/RUN_MODE = "dev"/' config.py
    
    # 运行
    python3 main.py 2>&1 | tee "outputs/log_${model//\//_}.txt"
    
    echo ""
    echo "Done: $model"
    echo ""
done

echo "All models completed."
