#!/usr/bin/env bash
# update.sh — 更新 A股前10市值数据
# 优先从东方财富 API 抓取实时数据，失败则保留现有数据

set -euo pipefail

# 脚本所在目录（确保相对路径正确）
DIR="$(cd "$(dirname "$0")" && pwd)"
DATA_FILE="$DIR/data.json"

# 当前时间戳
NOW=$(date '+%Y-%m-%d %H:%M:%S')

echo "[$NOW] 开始更新数据..."

# ===== 东方财富 行情 API =====
# secids 格式：市场.代码  1=上证  0=深证
# fields: f2=现价 f3=涨跌幅 f10=市盈率 f20=市值(元)
SECIDS="1.600519,1.601398,1.601288,1.600941,1.601939,1.601318,1.601988,1.600036,0.300750,1.601857"
FIELDS="f12,f14,f2,f3,f20"
API_URL="https://push2.eastmoney.com/api/qt/ulist.semi.pushdata/get?secids=${SECIDS}&fields=${FIELDS}&cb=&ut=b2884a393a59ad64002292a3e90d46a5"

# 抓取数据（超时10秒，失败则退出）
RAW=$(curl -sf --max-time 10 "$API_URL" || true)

if [ -z "$RAW" ]; then
  echo "警告：API 请求失败，保留原有数据，仅更新时间戳。"
  # 仅更新 lastUpdated 字段
  python3 - "$DATA_FILE" "$NOW" <<'PYEOF'
import json, sys
path, now = sys.argv[1], sys.argv[2]
with open(path) as f:
    data = json.load(f)
data['lastUpdated'] = now
with open(path, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print("时间戳已更新。")
PYEOF
  exit 0
fi

# ===== 解析 JSON 并写入 data.json =====
python3 - "$DATA_FILE" "$NOW" "$RAW" <<'PYEOF'
import json, sys

data_path = sys.argv[1]
now       = sys.argv[2]
raw       = sys.argv[3]

# 读取现有数据（保留结构）
with open(data_path, encoding='utf-8') as f:
    data = json.load(f)

# 解析东方财富返回的 JSON
try:
    obj = json.loads(raw)
    items = obj['data']['diff']
except Exception as e:
    print(f"解析失败: {e}，保留原有数据。")
    data['lastUpdated'] = now
    with open(data_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    sys.exit(0)

# 代码到现有条目的映射，方便更新
code_map = {s['code']: s for s in data['stocks']}

for item in items:
    code = str(item.get('f12', ''))
    if code not in code_map:
        continue
    entry = code_map[code]
    try:
        entry['price']     = round(float(item['f2']), 2)
        entry['change']    = round(float(item['f3']), 2)
        # f20 单位为元，转亿元
        entry['marketCap'] = round(float(item['f20']) / 1e8)
    except (KeyError, TypeError, ValueError):
        pass  # 字段缺失则保留原值

# 按市值重新排名
data['stocks'].sort(key=lambda s: s['marketCap'], reverse=True)
for i, s in enumerate(data['stocks'], 1):
    s['rank'] = i

data['lastUpdated'] = now
data['source']      = '东方财富'

with open(data_path, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"数据更新完成，共 {len(data['stocks'])} 条。")
PYEOF

echo "[$NOW] 完成。"
