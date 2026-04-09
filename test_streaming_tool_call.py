#!/usr/bin/env python3
"""
流式工具调用对比测试
测试 vLLM Qwen3.5-27B vs 阿里云 Qwen3.5-Plus 在流式工具调用时的输出行为差异
"""

import requests
import json
import time
import sys

# 配置
VLLM_CONFIG = {
    "base_url": "http://192.168.68.120:5555/v1",
    "model": "qwen3.5-27b",
    "api_key": "not-needed",
    "name": "vLLM Qwen3.5-27B"
}

ALIYUN_CONFIG = {
    "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "model": "qwen3.5-plus",
    "api_key": "sk-a2675c4123764e46880426a87bff42de",
    "name": "阿里云 Qwen3.5-Plus"
}

# 测试提示词 - 需要调用两个工具
TEST_PROMPT = "请先查询广州的天气，然后告诉我今天是星期几。请调用工具完成这两个任务。"

# 工具定义
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询指定城市的天气预报",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市名称"
                    }
                },
                "required": ["city"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_date_info",
            "description": "获取当前日期和星期",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]

def print_separator(title=""):
    print("\n" + "=" * 60)
    if title:
        print(f"  {title}")
        print("=" * 60)

def test_streaming(config):
    """测试流式输出"""
    print_separator(f"测试：{config['name']}")

    url = f"{config['base_url']}/chat/completions"
    headers = {
        "Authorization": f"Bearer {config['api_key']}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": config["model"],
        "messages": [
            {"role": "user", "content": TEST_PROMPT}
        ],
        "tools": TOOLS,
        "tool_choice": "auto",
        "stream": True,
        "stream_options": {"include_usage": True}
    }

    print(f"\n请求：POST {url}")
    print(f"提示词：{TEST_PROMPT}")
    print("\n流式输出内容:\n")
    print("-" * 60)

    chunks = []
    tool_calls_buffer = {}
    content_buffer = ""
    thinking_buffer = ""
    in_thinking = False

    start_time = time.time()
    first_token_time = None

    try:
        response = requests.post(url, headers=headers, json=payload, stream=True, timeout=60)
        response.raise_for_status()

        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('data: '):
                    data_str = line_str[6:]
                    if data_str.strip() == '[DONE]':
                        break

                    try:
                        data = json.loads(data_str)
                        chunks.append(data)

                        # 解析流式数据
                        if data.get('choices') and len(data['choices']) > 0:
                            delta = data['choices'][0].get('delta', {})

                            # 记录首字时间
                            if first_token_time is None:
                                first_token_time = time.time()

                            # 检查是否有 think/reasoning 内容
                            if 'reasoning' in delta and delta['reasoning']:
                                if not in_thinking:
                                    thinking_buffer = "\n[Thinking]: "
                                    in_thinking = True
                                thinking_buffer += delta['reasoning']
                                # print(f"\033[90m{delta['reasoning']}\033[0m", end='', flush=True)

                            # 检查是否有 content 内容
                            if 'content' in delta and delta['content']:
                                content_buffer += delta['content']
                                # print(delta['content'], end='', flush=True)

                            # 检查是否有 tool_calls
                            if 'tool_calls' in delta and delta['tool_calls']:
                                for tc in delta['tool_calls']:
                                    idx = tc.get('index', 0)
                                    if idx not in tool_calls_buffer:
                                        tool_calls_buffer[idx] = {"name": "", "arguments": ""}

                                    if 'function' in tc:
                                        func = tc['function']
                                        if 'name' in func and func['name']:
                                            tool_calls_buffer[idx]['name'] += func['name']
                                        if 'arguments' in func and func['arguments']:
                                            tool_calls_buffer[idx]['arguments'] += func['arguments']

                    except json.JSONDecodeError as e:
                        print(f"\n[解析错误] {e}")
                        continue

        elapsed = time.time() - start_time
        first_token_latency = (first_token_time - start_time) * 1000 if first_token_time else 0

        print("-" * 60)
        print(f"\n统计信息:")
        print(f"  首字延迟：{first_token_latency:.0f}ms")
        print(f"  总耗时：{elapsed:.2f}s")
        print(f"  接收 chunk 数：{len(chunks)}")

        # 输出最终结果
        print(f"\n最终工具调用:")
        if tool_calls_buffer:
            for idx, tc in sorted(tool_calls_buffer.items()):
                print(f"  [{idx}] {tc['name']}({tc['arguments']})")
        else:
            print("  (无工具调用)")

        if thinking_buffer:
            print(f"\nThinking 内容长度：{len(thinking_buffer)} chars")

        if content_buffer:
            print(f"Content 内容长度：{len(content_buffer)} chars")

        # 检查是否有 thinking 标签重复的问题
        print(f"\n流式行为分析:")
        if thinking_buffer and len(thinking_buffer) > 0:
            print("  - 检测到 thinking/reasoning 输出")
        if tool_calls_buffer:
            print(f"  - 检测到 {len(tool_calls_buffer)} 个工具调用")

        return {
            "success": True,
            "first_token_latency": first_token_latency,
            "total_time": elapsed,
            "chunks": len(chunks),
            "tool_calls": len(tool_calls_buffer),
            "has_thinking": len(thinking_buffer) > 0,
            "thinking_length": len(thinking_buffer),
            "content_length": len(content_buffer)
        }

    except Exception as e:
        print(f"\n[错误] {e}")
        return {"success": False, "error": str(e)}


def main():
    print_separator("流式工具调用对比测试")
    print("目的：对比 vLLM 本地模型 vs 阿里云 在工具调用时的流式输出行为")

    # 测试 vLLM
    vllm_result = test_streaming(VLLM_CONFIG)

    # 测试阿里云
    time.sleep(1)
    aliyun_result = test_streaming(ALIYUN_CONFIG)

    # 对比总结
    print_separator("对比总结")
    print(f"{'指标':<20} {'vLLM 27B':<18} {'阿里云 Plus':<18}")
    print("-" * 60)
    print(f"{'首字延迟':<20} {vllm_result.get('first_token_latency', 0):>12.0f}ms {aliyun_result.get('first_token_latency', 0):>12.0f}ms")
    print(f"{'总耗时':<20} {vllm_result.get('total_time', 0):>12.2f}s {aliyun_result.get('total_time', 0):>12.2f}s")
    print(f"{'Chunk 数量':<20} {vllm_result.get('chunks', 0):>14} {aliyun_result.get('chunks', 0):>14}")
    print(f"{'工具调用数':<20} {vllm_result.get('tool_calls', 0):>14} {aliyun_result.get('tool_calls', 0):>14}")
    print(f"{'Thinking 输出':<20} {'是' if vllm_result.get('has_thinking') else '否':>14} {'是' if aliyun_result.get('has_thinking') else '否':>14}")
    if vllm_result.get('has_thinking') or aliyun_result.get('has_thinking'):
        print(f"{'Thinking 长度':<20} {vllm_result.get('thinking_length', 0):>14} {aliyun_result.get('thinking_length', 0):>14}")

    print("\n\n观察要点:")
    print("1. vLLM 是否会流式输出 thinking 标签内容（导致重复显示）")
    print("2. 阿里云是否也会流式输出 thinking")
    print("3. 两者的工具调用是否都是同时返回还是分步返回")

if __name__ == "__main__":
    main()
