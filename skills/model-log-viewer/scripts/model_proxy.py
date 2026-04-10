#!/usr/bin/env python3
"""
模型 HTTP 代理 - 捕获 OpenClaw/ClaudeCode 的完整输入输出
支持流式 (SSE) 和非流式响应，支持基于时间窗口的会话关联
支持多模型路由（根据 model 字段转发到不同后端）
"""

import json
import hashlib
import aiohttp
from datetime import datetime
from pathlib import Path
from aiohttp import web
import argparse
from difflib import SequenceMatcher
from typing import Dict, Optional


class ConversationLogger:
    def __init__(self, base_dir: str = None):
        if base_dir is None:
            # 默认使用用户家目录下的路径
            base_dir = str(Path.home() / ".openclaw" / "model-logs")
        self.base_dir = Path(base_dir)
        try:
            self.base_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            # 如果无法创建目录，使用临时目录
            print(f"Warning: Cannot create {base_dir}, using /tmp/model-logs instead")
            self.base_dir = Path("/tmp/model-logs")
            self.base_dir.mkdir(parents=True, exist_ok=True)
        self.today_dir = self.base_dir / datetime.now().strftime("%Y-%m-%d")
        self.today_dir.mkdir(exist_ok=True)

        # 会话关联参数
        self.time_window_seconds = 60  # 60 秒内的请求可能属于同一对话
        self.similarity_threshold = 0.8  # system prompt 相似度阈值

        # 内存中的会话缓存 {conversation_id: conversation_data}
        self.active_conversations = {}

    def calculate_similarity(self, a: str, b: str) -> float:
        """计算两个字符串的相似度"""
        if not a or not b:
            return 0.0
        return SequenceMatcher(None, a, b).ratio()

    def get_system_prompt(self, messages: list) -> str:
        """提取 system prompt"""
        for msg in messages:
            if isinstance(msg, dict) and msg.get('role') == 'system':
                content = msg.get('content', '')
                if isinstance(content, str):
                    return content[:500]  # 只取前 500 字符
        return ""

    def get_user_id(self, messages: list) -> str:
        """从消息中提取用户 ID (ou_xxx 格式)"""
        import re
        for msg in messages:
            if isinstance(msg, dict):
                content = msg.get('content', '')
                # 处理 content 是列表的情况（多模态消息）
                if isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict) and 'text' in item:
                            text_content = item.get('text', '')
                            # 优先匹配 sender_id 或 id 字段中的 ou_xxx
                            match = re.search(r'(?:sender_id|sender|id|label)"?:\s*"?(ou_[a-z0-9]+)"?', text_content)
                            if match:
                                return match.group(1)
                            # 备用：匹配任何 ou_xxx
                            match = re.search(r'ou_[a-z0-9]+', text_content)
                            if match:
                                return match.group()
                # 处理 content 是字符串的情况
                elif isinstance(content, str):
                    # 优先匹配 sender_id 或 id 字段中的 ou_xxx
                    match = re.search(r'(?:sender_id|sender|id|label)"?:\s*"?(ou_[a-z0-9]+)"?', content)
                    if match:
                        return match.group(1)
                    # 备用：匹配任何 ou_xxx
                    match = re.search(r'ou_[a-z0-9]+', content)
                    if match:
                        return match.group()
        return "unknown"

    def is_new_session(self, messages: list) -> bool:
        """检查是否是新的会话（通过 /new 或 /reset 标记）"""
        for msg in messages:
            if isinstance(msg, dict) and msg.get('role') == 'user':
                content = msg.get('content', '')
                # 处理 content 是列表的情况
                if isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict) and 'text' in item:
                            if 'A new session was started via /new or /reset' in item.get('text', ''):
                                return True
                # 处理 content 是字符串的情况
                elif isinstance(content, str):
                    if 'A new session was started via /new or /reset' in content:
                        return True
        return False

    def find_matching_conversation(self, client_ip: str, messages: list, system_prompt: str) -> str:
        """
        查找是否属于已有的对话
        返回匹配的 conversation_id 或 None
        """
        now = datetime.now()

        for conv_id, conv_data in list(self.active_conversations.items()):
            # 1. 检查是否同一 IP
            if conv_data['client_ip'] != client_ip:
                continue

            # 2. 检查是否超时
            last_time = datetime.fromisoformat(conv_data['last_updated'])
            time_diff = (now - last_time).total_seconds()
            if time_diff > self.time_window_seconds:
                # 超时会话，清理
                del self.active_conversations[conv_id]
                continue

            # 3. 检查 system prompt 相似度
            old_system = conv_data.get('system_prompt', '')
            if old_system and system_prompt:
                similarity = self.calculate_similarity(old_system, system_prompt)
                if similarity >= self.similarity_threshold:
                    return conv_id

            # 4. 如果新请求是 tool 响应，说明是智能体工作流的一部分
            last_msg = messages[-1] if messages else {}
            if isinstance(last_msg, dict) and last_msg.get('role') == 'tool':
                return conv_id

        return None

    def get_conversation_id(self, client_ip: str, messages: list, headers: dict) -> str:
        """
        生成或查找会话 ID
        优先级：1. X-Session-ID 头 > 2. 用户 ID + /new 标记 > 3. 直接关联最近会话
        """
        # 尝试从请求头获取会话 ID
        session_id = headers.get("x-session-id") or headers.get("x-request-id")
        if session_id:
            return f"session_{session_id}"

        # 优先使用用户 ID 作为会话标识
        user_id = self.get_user_id(messages)
        if user_id != "unknown":
            today = datetime.now().strftime("%Y%m%d")
            base_conv_id = f"conv_{user_id}_{today}"

            # 检查是否是 /new 或 /reset 触发的新会话
            is_new = self.is_new_session(messages)

            if not is_new:
                # 不是新会话，直接关联到同一用户的最近会话（不管时间）
                for conv_id, conv_data in list(self.active_conversations.items()):
                    if conv_id.startswith(base_conv_id):
                        if conv_data['client_ip'] == client_ip:
                            return conv_id

            # 创建新的子会话（/new 标记或无匹配会话）
            conv_id = f"{base_conv_id}_{datetime.now().strftime('%H%M%S')}"
            self.active_conversations[conv_id] = {
                "client_ip": client_ip,
                "user_id": user_id,
                "system_prompt": self.get_system_prompt(messages),
                "started_at": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat(),
                "is_new_session": is_new  # 标记是否由 /new 触发
            }
            return conv_id

        # 无用户 ID 时，使用原有逻辑（时间窗口 + 相似度）
        system_prompt = self.get_system_prompt(messages)
        existing_conv = self.find_matching_conversation(client_ip, messages, system_prompt)
        if existing_conv:
            return existing_conv

        # 创建新对话 ID
        if not messages:
            conv_id = f"conv_{datetime.now().strftime('%H%M%S_%f')}"
        else:
            first_msg = messages[0]
            content = f"{first_msg.get('role', '')}:{str(first_msg.get('content', ''))[:100]}"
            hash_id = hashlib.md5(content.encode()).hexdigest()[:12]
            conv_id = f"conv_{hash_id}"

        # 缓存会话信息
        self.active_conversations[conv_id] = {
            "client_ip": client_ip,
            "system_prompt": system_prompt,
            "started_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat()
        }

        return conv_id

    def identify_client(self, headers: dict) -> str:
        ua = headers.get("user-agent", "").lower()
        if "openclaw" in ua:
            return "openclaw"
        elif "claude" in ua or "anthropic" in ua:
            return "claudecode"
        elif "openai" in ua:
            return "openai_sdk"
        return "unknown"

    def parse_sse_stream(self, sse_text: str) -> dict:
        """解析 SSE 流，提取完整的响应内容"""
        result = {
            "content": "",
            "reasoning": "",
            "tool_calls": [],
            "usage": {},
            "finish_reason": None,
            "error": None
        }
        lines = sse_text.split("\n")

        for line in lines:
            if line.startswith("data: "):
                data = line[6:]
                if data == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)

                    # 检查是否有错误
                    if chunk.get("error"):
                        result["error"] = chunk.get("error")
                        break

                    # 直接检查 chunk 是否有 usage（某些 vLLM 版本在 choices 为空的 chunk 中返回）
                    if chunk.get("usage"):
                        result["usage"] = chunk["usage"]

                    choices = chunk.get("choices", [])
                    if not choices or len(choices) == 0:
                        # 空 choices，可能是最后一个包含 usage 的 chunk
                        continue

                    choice = choices[0]
                    delta = choice.get("delta", {})

                    # 累加内容
                    if delta.get("content"):
                        result["content"] += delta["content"]
                    # 兼容多种 reasoning 字段名称：reasoning_content, reasoning, thinking
                    if delta.get("reasoning_content"):
                        result["reasoning"] += delta["reasoning_content"]
                    elif delta.get("reasoning"):
                        result["reasoning"] += delta["reasoning"]
                    elif delta.get("thinking"):
                        result["reasoning"] += delta["thinking"]

                    # 累积 tool_calls（流式响应中每个 chunk 可能包含一个工具调用片段）
                    if delta.get("tool_calls"):
                        for tc in delta["tool_calls"]:
                            index = tc.get("index", 0)
                            # 如果是新的 tool_call，创建新条目
                            if index >= len(result["tool_calls"]):
                                # 创建新的工具调用条目，初始化 arguments 为空字符串
                                new_tc = {
                                    "index": index,
                                    "id": tc.get("id", ""),
                                    "type": tc.get("type", "function"),
                                    "function": {
                                        "name": tc.get("function", {}).get("name", ""),
                                        "arguments": ""
                                    }
                                }
                                result["tool_calls"].append(new_tc)

                            # 累积参数到已存在的条目
                            if index < len(result["tool_calls"]):
                                existing = result["tool_calls"][index]
                                # 累积 name（如果有）
                                tc_name = tc.get("function", {}).get("name", "")
                                if tc_name:
                                    existing["function"]["name"] = tc_name
                                # 累积 arguments（如果有）
                                tc_args = tc.get("function", {}).get("arguments", "")
                                if tc_args:
                                    existing["function"]["arguments"] += tc_args

                    # 检查 finish_reason
                    if choice.get("finish_reason"):
                        result["finish_reason"] = choice["finish_reason"]
                except Exception as e:
                    # 记录解析错误
                    result["error"] = str(e)

        return result

    def log(self, client_ip: str, headers: dict, request_body: dict, response_data: dict,
            endpoint: str, model_name: str, is_stream: bool = False, duration: float = None):
        messages = request_body.get("messages", [])
        conv_id = self.get_conversation_id(client_ip, messages, headers)
        user_id = self.get_user_id(messages)

        # 更新会话最后活动时间
        if conv_id in self.active_conversations:
            self.active_conversations[conv_id]["last_updated"] = datetime.now().isoformat()

        client = self.identify_client(headers)

        conv_dir = self.today_dir / conv_id
        conv_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

        # 根据是否流式处理响应
        if is_stream:
            content = response_data.get("content", "")
            reasoning = response_data.get("reasoning", "")
            tool_calls = response_data.get("tool_calls", [])
            usage = response_data.get("usage", {})
            finish_reason = response_data.get("finish_reason", "")
            error = response_data.get("error")  # 流式响应可能的错误
        else:
            choice = response_data.get("choices", [{}])[0] if response_data.get("choices") else {}
            message = choice.get("message", {})
            content = message.get("content", "")
            # 兼容多种 reasoning 字段名称：reasoning_content, reasoning, thinking
            reasoning = message.get("reasoning_content", "") or message.get("reasoning", "") or message.get("thinking", "")
            tool_calls = message.get("tool_calls") or choice.get("tool_calls", [])
            usage = response_data.get("usage", {})
            finish_reason = choice.get("finish_reason", "")
            error = response_data.get("error")  # 非流式响应可能的错误

        record = {
            "timestamp": datetime.now().isoformat(),
            "client_ip": client_ip,
            "client": client,
            "user_id": user_id,
            "conversation_id": conv_id,
            "endpoint": endpoint,
            "model": model_name,
            "is_stream": is_stream,
            "request": {
                "model": request_body.get("model", "unknown"),
                "messages": request_body.get("messages", []),
                "parameters": {k: v for k, v in request_body.items() if k not in ["model", "messages", "endpoint"]}
            },
            "response": {
                "content": content,
                "reasoning": reasoning,
                "tool_calls": tool_calls,
                "usage": usage,
                "finish_reason": finish_reason,
                "duration": duration,  # 新增：运行时间（秒）
                "error": error  # 新增：错误信息（如果有）
            }
        }

        log_file = conv_dir / f"{timestamp}_{client}.json"
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(record, f, indent=2, ensure_ascii=False)

        index_file = conv_dir / "index.json"
        if index_file.exists():
            with open(index_file, "r", encoding="utf-8") as f:
                index = json.load(f)
        else:
            index = {
                "conversation_id": conv_id,
                "user_id": user_id,
                "client": client,
                "first_message": messages[0] if messages else None,
                "started_at": record["timestamp"],
                "requests": []
            }

        index["last_updated"] = record["timestamp"]
        index["request_count"] = index.get("request_count", 0) + 1
        index["requests"].append({
            "timestamp": record["timestamp"],
            "model": model_name,
            "tokens": usage.get("total_tokens", 0),
            "user_id": user_id
        })

        with open(index_file, "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2, ensure_ascii=False)

        print(f"[{datetime.now().strftime('%H:%M:%S')}] {client_ip} | {client} | model={model_name} | conv={conv_id} | {endpoint} | stream={is_stream}")
        return conv_id, log_file


class VLLMProxy:
    def __init__(self, config: dict, port: int = None):
        self.models: Dict[str, dict] = config.get("models", {})
        self.default_model = config.get("default_model")
        self.logs_dir = config.get("logs_dir", "/home/zhangyanbo/.openclaw/model-logs")
        self.port = port

        # 如果是新的配置格式（只有 enabled_models 和 model_port_mapping），从 openclaw.json 加载模型信息
        if not self.models and config.get("model_port_mapping"):
            self._load_models_from_openclaw(config, port)

        self.logger = ConversationLogger(base_dir=self.logs_dir)
        self.app = web.Application()

        # 注册所有路由
        self.app.router.add_route("*", "/{path:.*}", self.handle_request)

        # 打印配置信息
        print("=" * 60)
        print("vLLM 多模型代理配置:")
        print("-" * 60)
        for name, info in self.models.items():
            marker = " (default)" if name == self.default_model else ""
            print(f"  {name}{marker}: {info['url']} - {info.get('name', '未命名')}")
        print("-" * 60)
        print(f"日志目录：{Path(self.logger.base_dir).absolute()}")
        print("=" * 60)

    def _load_models_from_openclaw(self, config: dict, port: int = None):
        """从 openclaw.json 加载模型配置，只加载当前端口对应的模型"""
        from pathlib import Path
        import json

        openclaw_path = Path.home() / ".openclaw" / "openclaw.json"
        if not openclaw_path.exists():
            print(f"Warning: openclaw.json not found at {openclaw_path}")
            return

        try:
            with open(openclaw_path, "r", encoding="utf-8") as f:
                openclaw = json.load(f)

            providers = openclaw.get("models", {}).get("providers", {})
            model_port_mapping = config.get("model_port_mapping", {})

            # 只加载当前端口对应的模型
            for model_key, model_port in model_port_mapping.items():
                if port is not None and model_port != port:
                    continue  # 跳过非当前端口的模型

                if model_key in [f"{p}/{m['id']}" for p in providers for m in providers[p].get("models", [])]:
                    for provider_name, provider_config in providers.items():
                        base_url = provider_config.get("baseUrl", "")
                        api_key = provider_config.get("apiKey", "")
                        for model in provider_config.get("models", []):
                            full_key = f"{provider_name}/{model.get('id', '')}"
                            if full_key == model_key:
                                self.models[model_key] = {
                                    "url": base_url,
                                    "name": model.get("name", model.get("id", "")),
                                    "provider": provider_name,
                                    "model_id": model.get("id", ""),
                                    "api_key": api_key  # 保存 API 密钥
                                }
                                break
        except Exception as e:
            print(f"Error loading models from openclaw.json: {e}")

    def get_backend_url(self, model_name: str) -> Optional[str]:
        """根据模型名获取后端 URL"""
        if model_name in self.models:
            return self.models[model_name]["url"]

        # 尝试模糊匹配（去除版本号等）
        model_lower = model_name.lower()
        for name, info in self.models.items():
            name_lower = name.lower().replace("-", "").replace("_", "")
            model_clean = model_lower.replace("-", "").replace("_", "")
            if name_lower in model_clean or model_clean in name_lower:
                return info["url"]

        # 返回默认模型
        if self.default_model and self.default_model in self.models:
            return self.models[self.default_model]["url"]

        return None

    async def handle_request(self, request: web.Request) -> web.Response:
        client_ip = request.remote or "unknown"
        headers = dict(request.headers)
        path = request.match_info["path"]

        request_body = {}
        if request.can_read_body:
            body_bytes = await request.read()
            try:
                request_body = json.loads(body_bytes.decode("utf-8"))
            except:
                pass

        # 获取请求的模型名
        requested_model = request_body.get("model", "")
        backend_url = self.get_backend_url(requested_model)
        used_model_name = requested_model if backend_url else "unknown"

        if not backend_url:
            return web.json_response({
                "error": f"模型 '{requested_model}' 未配置，可用的模型：{list(self.models.keys())}"
            }, status=400)

        # 获取 API 密钥
        api_key = self.models.get(requested_model, {}).get("api_key", "")

        # 保存原始 path 用于日志记录
        original_path = path

        # 构建后端 URL - backend_url 已包含/v1，path 去掉前导斜杠和 v1 前缀
        raw_path = path.lstrip("/")
        if raw_path.startswith("v1/"):
            raw_path = raw_path[3:]
        url = f"{backend_url}/{raw_path}"

        # 如果是流式请求，添加 stream_options 以获取 usage
        request_body_copy = request_body.copy() if request_body else {}
        if request_body_copy.get("stream", False) and "stream_options" not in request_body_copy:
            request_body_copy["stream_options"] = {"include_usage": True}

        # 构建请求头，添加 Authorization
        forward_headers = {k: v for k, v in headers.items() if k.lower() not in ['host', 'content-length']}
        if api_key and "authorization" not in [k.lower() for k in forward_headers.keys()]:
            forward_headers["Authorization"] = f"Bearer {api_key}"
        request_start = datetime.now()

        # 配置超时：连接 10 秒，读取 120 秒（推理模型可能需要较长时间）
        timeout = aiohttp.ClientTimeout(total=120, connect=10, sock_read=120)

        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.request(
                    method=request.method,
                    url=url,
                    json=request_body_copy if request_body_copy else None,
                    headers=forward_headers
                ) as resp:
                    content_type = resp.content_type

                    # 检查是否流式响应
                    is_stream = "text/event-stream" in content_type or request_body.get("stream", False)

                    if is_stream:
                        # 流式响应：读取完整文本后解析 SSE
                        sse_text = await resp.text()
                        response_data = self.logger.parse_sse_stream(sse_text)

                        # 创建代理响应（流式返回）
                        proxy_resp = web.StreamResponse(status=resp.status, headers={"Content-Type": "text/event-stream"})
                        await proxy_resp.prepare(request)
                        await proxy_resp.write(sse_text.encode())
                        await proxy_resp.write_eof()
                    else:
                        # 非流式响应：JSON
                        response_data = await resp.json()
                        proxy_resp = web.json_response(response_data, status=resp.status)

                    # 记录请求结束时间并计算运行时间
                    request_end = datetime.now()
                    duration = (request_end - request_start).total_seconds()

                    # 记录日志（只记录 v1 开头的请求）
                    if original_path.startswith("v1/"):
                        self.logger.log(
                            client_ip=client_ip,
                            headers=headers,
                            request_body=request_body,
                            response_data=response_data,
                            endpoint=original_path,
                            model_name=used_model_name,
                            is_stream=is_stream,
                            duration=duration  # 新增：运行时间
                        )

                    return proxy_resp

        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)


def load_config(config_path: str) -> dict:
    """加载配置文件"""
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser(description="vLLM HTTP 代理 (支持多模型路由)")
    parser.add_argument("--host", default="0.0.0.0", help="监听地址")
    parser.add_argument("--port", type=int, default=8888, help="监听端口")
    parser.add_argument("--config", default="proxy_config.json", help="配置文件路径")
    args = parser.parse_args()

    # 加载配置
    config = load_config(args.config)
    config["proxy_host"] = args.host
    config["proxy_port"] = args.port

    proxy = VLLMProxy(config, port=args.port)
    print(f"\n代理服务启动：http://{args.host}:{args.port}")
    print(f"日志目录：{Path(config.get('logs_dir', '/home/zhangyanbo/.openclaw/model-logs')).absolute()}\n")
    web.run_app(proxy.app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
