#!/usr/bin/env python3
"""
日志查看器 Web UI - 支持按日期查看对话日志、Excel 导出
"""

import json
import re
from pathlib import Path
from datetime import datetime
from aiohttp import web
import argparse
from io import BytesIO


class LogDataManager:
    def __init__(self, logs_dir: str = "/home/zhangyanbo/.openclaw/model-logs"):
        self.logs_dir = Path(logs_dir)

    def get_available_dates(self) -> list:
        """获取所有有日志的日期"""
        dates = []
        if self.logs_dir.exists():
            for d in sorted(self.logs_dir.glob("*")):
                if d.is_dir() and re.match(r"\d{4}-\d{2}-\d{2}", d.name):
                    dates.append(d.name)
        return dates

    def extract_user_id(self, messages: list) -> str:
        """从消息中提取用户 ID"""
        for msg in messages:
            if isinstance(msg, dict):
                content = msg.get('content', '')
                if isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict) and 'text' in item:
                            text_content = item.get('text', '')
                            match = re.search(r'(?:sender_id|sender|id|label)"?:\s*"?(ou_[a-z0-9]+)"?', text_content)
                            if match:
                                return match.group(1)
                            match = re.search(r'ou_[a-z0-9]+', text_content)
                            if match:
                                return match.group()
                elif isinstance(content, str):
                    match = re.search(r'(?:sender_id|sender|id|label)"?:\s*"?(ou_[a-z0-9]+)"?', content)
                    if match:
                        return match.group(1)
                    match = re.search(r'ou_[a-z0-9]+', content)
                    if match:
                        return match.group()
        return "unknown"

    def get_conversations(self, date: str) -> list:
        """获取指定日期的所有对话"""
        date_dir = self.logs_dir / date
        if not date_dir.exists():
            return []

        conversations = []
        for conv_folder in sorted(date_dir.glob("conv_*")):
            if not conv_folder.is_dir():
                continue

            index_file = conv_folder / "index.json"
            if not index_file.exists():
                continue

            with open(index_file, "r", encoding="utf-8") as f:
                index = json.load(f)

            requests = []
            for log_file in sorted(conv_folder.glob("*.json")):
                if log_file.name == "index.json":
                    continue
                with open(log_file, "r", encoding="utf-8") as f:
                    record = json.load(f)
                    requests.append(record)

            user_id = index.get("user_id", "unknown")
            if user_id == "unknown" and requests:
                messages = requests[0]["request"].get("messages", [])
                user_id = self.extract_user_id(messages)

            total_tokens = sum(
                r["response"].get("usage", {}).get("total_tokens", 0)
                for r in requests
            )

            conversations.append({
                "conversation_id": conv_folder.name,
                "user_id": user_id,
                "request_count": index.get("request_count", len(requests)),
                "started_at": index.get("started_at", "")[:19],
                "last_updated": index.get("last_updated", "")[:19],
                "total_tokens": total_tokens,
                "requests": sorted(requests, key=lambda x: x["timestamp"])
            })

        return conversations

    def get_conversation_detail(self, date: str, conv_id: str) -> dict:
        """获取单个对话的详细信息"""
        date_dir = self.logs_dir / date
        conv_folder = date_dir / conv_id

        if not conv_folder.exists():
            return None

        index_file = conv_folder / "index.json"
        if not index_file.exists():
            return None

        with open(index_file, "r", encoding="utf-8") as f:
            index = json.load(f)

        requests = []
        for log_file in sorted(conv_folder.glob("*.json")):
            if log_file.name == "index.json":
                continue
            with open(log_file, "r", encoding="utf-8") as f:
                record = json.load(f)
                requests.append(record)

        return {
            "index": index,
            "requests": sorted(requests, key=lambda x: x["timestamp"])
        }

    def get_all_requests_for_date(self, date: str, time_start: str = "00:00", time_end: str = "23:59") -> list:
        """获取指定日期的所有请求记录（用于 Excel 导出）"""
        conversations = self.get_conversations(date)
        all_requests = []

        for conv in conversations:
            conv_time = conv["started_at"][11:16] if conv["started_at"] else ""
            if time_start <= conv_time <= time_end:
                for req in conv["requests"]:
                    all_requests.append({
                        "conversation_id": conv["conversation_id"],
                        "user_id": conv["user_id"],
                        **req
                    })

        return all_requests


