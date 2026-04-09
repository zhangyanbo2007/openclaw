#!/bin/bash
# 人脸识别脚本 - 用于进出门检测
# 使用方法：bash face_recognition.sh [image_path]

# ==================== 配置区域 ====================
ACCESS_KEY_ID="LTAI5tJwStftMmxKNNXC3bbi"
ACCESS_KEY_SECRET="Bb6cOOmap0dNuPP849PXp62Iuyax7G"
DB_NAME="home_family"
OWNER_ID="zhangyanbo"
THRESHOLD=80

# 默认使用猫眼抓图
IMAGE_PATH="${1:-/tmp/openclaw/face_zhangyanbo.jpg}"
# ==================== 配置区域 ====================

# 检查图片是否存在
if [ ! -f "$IMAGE_PATH" ]; then
    echo "❌ 图片不存在：$IMAGE_PATH"
    exit 1
fi

# 生成签名参数
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
NONCE=$(cat /proc/sys/kernel/random/uuid)

# 将图片转换为 Base64
IMG_BASE64=$(base64 -w 0 "$IMAGE_PATH")

# 构造请求参数
PARAMS="AccessKeyId=$ACCESS_KEY_ID"
PARAMS="$PARAMS&Action=SearchFace"
PARAMS="$PARAMS&DbName=$DB_NAME"
PARAMS="$PARAMS&Format=JSON"
PARAMS="$PARAMS&ImageUrl=data:image/jpeg;base64,$IMG_BASE64"
PARAMS="$PARAMS&Limit=1"
PARAMS="$PARAMS&RegionId=cn-shanghai"
PARAMS="$PARAMS&SignatureMethod=HMAC-SHA1"
PARAMS="$PARAMS&SignatureNonce=$NONCE"
PARAMS="$PARAMS&SignatureVersion=1.0"
PARAMS="$PARAMS&Threshold=$THRESHOLD"
PARAMS="$PARAMS&Timestamp=$TIMESTAMP"
PARAMS="$PARAMS&Version=2019-12-30"

# 使用 Python 计算签名并发送请求（避免 bash 处理长参数的问题）
python3 << PYEOF
import hashlib
import hmac
import base64
import json
import urllib.request
import urllib.parse
import os

ACCESS_KEY_ID = "$ACCESS_KEY_ID"
ACCESS_KEY_SECRET = "$ACCESS_KEY_SECRET"
OWNER_ID = "$OWNER_ID"
THRESHOLD = $THRESHOLD

params = "$PARAMS"

def percent_encode(value):
    if value is None:
        return ""
    return urllib.parse.quote(str(value), safe='')

# 解析参数
param_dict = {}
for item in params.split('&'):
    if '=' in item:
        k, v = item.split('=', 1)
        param_dict[k] = v

# 计算签名
sorted_params = sorted(param_dict.items())
canonicalized = '&'.join(f'{percent_encode(k)}={percent_encode(v)}' for k, v in sorted_params)
string_to_sign = f'POST&{percent_encode("/")}&{percent_encode(canonicalized)}'
signature = base64.b64encode(hmac.new((ACCESS_KEY_SECRET + '&').encode(), string_to_sign.encode(), hashlib.sha1).digest()).decode()

# 构造完整请求
post_data = '&'.join(f'{percent_encode(k)}={percent_encode(v)}' for k, v in sorted_params)
post_data = f'{post_data}&Signature={percent_encode(signature)}'

url = 'https://facebody.cn-shanghai.aliyuncs.com/'
req = urllib.request.Request(url, data=post_data.encode(), headers={"Content-Type": "application/x-www-form-urlencoded"})

try:
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read().decode())
        
        # 输出 JSON 结果供 shell 解析
        print(json.dumps(result, ensure_ascii=False))
        
        # 解析识别结果
        if "Data" in result and "FaceList" in result["Data"]:
            faces = result["Data"]["FaceList"]
            if len(faces) > 0:
                entity = faces[0].get("EntityId", "")
                score = faces[0].get("Score", 0)
                
                # 写入结果文件供 HA 读取
                with open('/tmp/openclaw/face_result.json', 'w') as f:
                    json.dump({
                        "entity_id": entity,
                        "score": score,
                        "is_owner": entity == OWNER_ID and score >= THRESHOLD
                    }, f)
                
                # 输出结果供 shell 使用
                if entity == OWNER_ID and score >= THRESHOLD:
                    os.environ['FACE_RESULT'] = 'owner'
                else:
                    os.environ['FACE_RESULT'] = 'other'
            else:
                with open('/tmp/openclaw/face_result.json', 'w') as f:
                    json.dump({"entity_id": None, "score": 0, "is_owner": False}, f)
                os.environ['FACE_RESULT'] = 'unknown'
        else:
            with open('/tmp/openclaw/face_result.json', 'w') as f:
                json.dump({"error": result}, f)
            os.environ['FACE_RESULT'] = 'error'
            
except Exception as e:
    print(json.dumps({"error": str(e)}))
    with open('/tmp/openclaw/face_result.json', 'w') as f:
        json.dump({"error": str(e)}, f)
PYEOF

# 读取结果
if [ -f /tmp/openclaw/face_result.json ]; then
    RESULT=$(cat /tmp/openclaw/face_result.json)
    IS_OWNER=$(echo "$RESULT" | jq -r '.is_owner // false')
    ENTITY=$(echo "$RESULT" | jq -r '.entity_id // "unknown"')
    SCORE=$(echo "$RESULT" | jq -r '.score // 0')
    
    echo ""
    echo "🎯 识别结果:"
    echo "   人员：$ENTITY"
    echo "   相似度：$SCORE%"
    
    if [ "$IS_OWNER" = "true" ]; then
        echo "✅ 是主人回家"
        exit 0
    else
        echo "ℹ️  不是主人或识别失败"
        exit 1
    fi
else
    echo "❌ 识别失败"
    exit 1
fi
