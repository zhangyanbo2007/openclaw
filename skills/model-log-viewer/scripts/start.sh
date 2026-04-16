#!/bin/bash
# 模型日志查看器启动脚本

set -e

cd "$(dirname "$0")"

PORT=${1:-9001}

echo "========================================="
echo "  模型日志查看器"
echo "========================================="
echo ""
echo "监听端口：$PORT"
echo "工作目录：$(pwd)"
echo ""

# 检查是否已有进程在监听端口
if command -v ss &> /dev/null; then
    PORT_CHECK=$(ss -tlnp 2>/dev/null | grep ":$PORT " || true)
elif command -v netstat &> /dev/null; then
    PORT_CHECK=$(netstat -tlnp 2>/dev/null | grep ":$PORT " || true)
else
    # Fallback: 检查进程是否存在
    EXISTING_PID=$(pgrep -f "server.py.*$PORT" 2>/dev/null || true)
    if [ -n "$EXISTING_PID" ]; then
        echo "检测到已运行的服务 (PID: $EXISTING_PID)"
        echo "访问地址：http://localhost:$PORT"
        exit 0
    fi
    PORT_CHECK=""
fi

if [ -n "$PORT_CHECK" ]; then
    echo "检测到已运行的服务 (端口 $PORT 正在监听)"
    echo "访问地址：http://localhost:$PORT"
    exit 0
fi

# 清理可能存在的僵尸进程
EXISTING_PID=$(pgrep -f "server.py.*$PORT" 2>/dev/null || true)
if [ -n "$EXISTING_PID" ]; then
    echo "清理僵尸进程 (PID: $EXISTING_PID)..."
    kill $EXISTING_PID 2>/dev/null || true
    sleep 1
fi

# 启动服务
echo "启动服务..."
nohup /home/zhangyanbo/anaconda3/envs/model_proxy/bin/python server.py --port $PORT > /tmp/log_viewer.log 2>&1 &

PID=$!
echo ""
echo "========================================="
echo "  服务已启动!"
echo "========================================="
echo "  访问地址：http://localhost:$PORT"
echo "  进程 PID: $PID"
echo "  日志文件：/tmp/log_viewer.log"
echo ""
echo "功能:"
echo "  - 代理服务控制 (8888/8889 端口)"
echo "  - 实时日志查看"
echo "  - 历史会话浏览"
echo "  - 配置文件编辑"
echo "========================================="
