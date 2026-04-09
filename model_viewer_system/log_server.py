#!/usr/bin/env python3
"""
日志查看器 Web 服务器 + 代理控制
支持在 Web 界面启动/停止代理服务，实时查看日志
"""

import json
import subprocess
import threading
import signal
import os
from pathlib import Path
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
import urllib.parse
import time
from socketserver import ThreadingMixIn

LOGS_DIR = Path("/code/project/deploy_model/logs")
BASE_DIR = Path("/code/project/deploy_model")

# 全局状态
proxy_processes = {}
proxy_logs = {8888: [], 9999: []}
LOG_MAX_LINES = 500


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


class LogViewerHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)

        if parsed.path == "/":
            self.send_file("log_viewer.html")
        elif parsed.path.startswith("/api/logs/conversations"):
            self.get_conversations(query.get("date", [datetime.now().strftime("%Y-%m-%d")])[0])
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
        else:
            super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        content_length = int(self.headers.get('Content-Length', 0))
        body = json.loads(self.rfile.read(content_length).decode()) if content_length else {}

        if parsed.path == "/api/proxy/start":
            self.start_proxy(body.get("port", 8888), body.get("config", "proxy_config.json"))
        elif parsed.path == "/api/proxy/stop":
            self.stop_proxy(body.get("port", 8888))
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

    def get_detail(self, date, conv_id):
        """获取会话详情"""
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

    def get_proxy_log(self, port):
        """获取代理日志"""
        logs = proxy_logs.get(port, [])
        self.send_json({
            "success": True,
            "log": "\n".join(logs[-LOG_MAX_LINES:]),
            "port": port
        })

    def get_proxy_status(self):
        """获取代理状态"""
        status = {}
        for port in [8888, 9999]:
            pid = proxy_processes.get(port)
            if pid and pid.poll() is None:
                status[str(port)] = {"running": True, "pid": pid.pid}
            else:
                status[str(port)] = {"running": False, "pid": None}
                if port in proxy_processes:
                    del proxy_processes[port]
        self.send_json({"success": True, "status": status})

    def start_proxy(self, port, config):
        """启动代理服务（不后台，实时捕获日志）"""
        global proxy_processes, proxy_logs

        if port in proxy_processes and proxy_processes[port].poll() is None:
            self.send_json({"success": False, "error": f"Proxy already running on port {port}"})
            return

        try:
            cmd = [
                "/root/anaconda3/envs/vllm/bin/python",
                "-u",
                str(BASE_DIR / "vllm_proxy.py"),
                "--host", "0.0.0.0",
                "--port", str(port),
                "--config", str(BASE_DIR / config)
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

            # 启动日志读取线程
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
            # 尝试通过 pkill 停止
            try:
                subprocess.run(f"pkill -f 'vllm_proxy.*{port}'", shell=True)
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
    port = 9001
    server = ThreadedHTTPServer(("0.0.0.0", port), LogViewerHandler)

    print("=" * 60)
    print("日志查看器启动")
    print("=" * 60)
    print(f"访问地址：http://localhost:{port}")
    print(f"日志目录：{LOGS_DIR.absolute()}")
    print("")
    print("功能:")
    print("  - 选择代理端口 (8888/9999)")
    print("  - 启动/停止代理服务（实时日志）")
    print("  - 查看历史会话")
    print("=" * 60)

    def signal_handler(sig, frame):
        print("\n正在停止所有代理服务...")
        for port, proc in proxy_processes.items():
            if proc.poll() is None:
                proc.terminate()
        print("已退出")
        exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    server.serve_forever()


if __name__ == "__main__":
    main()
