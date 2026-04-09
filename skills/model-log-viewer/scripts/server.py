#!/usr/bin/env python3
"""
模型日志查看器 + 代理服务控制
支持多模型代理启动/停止，实时日志查看，会话浏览
"""

import json
import subprocess
import threading
import signal
import os
import time
import re
import socket
from pathlib import Path
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
import urllib.parse
from socketserver import ThreadingMixIn

# 配置
BASE_DIR = Path(__file__).parent
LOGS_DIR = Path.home() / ".openclaw" / "model-logs"  # 日志目录放到外面的 model-logs 文件夹

# 全局状态
proxy_processes = {}
proxy_logs = {}
LOG_MAX_LINES = 500


def is_port_in_use(port):
    """检查端口是否被占用（通过 socket 连接测试）"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


class LogViewerHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)

        if parsed.path == "/":
            self.send_file("index.html")
        elif parsed.path == "/detail":
            # 详情页：渲染 HTML
            self.render_detail_page(
                query.get("date", [datetime.now().strftime("%Y-%m-%d")])[0],
                query.get("conv_id", [""])[0]
            )
        elif parsed.path.startswith("/api/conversations") or parsed.path.startswith("/api/logs/conversations"):
            self.get_conversations(query.get("date", [datetime.now().strftime("%Y-%m-%d")])[0])
        elif parsed.path.startswith("/api/requests") or parsed.path.startswith("/api/logs/requests"):
            self.get_requests(query.get("date", [datetime.now().strftime("%Y-%m-%d")])[0],
                             query.get("start", ["00:00"])[0],
                             query.get("end", ["23:59"])[0])
        elif parsed.path.startswith("/api/logs/detail"):
            self.get_detail(
                query.get("date", [datetime.now().strftime("%Y-%m-%d")])[0],
                query.get("id", [""])[0]
            )
        elif parsed.path.startswith("/api/proxy/log"):
            port = query.get("port", ["8888"])[0]
            self.get_proxy_log(int(port))
        elif parsed.path.startswith("/api/proxy/status"):
            self.get_proxy_status()
        elif parsed.path.startswith("/api/proxy/config"):
            self.get_config()
        elif parsed.path.startswith("/api/openclaw/models"):
            self.get_openclaw_models()
        elif parsed.path == "/api/sync":
            # GET request: return current config
            self.get_config()
        elif parsed.path.startswith("/api/export/excel"):
            self.export_excel(query.get("date", [datetime.now().strftime("%Y-%m-%d")])[0],
                             query.get("start", ["00:00"])[0],
                             query.get("end", ["23:59"])[0])
        else:
            # 静态文件
            super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        content_length = int(self.headers.get('Content-Length', 0))
        body = json.loads(self.rfile.read(content_length).decode()) if content_length else {}

        if parsed.path == "/api/proxy/start":
            self.start_proxy(body.get("port", 8888), body.get("config", "proxy_config.json"))
        elif parsed.path == "/api/proxy/stop":
            self.stop_proxy(body.get("port", 8888))
        elif parsed.path == "/api/proxy/save_config":
            self.save_config(body)
        elif parsed.path == "/api/sync":
            self.sync_to_openclaw_post(body)
        else:
            self.send_error(404)

    def send_file(self, filename):
        filepath = BASE_DIR / filename
        if filepath.exists():
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(content.encode("utf-8"))
        else:
            self.send_error(404, f"File not found: {filename}")

    def send_json(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

    def get_conversations(self, date):
        """获取会话列表"""
        date_dir = LOGS_DIR / date
        conversations = []

        if date_dir.exists():
            for conv_dir in sorted(date_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
                if conv_dir.is_dir():
                    index_file = conv_dir / "index.json"
                    if index_file.exists():
                        with open(index_file, "r", encoding="utf-8") as f:
                            conv_data = json.load(f)
                        conv_data["id"] = conv_dir.name
                        conversations.append(conv_data)

        self.send_json({"success": True, "conversations": conversations})

    def get_requests(self, date, time_start="00:00", time_end="23:59"):
        """获取所有请求数据（用于前端处理）"""
        date_dir = LOGS_DIR / date
        all_requests = []

        if date_dir.exists():
            for conv_dir in sorted(date_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
                if not conv_dir.is_dir():
                    continue
                index_file = conv_dir / "index.json"
                if not index_file.exists():
                    continue

                with open(index_file, "r", encoding="utf-8") as f:
                    index_data = json.load(f)

                conv_started_at = index_data.get("started_at", "")
                conv_time = conv_started_at[11:16] if conv_started_at else ""

                if time_start <= conv_time <= time_end:
                    for log_file in sorted(conv_dir.glob("*.json")):
                        if log_file.name == "index.json":
                            continue
                        with open(log_file, "r", encoding="utf-8") as f:
                            record = json.load(f)
                            record["conversation_id"] = conv_dir.name
                            record["user_id"] = index_data.get("user_id", "unknown")
                            all_requests.append(record)

        self.send_json({"success": True, "requests": all_requests})

    def export_excel(self, date, time_start="00:00", time_end="23:59"):
        """导出 Excel（指定日期的所有数据）"""
        try:
            import openpyxl
        except ImportError:
            self.send_json({"success": False, "error": "openpyxl 未安装，请先运行：pip install openpyxl"})
            return

        from io import BytesIO

        # 获取请求数据
        date_dir = LOGS_DIR / date
        requests_list = []

        if date_dir.exists():
            for conv_dir in sorted(date_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
                if not conv_dir.is_dir():
                    continue
                index_file = conv_dir / "index.json"
                if not index_file.exists():
                    continue

                with open(index_file, "r", encoding="utf-8") as f:
                    index_data = json.load(f)

                conv_started_at = index_data.get("started_at", "")
                conv_time = conv_started_at[11:16] if conv_started_at else ""

                if time_start <= conv_time <= time_end:
                    for log_file in sorted(conv_dir.glob("*.json")):
                        if log_file.name == "index.json":
                            continue
                        with open(log_file, "r", encoding="utf-8") as f:
                            record = json.load(f)
                            requests_list.append({
                                "conversation_id": conv_dir.name,
                                "user_id": index_data.get("user_id", "unknown"),
                                **record
                            })

        # 创建 Excel
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "对话日志"

        headers = [
            "序号", "时间戳", "日期", "时间", "会话 ID", "用户 ID", "客户端 IP", "客户端",
            "端点", "模型", "角色", "请求内容 (完整)", "响应内容 (完整)", "推理过程",
            "Prompt Tokens", "Completion Tokens", "Total Tokens", "Finish Reason",
            "是否流式", "Tool Calls"
        ]
        ws.append(headers)

        for idx, req in enumerate(requests_list, 1):
            timestamp = req.get("timestamp", "")
            date_only = timestamp[:10] if timestamp else ""
            time_only = timestamp[11:19] if timestamp else ""

            request_data = req.get("request", {})
            response_data = req.get("response", {})

            messages = request_data.get("messages", [])
            last_msg = messages[-1] if messages else {}
            role = last_msg.get("role", "")

            full_request_content = json.dumps(messages, ensure_ascii=False, indent=2)

            content = response_data.get("content", "")
            reasoning = response_data.get("reasoning", "")
            tool_calls = response_data.get("tool_calls", [])
            usage = response_data.get("usage", {})

            row = [
                idx,
                timestamp,
                date_only,
                time_only,
                req.get("conversation_id", ""),
                req.get("user_id", ""),
                req.get("client_ip", ""),
                req.get("client", ""),
                req.get("endpoint", ""),
                request_data.get("model", ""),
                role,
                full_request_content,
                content,
                reasoning,
                usage.get("prompt_tokens", 0),
                usage.get("completion_tokens", 0),
                usage.get("total_tokens", 0),
                response_data.get("finish_reason", ""),
                str(req.get("is_stream", False)),
                json.dumps(tool_calls, ensure_ascii=False) if tool_calls else ""
            ]
            ws.append(row)

        # 设置列宽
        for i, col_letter in enumerate(['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T']):
            ws.column_dimensions[col_letter].width = 20
        ws.column_dimensions['L'].width = 80
        ws.column_dimensions['M'].width = 80
        ws.column_dimensions['N'].width = 50

        # 保存到内存
        output = BytesIO()
        wb.save(output)
        output.seek(0)

        filename = f"log_{date}_{time_start}_{time_end}.xlsx"

        self.send_response(200)
        self.send_header("Content-Type", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.end_headers()
        self.wfile.write(output.getvalue())

    def get_detail(self, date, conv_id):
        """获取会话详情（API）"""
        conv_dir = LOGS_DIR / date / conv_id
        records = []
        user_id = "unknown"

        if conv_dir.exists():
            for log_file in sorted(conv_dir.glob("*.json")):
                if log_file.name != "index.json":
                    with open(log_file, "r", encoding="utf-8") as f:
                        records.append(json.load(f))

            index_file = conv_dir / "index.json"
            if index_file.exists():
                with open(index_file, "r", encoding="utf-8") as f:
                    user_id = json.load(f).get("user_id", "unknown")

        self.send_json({
            "success": True,
            "records": records,
            "user_id": user_id
        })

    def render_detail_page(self, date: str, conv_id: str):
        """渲染详情页 HTML - 完整对话时间轴，包含 User/Assistant/工具/模型四种角色"""
        conv_dir = LOGS_DIR / date / conv_id
        if not conv_dir.exists():
            self.send_error(404, "Conversation not found")
            return

        # 读取数据
        records = []
        user_id = "unknown"
        index_data = {}

        index_file = conv_dir / "index.json"
        if index_file.exists():
            with open(index_file, "r", encoding="utf-8") as f:
                index_data = json.load(f)
                user_id = index_data.get("user_id", "unknown")

        for log_file in sorted(conv_dir.glob("*.json")):
            if log_file.name != "index.json":
                with open(log_file, "r", encoding="utf-8") as f:
                    records.append(json.load(f))

        requests = sorted(records, key=lambda x: x["timestamp"])

        # 构建代理模型 URL 映射
        proxy_model_info = {}
        config_file = BASE_DIR / "proxy_config.json"
        openclaw_config_path = Path.home() / ".openclaw" / "openclaw.json"

        if config_file.exists() and openclaw_config_path.exists():
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    proxy_config = json.load(f)
                with open(openclaw_config_path, "r", encoding="utf-8") as f:
                    openclaw_config = json.load(f)

                model_port_mapping = proxy_config.get("model_port_mapping", {})
                providers = openclaw_config.get("models", {}).get("providers", {})

                for model_key, port in model_port_mapping.items():
                    parts = model_key.split("/")
                    if len(parts) >= 2:
                        provider_name = parts[0]
                        model_name = "/".join(parts[1:])
                        provider = providers.get(provider_name, {})
                        base_url = provider.get("baseUrl", "")
                        proxy_model_info[model_name] = {
                            "proxy_url": f"http://localhost:{port}/v1",
                            "original_url": base_url,
                            "model": model_name,
                        }
            except:
                pass

        # 按时间轴展开所有事件（User/Assistant/Tool/Model 四种角色）
        timeline_events = []
        prev_timestamp = None
        session_start = index_data.get("started_at")  # 用于计算第一个请求的间隔
        round_num = 0  # 轮次计数器（只在用户输入时递增）

        def extract_user_text(content) -> tuple:
            """提取真正的用户消息（带 ou_ ID 或 GMT+8 时间戳的实际问题）"""
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and "text" in item:
                        text = item["text"]
                        # 模式 1: [Day YYYY-MM-DD HH:MM GMT+8] 用户问题
                        match = re.search(r'\[(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}\s+GMT\+\d+\]\s*(.+?)(?:\n\n|$)', text, re.DOTALL)
                        if match:
                            user_text = match.group(1).strip()
                            if user_text and len(user_text) > 1 and not user_text.startswith('A new session') and not user_text.startswith('<conversation'):
                                return (True, user_text[:500])
                        # 模式 2: [User]: 用户问题
                        match = re.search(r'\[User\]:\s*(.+?)(?:\n\n|$)', text, re.DOTALL)
                        if match:
                            user_text = match.group(1).strip()
                            if user_text and len(user_text) > 1:
                                return (True, user_text[:500])
                        # 模式 3: Sender 格式的 UI 消息
                        match = re.search(r'Sender.*?\n(?:```json.*?```\n)?\[(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}\s+GMT\+\d+\]\s*(.+?)(?:\n\n|$)', text, re.DOTALL)
                        if match:
                            user_text = match.group(1).strip()
                            if user_text and len(user_text) > 1:
                                return (True, user_text[:500])
            return (False, "")

        def escape_html(text: str) -> str:
            if not text:
                return ""
            return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("\n", "<br>")

        def render_message_content(content, role: str = "") -> str:
            if content is None:
                return ""
            if isinstance(content, list):
                parts = []
                for item in content:
                    if isinstance(item, dict):
                        if "text" in item:
                            parts.append(item["text"])
                        elif "image_url" in item:
                            parts.append("[Image]")
                content = "\n\n".join(parts)
            elif not isinstance(content, str):
                content = str(content)
            return escape_html(content)

        def get_role_style(role: str) -> dict:
            styles = {
                "system": {"color": "#e65100", "bg": "#fff3e0", "label": "⚙️ system", "border": "#ff9800"},
                "user": {"color": "#1565c0", "bg": "#e3f2fd", "label": "👤 User", "border": "#2196f3"},
                "assistant": {"color": "#2e7d32", "bg": "#e8f5e9", "label": "🤖 Assistant", "border": "#4caf50"},
                "tool": {"color": "#6a1b9a", "bg": "#f3e5f5", "label": "🔧 Tool", "border": "#9c27b0"},
                "model": {"color": "#00796b", "bg": "#e0f2f1", "label": "🤖 Model", "border": "#009688"},
            }
            return styles.get(role, {"color": "#666", "bg": "#f5f5f5", "label": role, "border": "#999"})

        # 按时间顺序处理每个请求，只保留一个"模型"角色
        timeline_events = []
        round_num = 0  # 轮次计数器（只在用户输入时递增）

        for req in requests:
            timestamp = req["timestamp"]
            messages = req["request"].get("messages", [])
            response = req["response"]
            usage = response.get("usage", {})
            request_model = req["request"].get("model", "")
            tool_calls = response.get("tool_calls", []) or []

            model_info = proxy_model_info.get(request_model, {})
            proxy_url = model_info.get("proxy_url", "")
            original_url = model_info.get("original_url", "")
            model_name = model_info.get("model", request_model)

            # 从 response 中读取 duration（运行时间）
            duration = response.get("duration")
            if duration:
                interval_str = f"{duration:.1f}s"
            else:
                interval_str = "-"

            # 提取用户消息（仅用于显示轮次号）
            for msg in messages:
                if msg.get("role") == "user":
                    content = msg.get("content", "")
                    is_real_user, extracted_text = extract_user_text(content)
                    if is_real_user:
                        round_num += 1
                        break  # 每个请求只计一次轮次

            # 添加 Model 行（模型的输入和输出）
            resp_content = response.get("content") or ""
            reasoning = response.get("reasoning") or ""
            if not isinstance(resp_content, str):
                resp_content = str(resp_content)

            # 构建输出内容：包含 content + reasoning + tool_calls
            output_parts = []
            if resp_content:
                output_parts.append(resp_content)
            if reasoning:
                output_parts.append(f"\n\n[Thinking]: {reasoning}")
            if tool_calls:
                for tc in tool_calls:
                    func = tc.get("function", {})
                    tool_name = func.get("name", "unknown")
                    tool_args = func.get("arguments", "{}")
                    output_parts.append(f"\n\n[Tool Call]: {tool_name}({tool_args})")

            # 从 response 中读取 duration（运行时间）
            duration = response.get("duration")
            if duration:
                duration_str = f"{duration:.1f}s"
            else:
                duration_str = "-"

            timeline_events.append({
                "round": round_num,
                "timestamp": timestamp,
                "role": "model",
                "input": messages,  # 完整的输入消息
                "output": "".join(output_parts),
                "interval": duration_str,  # 使用运行时间
                "model_info": {
                    "proxy_url": proxy_url,
                    "original_url": original_url,
                    "model": model_name,
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0)
                }
            })

        # 构建 HTML 行 - 只显示模型角色
        rows = []
        last_round = 0

        for event in timeline_events:
            round_num = event["round"]
            timestamp = event["timestamp"]
            role = event["role"]
            interval = event.get("interval", "-")

            # Model 行（模型调用详情）
            model_info = event.get("model_info", {})
            input_messages = event.get("input", [])
            model_output = event.get("output", "")

            proxy_url_display = model_info.get("proxy_url", "N/A")
            original_url_display = model_info.get("original_url", "N/A")
            model_display = model_info.get("model", "N/A")
            prompt_tokens = model_info.get("prompt_tokens", 0)
            completion_tokens = model_info.get("completion_tokens", 0)

            # 生成模型输入的 HTML
            input_html = ""
            for msg in input_messages:
                msg_role = msg.get("role", "unknown")
                msg_content = msg.get("content", "")
                msg_style = get_role_style(msg_role)
                input_html += f'''
                    <div style="margin-bottom: 10px; padding: 8px; background: {msg_style['bg']}; border-radius: 4px; border-left: 3px solid {msg_style['border']};">
                        <div style="font-size: 11px; font-weight: 600; color: {msg_style['color']}; margin-bottom: 4px;">{msg_style['label']}</div>
                        <div style="font-size: 12px; white-space: pre-wrap; word-break: break-word; line-height: 1.5;">{render_message_content(msg_content, msg_role)}</div>
                    </div>
                '''

            # 轮次号只在用户消息变化时显示
            round_display = round_num if round_num != last_round else ""
            last_round = round_num

            rows.append(f'''
                <tr class="model-row">
                    <td style="width: 50px; vertical-align: middle; font-weight: 600; color: #666;">{round_display}</td>
                    <td style="width: 140px;">{timestamp[11:23]}</td>
                    <td style="width: 80px;"><span style="padding: 4px 8px; border-radius: 4px; background: #e0f2f1; color: #00796b; font-weight: 600;">🤖 Model</span></td>
                    <td style="width: 180px;">
                        <div style="font-size: 11px; line-height: 1.6;">
                            <div><span style="color: #666;">代理:</span> <span style="font-family: monospace; color: #007bff;">{proxy_url_display}</span></div>
                            <div><span style="color: #666;">原始:</span> <span style="font-family: monospace; color: #0056b3;">{original_url_display}</span></div>
                            <div><span style="color: #666;">模型:</span> <span style="color: #333;">{model_display}</span></div>
                        </div>
                    </td>
                    <td>
                        <div style="margin-bottom: 10px;">
                            <div style="font-size: 12px; color: #666; font-weight: 600; margin-bottom: 6px;">📥 模型输入 ({len(input_messages)} 条消息)</div>
                            <div style="font-size: 11px; white-space: pre-wrap; word-break: break-word; line-height: 1.5; background: #fafafa; padding: 8px; border-radius: 4px; max-height: 600px; overflow-y: auto;">{input_html}</div>
                        </div>
                        <div style="border-top: 1px solid #eee; padding-top: 8px;">
                            <div style="font-size: 12px; color: #666; font-weight: 600; margin-bottom: 6px;">📤 模型输出</div>
                            <div style="white-space: pre-wrap; max-height: 500px; overflow-y: auto; font-size: 13px;">{escape_html(model_output)}</div>
                        </div>
                    </td>
                    <td style="width: 100px; vertical-align: middle; text-align: center;">
                        <span class="tokens">{prompt_tokens}/{completion_tokens}</span>
                    </td>
                    <td style="width: 70px; vertical-align: middle; text-align: center;" class="interval">{interval}</td>
                </tr>
            ''')

        html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>对话时间轴 - {conv_id}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; min-height: 100vh; }}
        .container {{ max-width: 1800px; margin: 0 auto; }}
        h1 {{ color: white; margin-bottom: 10px; text-shadow: 2px 2px 4px rgba(0,0,0,0.2); }}
        .breadcrumb {{ margin-bottom: 20px; }}
        .breadcrumb a {{ color: rgba(255,255,255,0.9); text-decoration: none; }}
        .breadcrumb a:hover {{ text-decoration: underline; }}
        .header-card {{ background: white; padding: 20px; border-radius: 12px; margin-bottom: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.15); }}
        .header-info {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }}
        .info-item {{ }}
        .info-label {{ color: #666; font-size: 12px; margin-bottom: 5px; }}
        .info-value {{ font-size: 16px; color: #333; }}
        table {{ width: 100%; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.15); }}
        th, td {{ padding: 12px 15px; text-align: left; border-bottom: 1px solid #eee; vertical-align: top; }}
        th {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); font-weight: 600; color: white; white-space: nowrap; }}
        tr:hover {{ background: #f8f9fa; }}
        .user-row {{ background: rgba(227, 242, 253, 0.3); }}
        .tool-row {{ background: rgba(243, 229, 245, 0.3); }}
        .model-row {{ background: rgba(224, 242, 241, 0.3); }}
        .tokens {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 6px 12px; border-radius: 12px; font-size: 12px; color: white; font-weight: 600; display: inline-block; min-width: 60px; text-align: center; }}
        .interval {{ background: #e8eaf6; padding: 4px 8px; border-radius: 8px; font-size: 12px; color: #3f51b5; font-weight: 600; display: inline-block; min-width: 40px; text-align: center; }}
        .legend {{ display: flex; gap: 15px; margin-bottom: 15px; flex-wrap: wrap; }}
        .legend-item {{ display: flex; align-items: center; gap: 5px; font-size: 13px; color: white; }}
        .legend-color {{ width: 16px; height: 16px; border-radius: 4px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="breadcrumb">
            <a href="/">← 返回首页</a>
        </div>

        <div class="legend">
            <div class="legend-item"><div class="legend-color" style="background: #e3f2fd;"></div>👤 User - 真正的用户输入</div>
            <div class="legend-item"><div class="legend-color" style="background: #e8f5e9;"></div>🤖 Assistant - 机器人输出</div>
            <div class="legend-item"><div class="legend-color" style="background: #f3e5f5;"></div>🔧 工具 - 工具调用和响应</div>
            <div class="legend-item"><div class="legend-color" style="background: #e0f2f1;"></div>🤖 模型 - 模型调用（输入 + 输出）</div>
        </div>

        <h1>📋 对话时间轴</h1>

        <div class="header-card">
            <div style="margin-bottom: 15px;">
                <span style="color: #666; font-size: 14px;">会话 ID:</span>
                <span style="font-family: monospace; color: #007bff;">{conv_id}</span>
            </div>
            <div class="header-info">
                <div class="info-item">
                    <div class="info-label">用户 ID</div>
                    <div class="info-value">{user_id}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">事件数</div>
                    <div class="info-value">{len(timeline_events)}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">开始时间</div>
                    <div class="info-value">{index_data.get('started_at', '')[:19]}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">最后更新</div>
                    <div class="info-value">{index_data.get('last_updated', '')[:19]}</div>
                </div>
            </div>
        </div>

        <table>
            <thead>
                <tr>
                    <th style="width: 50px;">序号</th>
                    <th style="width: 140px;">时间</th>
                    <th style="width: 100px;">角色</th>
                    <th style="width: 180px;">模型信息</th>
                    <th>输入 / 输出</th>
                    <th style="width: 100px;">Token(I/O)</th>
                    <th style="width: 70px;">间隔</th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows)}
            </tbody>
        </table>
    </div>
</body>
</html>'''

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def get_proxy_log(self, port):
        """获取代理日志"""
        logs = proxy_logs.get(port, [])
        self.send_json({
            "success": True,
            "log": "\n".join(logs[-LOG_MAX_LINES:]),
            "port": port
        })

    def get_proxy_status(self):
        """获取代理状态 - 所有已配置端口"""
        status = {}

        # 从配置文件读取已配置的端口
        config_file = BASE_DIR / "proxy_config.json"
        configured_ports = []
        if config_file.exists():
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
                model_port_mapping = config.get("model_port_mapping", {})
                configured_ports = list(set(model_port_mapping.values()))
            except:
                pass

        # 默认端口
        if not configured_ports:
            configured_ports = [8888, 8889]

        # 检查所有已配置端口的状态
        for port in configured_ports:
            pid = proxy_processes.get(port)
            # 优先检查是否在进程字典中且正在运行
            if pid and pid.poll() is None:
                status[str(port)] = {"running": True, "pid": pid.pid}
            else:
                # 进程不在字典中，检查端口是否被占用（可能是外部启动的进程）
                port_in_use = is_port_in_use(port)
                if port_in_use:
                    status[str(port)] = {"running": True, "pid": None, "external": True}
                else:
                    status[str(port)] = {"running": False, "pid": None}
                    if port in proxy_processes:
                        del proxy_processes[port]

        self.send_json({"success": True, "status": status, "ports": configured_ports})

    def get_config(self):
        """获取配置文件"""
        config_file = BASE_DIR / "proxy_config.json"
        if config_file.exists():
            with open(config_file, "r", encoding="utf-8") as f:
                self.send_json({"success": True, "config": json.load(f)})
        else:
            self.send_json({"success": False, "error": "Config not found"})

    def save_config(self, config):
        """保存配置文件"""
        config_file = BASE_DIR / "proxy_config.json"
        try:
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            # 初始化已配置端口的日志数组
            model_port_mapping = config.get("model_port_mapping", {})
            ports = list(set(model_port_mapping.values()))
            for port in ports:
                if port not in proxy_logs:
                    proxy_logs[port] = []

            self.send_json({"success": True, "ports": ports})
        except Exception as e:
            self.send_json({"success": False, "error": str(e)})

    def get_openclaw_models(self):
        """从 openclaw.json 读取所有模型配置，过滤掉本地转发的模型"""
        openclaw_config = Path.home() / ".openclaw" / "openclaw.json"
        if not openclaw_config.exists():
            self.send_json({"success": False, "error": "openclaw.json not found"})
            return

        try:
            with open(openclaw_config, "r", encoding="utf-8") as f:
                config = json.load(f)

            models = {}
            providers = config.get("models", {}).get("providers", {})

            for provider_name, provider_config in providers.items():
                base_url = provider_config.get("baseUrl", "")
                for model in provider_config.get("models", []):
                    model_id = model.get("id", "")
                    model_name = model.get("name", model_id)

                    # 过滤掉本地转发的模型（名称中包含"本地转发"）
                    if "本地转发" in model_name:
                        continue

                    model_key = f"{provider_name}/{model_id}"
                    models[model_key] = {
                        "url": base_url,
                        "name": model_name,
                        "provider": provider_name,
                        "model_id": model_id
                    }

            self.send_json({"success": True, "models": models})
        except Exception as e:
            self.send_json({"success": False, "error": str(e)})

    def sync_to_openclaw_post(self, params):
        """同步代理配置到 openclaw.json 并重启 gateway"""
        try:
            # 读取当前 proxy_config.json
            config_file = BASE_DIR / "proxy_config.json"
            with open(config_file, "r", encoding="utf-8") as f:
                proxy_config = json.load(f)

            model_port_mapping = proxy_config.get("model_port_mapping", {})

            # 读取 openclaw.json
            openclaw_config_path = Path.home() / ".openclaw" / "openclaw.json"
            with open(openclaw_config_path, "r", encoding="utf-8") as f:
                openclaw_config = json.load(f)

            # 获取当前所有模型信息（包括被过滤的）
            all_providers = openclaw_config.get("models", {}).get("providers", {})
            all_models = {}
            for provider_name, provider_config in all_providers.items():
                base_url = provider_config.get("baseUrl", "")
                for model in provider_config.get("models", []):
                    model_id = model.get("id", "")
                    model_name = model.get("name", model_id)
                    model_key = f"{provider_name}/{model_id}"
                    all_models[model_key] = {
                        "url": base_url,
                        "name": model_name,
                        "provider": provider_name,
                        "model_id": model_id
                    }

            # 反转映射：port -> model_key
            port_to_model = {v: k for k, v in model_port_mapping.items()}

            # 为每个端口生成 provider 配置
            for port_str, model_key in port_to_model.items():
                port = int(port_str)
                provider_name = f"vllm-{port}"

                # 获取模型信息
                model_info = all_models.get(model_key)

                if model_info:
                    openclaw_config["models"]["providers"][provider_name] = {
                        "baseUrl": f"http://localhost:{port}/v1",
                        "apiKey": "not-needed",
                        "api": "openai-completions",
                        "models": [{
                            "id": model_info["model_id"],
                            "name": f"{model_info['name']}（本地转发 {port}）",
                            "api": "openai-completions"
                        }]
                    }

            # 写回 openclaw.json
            with open(openclaw_config_path, "w", encoding="utf-8") as f:
                json.dump(openclaw_config, f, indent=2, ensure_ascii=False)

            # 重启 gateway
            restart_result = self.restart_gateway()

            self.send_json({
                "success": True,
                "message": f"已同步 {len(port_to_model)} 个代理配置到 openclaw.json",
                "restart": restart_result
            })
        except Exception as e:
            self.send_json({"success": False, "error": str(e)})

    def restart_gateway(self):
        """重启 gateway"""
        try:
            # 查找并停止 gateway 进程
            subprocess.run("pkill -f 'openclaw.*gateway' || true", shell=True)
            time.sleep(1)
            return {"success": True, "message": "gateway 已重启"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def start_proxy(self, port, config_file_name):
        """启动代理服务"""
        global proxy_processes, proxy_logs

        # 检查是否已在进程中且正在运行
        if port in proxy_processes and proxy_processes[port].poll() is None:
            self.send_json({"success": False, "error": f"Proxy already running on port {port}"})
            return

        # 检查端口是否被外部进程占用
        if is_port_in_use(port):
            # 先停止外部进程
            try:
                subprocess.run(f"pkill -f 'model_proxy.*{port}'", shell=True, timeout=5)
                time.sleep(0.5)
            except:
                pass

        try:
            # 查找 model_proxy.py
            proxy_script = BASE_DIR.parent / "model_proxy.py"
            if not proxy_script.exists():
                proxy_script = BASE_DIR / "model_proxy.py"

            cmd = [
                "/home/zhangyanbo/anaconda3/envs/model_proxy/bin/python",
                "-u",
                str(proxy_script),
                "--host", "0.0.0.0",
                "--port", str(port),
                "--config", str(BASE_DIR / config_file_name)
            ]

            proc = subprocess.Popen(
                cmd,
                cwd=str(BASE_DIR),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            proxy_processes[port] = proc
            proxy_logs[port] = []

            def read_logs():
                try:
                    for line in iter(proc.stdout.readline, ''):
                        if line:
                            line = line.strip()
                            proxy_logs[port].append(line)
                            if len(proxy_logs[port]) > LOG_MAX_LINES:
                                proxy_logs[port].pop(0)
                            print(f"[{port}] {line}")
                except:
                    pass

            thread = threading.Thread(target=read_logs, daemon=True)
            thread.start()

            self.send_json({
                "success": True,
                "message": f"Proxy started on port {port}",
                "pid": proc.pid
            })
        except Exception as e:
            self.send_json({"success": False, "error": str(e)})

    def stop_proxy(self, port):
        """停止代理服务"""
        global proxy_processes

        proc = proxy_processes.get(port)
        if proc is None:
            try:
                subprocess.run(f"pkill -f 'model_proxy.*{port}'", shell=True)
                self.send_json({"success": True, "message": f"Proxy stopped on port {port}"})
            except Exception as e:
                self.send_json({"success": False, "error": str(e)})
            return

        try:
            proc.terminate()
            proc.wait(timeout=5)
            del proxy_processes[port]
            self.send_json({"success": True, "message": f"Proxy stopped on port {port}"})
        except subprocess.TimeoutExpired:
            proc.kill()
            del proxy_processes[port]
            self.send_json({"success": True, "message": f"Proxy killed on port {port}"})
        except Exception as e:
            self.send_json({"success": False, "error": str(e)})

    def log_message(self, format, *args):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {args[0]}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="模型日志查看器")
    parser.add_argument("--port", type=int, default=9001, help="监听端口")
    parser.add_argument("--host", default="0.0.0.0", help="监听地址")
    args = parser.parse_args()

    server = ThreadedHTTPServer((args.host, args.port), LogViewerHandler)

    print("=" * 60)
    print("模型日志查看器")
    print("=" * 60)
    print(f"访问地址：http://{args.host}:{args.port}")
    print(f"日志目录：{LOGS_DIR.absolute()}")
    print(f"配置文件：{BASE_DIR / 'proxy_config.json'}")
    print("")
    print("功能:")
    print("  - 模型配置与代理端口自动映射")
    print("  - 启动/停止代理服务（实时日志）")
    print("  - 查看历史会话")
    print("  - 同步配置到 openclaw.json")
    print("=" * 60)

    def signal_handler(sig, frame):
        print("\n正在停止所有代理服务...")
        for port, proc in proxy_processes.items():
            if proc.poll() is None:
                proc.terminate()
        server.shutdown()
        print("已退出")
        exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    server.serve_forever()


if __name__ == "__main__":
    main()