def try_import_openpyxl():
    """尝试导入 openpyxl，如果不存在则返回 None"""
    try:
        import openpyxl
        return openpyxl
    except ImportError:
        return None


def export_to_excel(requests: list) -> BytesIO:
    """将请求数据导出为 Excel（完整数据，不压缩）"""
    openpyxl = try_import_openpyxl()
    if openpyxl is None:
        return None

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "对话日志"

    # 设置表头
    headers = [
        "序号", "时间戳", "日期", "时间", "会话 ID", "用户 ID", "客户端 IP", "客户端",
        "端点", "模型", "角色", "请求内容 (完整)", "响应内容 (完整)", "推理过程",
        "Prompt Tokens", "Completion Tokens", "Total Tokens", "Finish Reason",
        "是否流式", "Tool Calls"
    ]

    ws.append(headers)

    # 设置列宽
    for i, col_letter in enumerate(['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T']):
        ws.column_dimensions[col_letter].width = 20
    ws.column_dimensions['L'].width = 80  # 请求内容
    ws.column_dimensions['M'].width = 80  # 响应内容
    ws.column_dimensions['N'].width = 50  # 推理过程

    # 填充数据
    for idx, req in enumerate(requests, 1):
        timestamp = req.get("timestamp", "")
        date = timestamp[:10] if timestamp else ""
        time = timestamp[11:19] if timestamp else ""

        request_data = req.get("request", {})
        response_data = req.get("response", {})

        messages = request_data.get("messages", [])
        last_msg = messages[-1] if messages else {}
        role = last_msg.get("role", "")

        # 完整的请求内容（所有消息）
        full_request_content = json.dumps(messages, ensure_ascii=False, indent=2)

        # 完整的响应内容
        content = response_data.get("content", "")
        reasoning = response_data.get("reasoning", "")
        tool_calls = response_data.get("tool_calls", [])
        usage = response_data.get("usage", {})

        row = [
            idx,
            timestamp,
            date,
            time,
            req.get("conversation_id", ""),
            req.get("user_id", ""),
            req.get("client_ip", ""),
            req.get("client", ""),
            req.get("endpoint", ""),
            request_data.get("model", ""),
            role,
            full_request_content,  # 完整请求内容
            content,  # 完整响应内容
            reasoning,  # 推理过程
            usage.get("prompt_tokens", 0),
            usage.get("completion_tokens", 0),
            usage.get("total_tokens", 0),
            response_data.get("finish_reason", ""),
            str(req.get("is_stream", False)),
            json.dumps(tool_calls, ensure_ascii=False) if tool_calls else ""
        ]

        ws.append(row)

    # 保存到内存
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output


# 全局数据管理器
data_manager = LogDataManager()


