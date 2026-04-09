#!/usr/bin/env python3
"""
vLLM 访问日志分析器 - 零延迟方案
通过读取 vLLM 日志文件分析访问模式，不影响请求性能
"""

import re
import json
import time
from datetime import datetime
from pathlib import Path
from collections import defaultdict


class VLLMLogAnalyzer:
    def __init__(self, vllm_log: str = "/tmp/vllm.log", output_dir: str = "/code/project/deploy_model/logs"):
        self.vllm_log = Path(vllm_log)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.today = datetime.now().strftime("%Y-%m-%d")
        self.today_dir = self.output_dir / self.today
        self.today_dir.mkdir(exist_ok=True)

        self.last_pos = 0
        if self.vllm_log.exists():
            self.last_pos = self.vllm_log.stat().st_size

        # 日志模式匹配
        self.request_pattern = re.compile(
            r'INFO:\s+(\d+\.\d+\.\d+\.\d+):(\d+)\s+-\s+"(\w+)\s+(\S+)\s+HTTP/[\d.]+"\s+(\d+)'
        )

        # 按 IP 统计
        self.ip_stats = defaultdict(lambda: {"requests": 0, "first_seen": None, "last_seen": None})

    def parse_line(self, line: str):
        """解析日志行"""
        match = self.request_pattern.search(line)
        if not match:
            return None

        ip, port, method, path, status = match.groups()

        # 只关注 API 请求
        if not path.startswith("/v1/"):
            return None

        return {
            "ip": ip,
            "port": int(port),
            "method": method,
            "path": path,
            "status": int(status),
            "timestamp": datetime.now().isoformat()
        }

    def save_record(self, record: dict):
        """保存记录到文件"""
        ip = record["ip"]
        safe_ip = ip.replace(".", "_")
        ip_file = self.today_dir / f"{safe_ip}.jsonl"

        with open(ip_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

        # 更新统计
        self.ip_stats[ip]["requests"] += 1
        if not self.ip_stats[ip]["first_seen"]:
            self.ip_stats[ip]["first_seen"] = record["timestamp"]
        self.ip_stats[ip]["last_seen"] = record["timestamp"]

    def get_summary(self):
        """获取摘要"""
        summary = {
            "date": self.today,
            "total_requests": sum(s["requests"] for s in self.ip_stats.values()),
            "unique_ips": len(self.ip_stats),
            "visitors": []
        }

        for ip, stats in sorted(self.ip_stats.items(), key=lambda x: x[1]["requests"], reverse=True):
            summary["visitors"].append({
                "ip": ip,
                "requests": stats["requests"],
                "first_seen": stats["first_seen"],
                "last_seen": stats["last_seen"]
            })

        return summary

    def watch(self, interval: float = 1.0):
        """持续监控日志"""
        print(f"开始监控：{self.vllm_log}")
        print(f"输出目录：{self.today_dir}")

        while True:
            try:
                if not self.vllm_log.exists():
                    time.sleep(interval)
                    continue

                current_size = self.vllm_log.stat().st_size
                if current_size < self.last_pos:
                    self.last_pos = 0

                with open(self.vllm_log, "r") as f:
                    f.seek(self.last_pos)
                    for line in f:
                        record = self.parse_line(line)
                        if record:
                            self.save_record(record)
                            print(f"[{record['timestamp']}] {record['ip']} -> {record['path']} ({record['status']})")

                self.last_pos = self.vllm_log.tell()

            except Exception as e:
                print(f"Error: {e}")

            time.sleep(interval)

    def save_summary(self):
        """保存摘要"""
        summary = self.get_summary()
        summary_file = self.today_dir / "summary.json"
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        return summary


def main():
    import argparse
    parser = argparse.ArgumentParser(description="vLLM 访问日志分析器")
    parser.add_argument("--watch", action="store_true", help="持续监控")
    parser.add_argument("--summary", action="store_true", help="显示摘要")
    parser.add_argument("--ip", type=str, help="查看指定 IP 的记录")
    args = parser.parse_args()

    analyzer = VLLMLogAnalyzer()

    if args.watch:
        analyzer.watch()
    elif args.summary:
        summary = analyzer.save_summary()
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    elif args.ip:
        safe_ip = args.ip.replace(".", "_")
        ip_file = analyzer.today_dir / f"{safe_ip}.jsonl"
        if ip_file.exists():
            print(f"IP {args.ip} 的记录:")
            with open(ip_file, "r") as f:
                for line in f:
                    print(line.strip())
        else:
            print(f"未找到 IP {args.ip} 的记录")
    else:
        summary = analyzer.save_summary()
        print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
