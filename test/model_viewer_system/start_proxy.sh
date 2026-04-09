#!/bin/bash
# vLLM 多模型代理启动脚本
# 支持 qwen3.5-27b 和 gemma-4-31b-it 两个模型

set -e

CONFIG_FILE="/code/project/deploy_model/proxy_config.json"
PROXY_PORT=8888

echo "========================================="
echo "  启动 vLLM 多模型代理服务"
echo "========================================="
echo ""

# 检查配置文件
if [ ! -f "$CONFIG_FILE" ]; then
    echo "错误：配置文件不存在：$CONFIG_FILE"
    exit 1
fi

echo "配置文件：$CONFIG_FILE"
echo ""
echo "模型配置:"
cat "$CONFIG_FILE" | python3 -c "
import sys, json
config = json.load(sys.stdin)
for name, info in config.get('models', {}).items():
    marker = ' (default)' if name == config.get('default_model') else ''
    print(f'  - {name}{marker}: {info[\"url\"]}')
"
echo ""
echo "========================================="

# 检查已有的代理进程
EXISTING_PID=$(pgrep -f "vllm_proxy.py.*$PROXY_PORT" 2>/dev/null || true)
if [ -n "$EXISTING_PID" ]; then
    echo "检测到已有的代理进程 (PID: $EXISTING_PID)，正在停止..."
    kill $EXISTING_PID 2>/dev/null || true
    sleep 2
fi

# 启动代理服务
echo "启动代理服务..."
cd /code/project/deploy_model
nohup /root/anaconda3/envs/vllm/bin/python -u vllm_proxy.py \
    --host 0.0.0.0 \
    --port $PROXY_PORT \
    --config "$CONFIG_FILE" \
    > /tmp/vllm_proxy.log 2>&1 &

PROXY_PID=$!
echo ""
echo "========================================="
echo "  代理服务已启动!"
echo "========================================="
echo "  监听地址：http://0.0.0.0:$PROXY_PORT"
echo "  进程 PID: $PROXY_PID"
echo "  日志文件：/tmp/vllm_proxy.log"
echo ""
echo "可用模型:"
echo "  - qwen3.5-27b    -> http://localhost:$PROXY_PORT/v1/chat/completions"
echo "  - gemma-4-31b-it -> http://localhost:$PROXY_PORT/v1/chat/completions"
echo ""
echo "使用示例:"
echo "  curl http://localhost:$PROXY_PORT/v1/chat/completions \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"model\": \"qwen3.5-27b\", \"messages\": [{\"role\": \"user\", \"content\": \"你好\"}]}'"
echo ""
echo "========================================="
