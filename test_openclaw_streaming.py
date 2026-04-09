#!/usr/bin/env python3
"""
在 OpenClaw 中测试两个模型的流式工具调用行为
通过 OpenClaw Gateway API 发送消息，观察流式输出差异
"""

import requests
import json
import time

# OpenClaw Gateway 配置
GATEWAY_URL = "http://localhost:18789"  # OpenClaw Gateway 默认端口

# 测试配置
TESTS = [
    {
        "name": "vLLM Qwen3.5-27B",
        "model": "vllm/qwen3.5-27b"
    },
    {
        "name": "阿里云 Qwen3.5-Plus",
        "model": "custom-dashscope-aliyuncs-com/qwen3.5-plus"
    }
]

# 测试提示词 - 需要调用工具
TEST_PROMPT = "查看一下广州今天的天气"

def test_model(model_name, model_id):
    """测试指定模型的流式输出行为"""
    print(f"\n{'='*60}")
    print(f"测试模型：{model_name} ({model_id})")
    print(f"{'='*60}\n")

    # 使用 OpenClaw 的会话 API 发送消息
    # 这里需要通过 webhook 或直接调用 agent API

    # 方法 1: 通过 OpenClaw 的 HTTP 触发器
    trigger_url = f"{GATEWAY_URL}/api/triggers/manual"

    headers = {
        "Content-Type": "application/json"
    }

    payload = {
        "agentId": "main",
        "model": model_id,
        "message": TEST_PROMPT,
        "stream": True
    }

    print(f"发送消息：{TEST_PROMPT}")
    print(f"模型：{model_id}")
    print("\n流式输出:\n")
    print("-" * 60)

    chunks = []
    first_token_time = None
    start_time = time.time()

    try:
        # 尝试通过 Gateway API 发送
        response = requests.post(trigger_url, headers=headers, json=payload, stream=True, timeout=30)

        if response.status_code == 200:
            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8')
                    chunks.append(line_str)

                    if first_token_time is None:
                        first_token_time = time.time()

                    # 打印原始输出
                    print(line_str[:200] if len(line_str) > 200 else line_str)

            elapsed = time.time() - start_time
            print(f"\n{'-'*60}")
            print(f"耗时：{elapsed:.2f}s, Chunks: {len(chunks)}")
        else:
            print(f"API 响应错误：{response.status_code}")
            print(f"响应内容：{response.text[:500]}")

    except requests.exceptions.ConnectionError:
        print(f"无法连接到 OpenClaw Gateway ({GATEWAY_URL})")
        print("请确保 Gateway 正在运行")
    except Exception as e:
        print(f"错误：{e}")

    return len(chunks)

def main():
    print("="*60)
    print("OpenClaw 流式工具调用测试")
    print("="*60)

    for test in TESTS:
        test_model(test["name"], test["model"])
        time.sleep(2)  # 等待一下再测试下一个

    print("\n\n测试完成！")
    print("请检查上面的输出，对比两个模型的流式行为差异")

if __name__ == "__main__":
    main()
