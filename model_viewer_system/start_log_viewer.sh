#!/bin/bash
# 日志查看器启动脚本

set -e

echo "========================================="
echo "  启动日志查看器"
echo "========================================="

cd /code/project/deploy_model

# 检查是否已有进程
EXISTING_PID=$(pgrep -f "log_server.py" 2>/dev/null || true)
if [ -n "$EXISTING_PID" ]; then
    echo "检测到已有的日志查看器进程 (PID: $EXISTING_PID)"
    echo "访问地址：http://localhost:9000"
    exit 0
fi

# 启动日志查看器
echo "启动日志查看器服务..."
nohup /root/anaconda3/envs/vllm/bin/python log_server.py > /tmp/log_server.log 2>&1 &

PID=$!
echo ""
echo "========================================="
echo "  日志查看器已启动!"
echo "========================================="
echo "  访问地址：http://localhost:9000"
echo "  进程 PID: $PID"
echo "  日志文件：/tmp/log_server.log"
echo ""
echo "支持功能:"
echo "  - 查看和选择代理端口 (8888/9999)"
echo "  - 启动/停止代理服务"
echo "  - 查看实时日志"
echo "  - 浏览历史会话"
echo "========================================="