def render_index_page(dates: list) -> str:
    """渲染首页 HTML - 现代化设计"""
    date_options = "".join(f'<option value="{d}">{d}</option>' for d in dates)

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>日志查看器</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            min-height: 100vh;
        }}
        .container {{ max-width: 1600px; margin: 0 auto; }}
        h1 {{ color: white; margin-bottom: 20px; text-shadow: 2px 2px 4px rgba(0,0,0,0.2); }}
        .controls {{
            background: white;
            padding: 20px;
            border-radius: 12px;
            margin-bottom: 20px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.15);
            display: flex;
            flex-wrap: wrap;
            gap: 15px;
            align-items: center;
        }}
        .controls label {{ color: #555; font-weight: 500; font-size: 14px; }}
        .controls select, .controls input {{
            padding: 10px 14px;
            border: 1px solid #ddd;
            border-radius: 8px;
            font-size: 14px;
            background: #fafafa;
            transition: all 0.2s;
        }}
        .controls select:focus, .controls input:focus {{
            outline: none;
            border-color: #667eea;
            background: white;
        }}
        .controls button {{
            padding: 10px 24px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            transition: all 0.2s;
        }}
        .btn-primary {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }}
        .btn-primary:hover {{ transform: translateY(-2px); box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4); }}
        .btn-success {{
            background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
            color: white;
        }}
        .btn-success:hover {{ transform: translateY(-2px); box-shadow: 0 4px 12px rgba(17, 153, 142, 0.4); }}
        table {{
            width: 100%;
            background: white;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 15px rgba(0,0,0,0.15);
        }}
        th, td {{ padding: 14px 16px; text-align: left; border-bottom: 1px solid #eee; }}
        th {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            font-weight: 600;
            color: white;
        }}
        tr:hover {{ background: #f8f9fa; }}
        .user-id {{ font-family: monospace; font-size: 12px; color: #666; background: #f0f0f0; padding: 3px 8px; border-radius: 4px; }}
        .conv-id {{ font-family: monospace; font-size: 13px; color: #667eea; font-weight: 500; }}
        .time {{ color: #666; font-size: 13px; }}
        .tokens {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            color: white;
            font-weight: 600;
        }}
        .view-btn {{
            padding: 6px 16px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 13px;
            font-weight: 500;
            transition: all 0.2s;
        }}
        .view-btn:hover {{ transform: translateY(-2px); box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4); }}
        .no-data {{ text-align: center; padding: 60px; color: rgba(255,255,255,0.8); font-size: 16px; }}
        .stats {{ display: flex; gap: 15px; margin-bottom: 20px; flex-wrap: wrap; }}
        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 12px;
            flex: 1;
            min-width: 180px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.15);
            transition: all 0.2s;
        }}
        .stat-card:hover {{ transform: translateY(-4px); box-shadow: 0 8px 25px rgba(0,0,0,0.2); }}
        .stat-value {{
            font-size: 28px;
            font-weight: bold;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}
        .stat-label {{ color: #666; font-size: 13px; margin-top: 6px; font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px; }}
        @media (max-width: 768px) {{
            .controls {{ flex-direction: column; align-items: stretch; }}
            .controls select, .controls input, .controls button {{ width: 100%; }}
            .stats {{ flex-direction: column; }}
            table {{ font-size: 13px; }}
            th, td {{ padding: 10px 12px; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📋 日志查看器</h1>

        <div class="controls">
            <label for="dateSelect">选择日期:</label>
            <select id="dateSelect" style="flex: 1; min-width: 150px;">{date_options}</select>

            <label for="timeStart">开始时间:</label>
            <input type="time" id="timeStart" value="00:00" style="width: 130px;">

            <label for="timeEnd">结束时间:</label>
            <input type="time" id="timeEnd" value="23:59" style="width: 130px;">

            <button class="btn-primary" onclick="loadConversations()">加载日志</button>
            <button class="btn-success" onclick="exportExcel()">导出 Excel</button>
        </div>

        <div id="statsArea" class="stats" style="display:none;">
            <div class="stat-card">
                <div class="stat-value" id="statConversations">0</div>
                <div class="stat-label">会话数</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="statRequests">0</div>
                <div class="stat-label">总请求数</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="statUsers">0</div>
                <div class="stat-label">用户数</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="statTokens">0</div>
                <div class="stat-label">总 Token</div>
            </div>
        </div>

        <table id="conversationsTable" style="display:none;">
            <thead>
                <tr>
                    <th>会话 ID</th>
                    <th>用户 ID</th>
                    <th>请求数</th>
                    <th>开始时间</th>
                    <th>最后更新</th>
                    <th>总 Token</th>
                    <th>操作</th>
                </tr>
            </thead>
            <tbody id="conversationsBody"></tbody>
        </table>

        <div id="noData" class="no-data">请选择日期并点击"加载日志"</div>
    </div>

    <script>
        let currentConversations = [];
        let currentRequests = [];

        async function loadConversations() {{
            const date = document.getElementById('dateSelect').value;
            const timeStart = document.getElementById('timeStart').value;
            const timeEnd = document.getElementById('timeEnd').value;

            const url = `/api/conversations?date=${{date}}&start=${{timeStart}}&end=${{timeEnd}}`;
            const resp = await fetch(url);
            const data = await resp.json();

            currentConversations = data;

            const excelUrl = `/api/requests?date=${{date}}&start=${{timeStart}}&end=${{timeEnd}}`;
            const excelResp = await fetch(excelUrl);
            currentRequests = await excelResp.json();

            if (data.length === 0) {{
                document.getElementById('noData').style.display = 'block';
                document.getElementById('conversationsTable').style.display = 'none';
                document.getElementById('statsArea').style.display = 'none';
                return;
            }}

            const totalRequests = data.reduce((sum, c) => sum + c.request_count, 0);
            const uniqueUsers = new Set(data.map(c => c.user_id)).size;
            const totalTokens = data.reduce((sum, c) => sum + c.total_tokens, 0);

            document.getElementById('statConversations').textContent = data.length;
            document.getElementById('statRequests').textContent = totalRequests;
            document.getElementById('statUsers').textContent = uniqueUsers;
            document.getElementById('statTokens').textContent = totalTokens;

            document.getElementById('statsArea').style.display = 'flex';
            document.getElementById('noData').style.display = 'none';
            document.getElementById('conversationsTable').style.display = 'table';

            const tbody = document.getElementById('conversationsBody');
            tbody.innerHTML = data.map(c => `
                <tr>
                    <td><span class="conv-id">${{c.conversation_id}}</span></td>
                    <td><span class="user-id">${{c.user_id}}</span></td>
                    <td style="text-align: center;">${{c.request_count}}</td>
                    <td class="time">${{c.started_at}}</td>
                    <td class="time">${{c.last_updated}}</td>
                    <td style="text-align: center;"><span class="tokens">${{c.total_tokens}}</span></td>
                    <td><button class="view-btn" onclick="viewDetail('${{c.conversation_id}}')">查看详情</button></td>
                </tr>
            `).join('');
        }}

        function viewDetail(convId) {{
            const date = document.getElementById('dateSelect').value;
            window.location.href = `/detail?date=${{date}}&conv_id=${{convId}}`;
        }}

        function exportExcel() {{
            const date = document.getElementById('dateSelect').value;
            const timeStart = document.getElementById('timeStart').value;
            const timeEnd = document.getElementById('timeEnd').value;

            if (!date) {{
                alert('请先选择日期');
                return;
            }}

            window.location.href = `/api/export/excel?date=${{date}}&start=${{timeStart}}&end=${{timeEnd}}`;
        }}

        window.onload = function() {{
            const selects = document.getElementById('dateSelect');
            if (selects.options.length > 0) {{
                selects.selectedIndex = selects.options.length - 1;
            }}
        }};
    </script>
</body>
</html>'''
    return html


def render_detail_page(date: str, conv_id: str, data: dict, proxy_config: dict = None, openclaw_config: dict = None) -> str:
    """渲染详情页 HTML - 完整对话时间轴，包含 User/Assistant/工具/模型四种角色"""
    requests = data.get("requests", [])

    # 构建代理模型 URL 映射
    proxy_model_info = {}
    if proxy_config and openclaw_config:
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
                    "model_key": model_key
                }

    # 按时间轴展开所有事件
    # 四类角色：User（真正用户输入）、Assistant（机器人输出）、工具（工具调用 + 响应）、模型（模型调用）
    timeline_events = []
    prev_timestamp = None

    def extract_user_text(content) -> tuple:
        """提取真正的用户消息（带 ou_ ID 或 GMT+8 时间戳的实际问题）"""
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and "text" in item:
                    text = item["text"]
                    # 检查是否包含 ou_ ID（飞书用户标识）
                    has_ou_id = bool(re.search(r"ou_[a-z0-9]+", text))

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

                    # 模式 4: 包含 ou_ ID 的文本，尝试提取第一个有意义的句子
                    if has_ou_id:
                        # 排除系统消息和模板
                        lines = text.split('\n')
                        for line in lines:
                            line = line.strip()
                            if line and len(line) > 3 and not line.startswith('A new session') and not line.startswith('<conversation') and not line.startswith('You are') and not line.startswith('['):
                                # 检查是否包含用户实际问题（问候、提问等）
                                if re.search(r'你好 | 好 | 什么 | 怎么 | 如何 | 为什么 | 能否 | 可以 | 想 | 要|help|what|how|why|can|could', line, re.IGNORECASE):
                                    return (True, line[:500])

                        # 备用：返回包含 ou_ 的文本片段
                        return (True, text[:500])
        elif isinstance(content, str):
            if re.search(r"ou_[a-z0-9]+", content):
                return (True, content[:500])
        return (False, "")

    def escape_html(text: str) -> str:
        """转义 HTML 特殊字符"""
        if not text:
            return ""
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("\n", "<br>")

    def render_message_content(content, role: str = "") -> str:
        """渲染消息内容，处理不同格式"""
        if content is None:
            return ""

        # 处理 content 是列表的情况（多模态消息）
        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, dict):
                    if "text" in item:
                        parts.append(item["text"])
                    elif "image_url" in item:
                        parts.append(f"[Image]")
            content = "\n\n".join(parts)
        elif not isinstance(content, str):
            content = str(content)

        return escape_html(content)

    def get_role_style(role: str) -> dict:
        """获取角色的样式配置"""
        styles = {
            "system": {"color": "#e65100", "bg": "#fff3e0", "label": "⚙️ system", "border": "#ff9800"},
            "user": {"color": "#1565c0", "bg": "#e3f2fd", "label": "👤 user", "border": "#2196f3"},
            "assistant": {"color": "#2e7d32", "bg": "#e8f5e9", "label": "🤖 assistant", "border": "#4caf50"},
            "tool": {"color": "#6a1b9a", "bg": "#f3e5f5", "label": "🔧 tool", "border": "#9c27b0"},
            "model": {"color": "#00796b", "bg": "#e0f2f1", "label": "🤖 Model", "border": "#009688"},
        }
        return styles.get(role, {"color": "#666", "bg": "#f5f5f5", "label": role, "border": "#999"})

    for req_idx, req in enumerate(requests):
        timestamp = req["timestamp"]
        messages = req["request"].get("messages", [])
        response = req["response"]
        usage = response.get("usage", {})
        endpoint = req.get("endpoint", "")
        request_model = req["request"].get("model", "")

        # 获取模型信息
        model_info = proxy_model_info.get(request_model, {})
        proxy_url = model_info.get("proxy_url", "")
        original_url = model_info.get("original_url", "")
        model_name = model_info.get("model", request_model)

        # 计算时间间隔
        if prev_timestamp:
            curr_dt = datetime.fromisoformat(timestamp)
            prev_dt = datetime.fromisoformat(prev_timestamp)
            interval = (curr_dt - prev_dt).total_seconds()
            interval_str = f"{interval:.1f}s"
        else:
            interval_str = "-"
        prev_timestamp = timestamp

        # 1. 检查并添加真正的用户消息
        for msg in messages:
            if msg.get("role") == "user":
                content = msg.get("content", "")
                is_real_user, user_text = extract_user_text(content)
                if is_real_user:
                    timeline_events.append({
                        "timestamp": timestamp,
                        "role_type": "User",
                        "category": "user",
                        "input": user_text,
                        "output": None,
                        "interval": interval_str,
                        "model_info": None
                    })
                    interval_str = "-"  # 只有第一个事件显示间隔
                    break

        # 2. 检查工具调用（来自响应）
        tool_calls = response.get("tool_calls", [])
        if tool_calls:
            for tc in tool_calls:
                func = tc.get("function", {})
                tool_name = func.get("name", "unknown")
                tool_args = func.get("arguments", "{}")
                timeline_events.append({
                    "timestamp": timestamp,
                    "role_type": "工具",
                    "category": "tool_call",
                    "input": f"工具：{tool_name}\n参数：{tool_args}",
                    "output": None,
                    "interval": interval_str,
                    "model_info": None
                })
                interval_str = "-"

        # 3. 检查工具响应（来自消息中的 tool 角色）
        for msg in messages:
            if msg.get("role") == "tool":
                content = msg.get("content", "")
                # 提取工具名
                tool_match = re.search(r'name:\s*(\w+)', content)
                tool_name = tool_match.group(1) if tool_match else "unknown"
                timeline_events.append({
                    "timestamp": timestamp,
                    "role_type": "工具",
                    "category": "tool_response",
                    "input": f"工具：{tool_name} 的响应",
                    "output": content[:2000],
                    "interval": interval_str,
                    "model_info": None
                })
                interval_str = "-"

        # 4. 添加模型响应（包含完整的输入和输出）
        resp_content = response.get("content") or response.get("reasoning") or ""
        if not isinstance(resp_content, str):
            resp_content = str(resp_content)

        # 模型输入：提取所有消息
        model_input_messages = []
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            model_input_messages.append({"role": role, "content": content})

        timeline_events.append({
            "timestamp": timestamp,
            "role_type": "模型",
            "category": "model_response",
            "input": model_input_messages,
            "output": resp_content,
            "interval": interval_str,
            "model_info": {
                "proxy_url": proxy_url,
                "original_url": original_url,
                "model": model_name,
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0)
            }
        })

    # 构建 HTML 行
    rows = []
    row_num = 0

    for event in timeline_events:
        row_num += 1
        role_type = event["role_type"]
        category = event["category"]
        interval = event["interval"]
        model_info = event.get("model_info")

        # 角色样式
        style = get_role_style(role_type if role_type != "模型" else "model")
        role_color = style["color"]
        role_bg = style["bg"]
        role_label = style["label"]
        role_border = style["border"]

        if category == "user":
            # 用户消息行
            rows.append(f'''
                <tr class="user-row">
                    <td style="width: 50px; vertical-align: middle; font-weight: 600;">{row_num}</td>
                    <td style="width: 140px;">{event["timestamp"][11:23]}</td>
                    <td style="width: 80px;"><span style="padding: 4px 8px; border-radius: 4px; background: {role_bg}; color: {role_color}; font-weight: 600;">{role_label}</span></td>
                    <td style="width: 180px; background: #fafafa;"></td>
                    <td colspan="2"><div style="white-space: pre-wrap; font-size: 13px;">{escape_html(event["input"])}</div></td>
                    <td style="width: 70px;" class="interval">{interval}</td>
                </tr>
            ''')

        elif category in ("tool_call", "tool_response"):
            # 工具调用/响应行
            tool_input = escape_html(event["input"]) if event["input"] else ""
            tool_output = escape_html(event["output"]) if event["output"] else ""

            if category == "tool_call":
                tool_label = "🔧 工具调用"
            else:
                tool_label = "📥 工具响应"

            rows.append(f'''
                <tr class="tool-row">
                    <td style="width: 50px;"></td>
                    <td style="width: 140px;">{event["timestamp"][11:23]}</td>
                    <td style="width: 80px;"><span style="padding: 4px 8px; border-radius: 4px; background: {role_bg}; color: {role_color}; font-weight: 600;">{role_label}</span></td>
                    <td style="width: 180px; background: #fafafa;"></td>
                    <td>
                        <div style="margin-bottom: 8px;">
                            <div style="font-size: 12px; color: #666; font-weight: 600; margin-bottom: 4px;">{tool_label}</div>
                            <div style="font-size: 11px; white-space: pre-wrap; background: #f8f9fa; padding: 8px; border-radius: 4px; border-left: 3px solid {role_border};">{tool_input}</div>
                        </div>
                        {'<div style="border-top: 1px solid #eee; padding-top: 8px;"><div style="font-size: 12px; color: #666; font-weight: 600; margin-bottom: 4px;">输出</div><div style="font-size: 11px; white-space: pre-wrap; max-height: 400px; overflow-y: auto; background: #fafafa; padding: 8px; border-radius: 4px;">' + tool_output + '</div></div>' if tool_output else ''}
                    </td>
                    <td style="width: 100px;"></td>
                    <td style="width: 70px;" class="interval"></td>
                </tr>
            ''')

        elif category == "model_response":
            # 模型响应行
            model_output = escape_html(event["output"]) if event["output"] else ""

            # 构建模型输入的完整显示
            input_messages = event["input"] if isinstance(event["input"], list) else []
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

            proxy_url_display = model_info["proxy_url"] if model_info else "N/A"
            original_url_display = model_info["original_url"] if model_info else "N/A"
            model_display = model_info["model"] if model_info else "N/A"
            prompt_tokens = model_info["prompt_tokens"] if model_info else 0
            completion_tokens = model_info["completion_tokens"] if model_info else 0

            rows.append(f'''
                <tr class="model-row">
                    <td style="width: 50px;"></td>
                    <td style="width: 140px;">{event["timestamp"][11:23]}</td>
                    <td style="width: 80px;"><span style="padding: 4px 8px; border-radius: 4px; background: {role_bg}; color: {role_color}; font-weight: 600;">{role_label}</span></td>
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
                            <div style="white-space: pre-wrap; max-height: 500px; overflow-y: auto; font-size: 13px;">{model_output}</div>
                        </div>
                    </td>
                    <td style="width: 100px;"><span class="tokens">{prompt_tokens}/{completion_tokens}</span></td>
                    <td style="width: 70px;" class="interval"></td>
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
        .tokens {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 4px 10px; border-radius: 12px; font-size: 12px; color: white; font-weight: 600; }}
        .interval {{ color: #666; font-size: 12px; }}
        .legend {{ display: flex; gap: 15px; margin-bottom: 15px; flex-wrap: wrap; }}
        .legend-item {{ display: flex; align-items: center; gap: 5px; font-size: 13px; color: white; }}
        .legend-color {{ width: 16px; height: 16px; border-radius: 4px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="breadcrumb">
            <a href="/">← 返回首页</a>
            <button class="export-btn" onclick="exportDetail()" style="padding: 8px 20px; background: rgba(255,255,255,0.2); color: white; border: 1px solid rgba(255,255,255,0.5); border-radius: 4px; cursor: pointer; font-size: 14px; float: right;">导出此对话 Excel</button>
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
                    <div class="info-value">{data.get('index', {}).get('user_id', 'unknown')}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">事件数</div>
                    <div class="info-value">{len(timeline_events)}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">开始时间</div>
                    <div class="info-value">{data.get('index', {}).get('started_at', '')[:19]}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">最后更新</div>
                    <div class="info-value">{data.get('index', {}).get('last_updated', '')[:19]}</div>
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

    <script>
        function exportDetail() {{
            const date = "{date}";
            const convId = "{conv_id}";
            window.location.href = `/api/export/excel-detail?date=${{date}}&conv_id=${{convId}}`;
        }}
    </script>
</body>
</html>'''
    return html


async def index_handler(request):
    """首页处理"""
    dates = data_manager.get_available_dates()
    html = render_index_page(dates)
    return web.Response(text=html, content_type="text/html")


async def api_conversations_handler(request):
    """API: 获取对话列表"""
    date = request.query.get("date", "")
    time_start = request.query.get("start", "00:00")
    time_end = request.query.get("end", "23:59")

    conversations = data_manager.get_conversations(date)

    filtered = []
    for conv in conversations:
        conv_time = conv["started_at"][11:16] if conv["started_at"] else ""
        if time_start <= conv_time <= time_end:
            filtered.append(conv)

    return web.json_response(filtered)


async def api_requests_handler(request):
    """API: 获取所有请求数据（用于前端处理）"""
    date = request.query.get("date", "")
    time_start = request.query.get("start", "00:00")
    time_end = request.query.get("end", "23:59")

    requests = data_manager.get_all_requests_for_date(date, time_start, time_end)
    return web.json_response(requests)


async def detail_handler(request):
    """详情页处理"""
    date = request.query.get("date", "")
    conv_id = request.query.get("conv_id", "")

    data = data_manager.get_conversation_detail(date, conv_id)
    if data is None:
        return web.Response(text="对话未找到", status=404)

    html = render_detail_page(date, conv_id, data)
    return web.Response(text=html, content_type="text/html")


async def api_detail_handler(request):
    """API: 获取对话详情"""
    date = request.query.get("date", "")
    conv_id = request.query.get("conv_id", "")

    data = data_manager.get_conversation_detail(date, conv_id)
    if data is None:
        return web.json_response({"error": "对话未找到"}, status=404)

    return web.json_response(data)


async def api_export_excel_handler(request):
    """API: 导出 Excel（指定日期的所有数据）"""
    date = request.query.get("date", "")
    time_start = request.query.get("start", "00:00")
    time_end = request.query.get("end", "23:59")

    requests_list = data_manager.get_all_requests_for_date(date, time_start, time_end)

    excel_data = export_to_excel(requests_list)
    if excel_data is None:
        return web.json_response(
            {"error": "openpyxl 未安装，请先运行：pip install openpyxl"},
            status=400
        )

    filename = f"log_{date}_{time_start}_{time_end}.xlsx"

    return web.Response(
        body=excel_data.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


async def api_export_excel_detail_handler(request):
    """API: 导出单个对话的 Excel"""
    date = request.query.get("date", "")
    conv_id = request.query.get("conv_id", "")

    data = data_manager.get_conversation_detail(date, conv_id)
    if data is None:
        return web.Response(text="对话未找到", status=404)

    # 将对话详情转换为请求列表格式
    requests_list = []
    for req in data.get("requests", []):
        requests_list.append({
            "conversation_id": conv_id,
            "user_id": data.get("index", {}).get("user_id", "unknown"),
            **req
        })

    excel_data = export_to_excel(requests_list)
    if excel_data is None:
        return web.json_response(
            {"error": "openpyxl 未安装，请先运行：pip install openpyxl"},
            status=400
        )

    filename = f"conv_{conv_id}_{date}.xlsx"

    return web.Response(
        body=excel_data.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


def create_app():
    app = web.Application()
    app.router.add_get("/", index_handler)
    app.router.add_get("/api/conversations", api_conversations_handler)
    app.router.add_get("/api/requests", api_requests_handler)
    app.router.add_get("/detail", detail_handler)
    app.router.add_get("/api/detail", api_detail_handler)
    app.router.add_get("/api/export/excel", api_export_excel_handler)
    app.router.add_get("/api/export/excel-detail", api_export_excel_detail_handler)
    return app


def main():
    parser = argparse.ArgumentParser(description="日志查看器")
    parser.add_argument("--host", default="0.0.0.0", help="监听地址（0.0.0.0 允许局域网访问）")
    parser.add_argument("--port", type=int, default=9001, help="监听端口")
    args = parser.parse_args()

    app = create_app()
    print(f"日志查看器启动：http://{args.host}:{args.port}")
    print(f"局域网访问地址：http://<你的 IP 地址>:{args.port}")
    web.run_app(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
