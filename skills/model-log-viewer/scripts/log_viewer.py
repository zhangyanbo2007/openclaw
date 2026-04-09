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
    def __init__(self, logs_dir: str = "/code/project/deploy_model/logs"):
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


def render_detail_page(date: str, conv_id: str, data: dict) -> str:
    """渲染详情页 HTML"""
    requests = data.get("requests", [])

    rows = []
    prev_time = None
    for i, req in enumerate(requests, 1):
        timestamp = req["timestamp"]
        messages = req["request"].get("messages", [])
        response = req["response"]
        usage = response.get("usage", {})
        endpoint = req.get("endpoint", "")

        if prev_time:
            curr_dt = datetime.fromisoformat(timestamp)
            prev_dt = datetime.fromisoformat(prev_time)
            interval = (curr_dt - prev_dt).total_seconds()
            interval_str = f"{interval:.1f}s"
        else:
            interval_str = "-"
        prev_time = timestamp

        last_msg = messages[-1] if messages else {}
        role = last_msg.get("role", "unknown")
        content = last_msg.get("content", "")

        if isinstance(content, list):
            content_parts = []
            for item in content:
                if isinstance(item, dict) and 'text' in item:
                    content_parts.append(item['text'][:200])
            content = " ".join(content_parts)
        elif not isinstance(content, str):
            content = str(content)

        resp_content = response.get("content", "")
        if not isinstance(resp_content, str):
            resp_content = str(resp_content)

        tokens = f"{usage.get('prompt_tokens', 0)}/{usage.get('completion_tokens', 0)}/{usage.get('total_tokens', 0)}"

        content_escaped = content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
        resp_content_escaped = resp_content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

        rows.append(f'''
            <tr>
                <td>{i}</td>
                <td>{timestamp[11:23]}</td>
                <td>{role}</td>
                <td><span class="endpoint">{endpoint}</span></td>
                <td>
                    <details>
                        <summary class="content-summary">{content_escaped[:100]}...</summary>
                        <div class="detail-content">{content_escaped}</div>
                    </details>
                </td>
                <td>
                    <details>
                        <summary class="content-summary">{resp_content_escaped[:100] if resp_content_escaped else '...'}</summary>
                        <div class="detail-content">{resp_content_escaped}</div>
                    </details>
                </td>
                <td><span class="tokens">{tokens}</span></td>
                <td class="interval">{interval_str}</td>
            </tr>
        ''')

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>对话详情 - {conv_id}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; padding: 20px; }}
        .container {{ max-width: 1600px; margin: 0 auto; }}
        h1 {{ color: #333; margin-bottom: 10px; }}
        .breadcrumb {{ margin-bottom: 20px; }}
        .breadcrumb a {{ color: #007bff; text-decoration: none; }}
        .breadcrumb a:hover {{ text-decoration: underline; }}
        .header-card {{ background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .header-info {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }}
        .info-item {{ }}
        .info-label {{ color: #666; font-size: 12px; margin-bottom: 5px; }}
        .info-value {{ font-size: 16px; color: #333; }}
        table {{ width: 100%; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        th, td {{ padding: 12px 15px; text-align: left; border-bottom: 1px solid #eee; vertical-align: top; }}
        th {{ background: #f8f9fa; font-weight: 600; color: #333; white-space: nowrap; }}
        tr:hover {{ background: #f8f9fa; }}
        .endpoint {{ font-family: monospace; font-size: 11px; background: #e7f3ff; padding: 2px 6px; border-radius: 4px; color: #007bff; }}
        .tokens {{ background: #e7f3ff; padding: 2px 8px; border-radius: 12px; font-size: 12px; color: #007bff; }}
        .interval {{ color: #666; font-size: 12px; }}
        details {{ }}
        summary {{ cursor: pointer; color: #007bff; }}
        summary:hover {{ color: #0056b3; }}
        .content-summary {{ font-size: 13px; color: #333; }}
        .detail-content {{ margin-top: 10px; padding: 10px; background: #f8f9fa; border-radius: 4px; font-size: 12px; white-space: pre-wrap; word-break: break-word; max-height: 400px; overflow-y: auto; }}
        .back-btn {{ padding: 8px 20px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 14px; text-decoration: none; display: inline-block; }}
        .back-btn:hover {{ background: #0056b3; }}
        .export-btn {{ padding: 8px 20px; background: #28a745; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 14px; float: right; }}
        .export-btn:hover {{ background: #1e7e34; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="breadcrumb">
            <a href="/">← 返回首页</a>
            <button class="export-btn" onclick="exportDetail()">导出此对话 Excel</button>
        </div>

        <h1>📋 对话详情</h1>

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
                    <div class="info-label">请求数</div>
                    <div class="info-value">{len(requests)}</div>
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
                    <th>轮次</th>
                    <th>时间</th>
                    <th>角色</th>
                    <th>端点</th>
                    <th>请求内容</th>
                    <th>响应内容</th>
                    <th>Token</th>
                    <th>间隔</th>
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
    """首页处理 - 返回模型日志查看器主页面"""
    # 读取 index.html 文件
    base_dir = Path(__file__).parent
    index_file = base_dir / "index.html"
    if index_file.exists():
        with open(index_file, "r", encoding="utf-8") as f:
            html = f.read()
        return web.Response(text=html, content_type="text/html")
    return web.Response(text="index.html not found", status=404)


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