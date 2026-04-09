#!/bin/bash
# 阿里云人脸识别测试脚本
# 使用方法：填写 AccessKey Secret 后运行 bash test_face_recognition.sh

# ==================== 配置区域 ====================
# 请填写你的 AccessKey Secret（在 RAM 控制台获取）
ACCESS_KEY_ID="LTAI5tDvdyose9UQdkojDxXZ"
ACCESS_KEY_SECRET="y9HZr4tbFgZdexKHYJWDFnAxkEfB62"

# 人脸库配置
DB_NAME="home_family_db"
ENTITY_ID="zhangyanbo"

# 测试图片（猫眼抓图）
TEST_IMAGE="/tmp/openclaw/face_test.jpg"
# ==================== 配置区域 ====================

if [ "$ACCESS_KEY_SECRET" = "请在此处填写你的 AccessKey Secret" ]; then
    echo "❌ 错误：请先填写 AccessKey Secret"
    echo ""
    echo "📋 获取 Secret 的步骤："
    echo "1. 访问阿里云 RAM 控制台：https://ram.console.aliyun.com/manage/ak"
    echo "2. 找到 AccessKey ID: $ACCESS_KEY_ID"
    echo "3. 复制对应的 AccessKey Secret"
    echo "4. 将 Secret 填写到本脚本第 9 行"
    echo ""
    echo "⚠️ 注意：Secret 只在创建时显示一次，如果忘记了请重新生成"
    exit 1
fi

echo "🔍 开始测试阿里云人脸识别..."
echo "AccessKey ID: $ACCESS_KEY_ID"
echo "人脸库：$DB_NAME"
echo "实体 ID: $ENTITY_ID"
echo ""

# 生成签名参数
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
NONCE=$(cat /proc/sys/kernel/random/uuid)

# 检查测试图片
if [ ! -f "$TEST_IMAGE" ]; then
    echo "❌ 测试图片不存在：$TEST_IMAGE"
    echo "请先运行猫眼抓图脚本"
    exit 1
fi

# 将图片转换为 Base64
IMG_BASE64=$(base64 -w 0 "$TEST_IMAGE")

# 构造请求参数
PARAMS="AccessKeyId=$ACCESS_KEY_ID"
PARAMS="$PARAMS&Action=SearchFace"
PARAMS="$PARAMS&Format=JSON"
PARAMS="$PARAMS&RegionId=cn-shanghai"
PARAMS="$PARAMS&SignatureMethod=HMAC-SHA1"
PARAMS="$PARAMS&SignatureNonce=$NONCE"
PARAMS="$PARAMS&SignatureVersion=1.0"
PARAMS="$PARAMS&Timestamp=$TIMESTAMP"
PARAMS="$PARAMS&Version=2019-12-30"
PARAMS="$PARAMS&DbName=$DB_NAME"
PARAMS="$PARAMS&ImageUrl=data:image/jpeg;base64,$IMG_BASE64"
PARAMS="$PARAMS&Limit=1"
PARAMS="$PARAMS&Threshold=80"

# URL 编码
ENCODED_PARAMS=$(echo -n "$PARAMS" | sed 's/&/\n/g' | while read line; do
    key=$(echo "$line" | cut -d= -f1)
    value=$(echo "$line" | cut -d= -f2-)
    echo -n "$(printf '%s' "$key" | jq -sRr @uri)=$(printf '%s' "$value" | jq -sRr @uri)&"
done | sed 's/&$//')

# 构造签名字符串
STRING_TO_SIGN="POST&%2F&$(echo -n "$ENCODED_PARAMS" | jq -sRr @uri)"

# 计算签名
SIGNATURE=$(echo -n "$STRING_TO_SIGN" | openssl dgst -sha1 -hmac "${ACCESS_KEY_SECRET}&" -binary | base64)

# 构造完整请求
POST_DATA="$ENCODED_PARAMS&Signature=$(echo -n "$SIGNATURE" | jq -sRr @uri)"

echo "📡 发送请求..."
echo ""

# 发送请求
RESPONSE=$(curl -s -X POST "https://facebody.cn-shanghai.aliyuncs.com/" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "$POST_DATA")

# 解析结果
echo "📊 返回结果:"
echo "$RESPONSE" | jq .

# 检查是否成功
CODE=$(echo "$RESPONSE" | jq -r '.Code // empty')
if [ "$CODE" = "200" ] || [ -n "$(echo "$RESPONSE" | jq '.Data.FaceList // empty')" ]; then
    echo ""
    echo "✅ 人脸识别测试成功!"
    
    # 显示识别结果
    ENTITY=$(echo "$RESPONSE" | jq -r '.Data.FaceList[0].EntityId // "未识别"')
    SCORE=$(echo "$RESPONSE" | jq -r '.Data.FaceList[0].Score // "0"')
    
    echo ""
    echo "🎯 识别结果:"
    echo "   人员：$ENTITY"
    echo "   相似度：$SCORE%"
    
    if [ "$ENTITY" = "$ENTITY_ID" ] && [ "$(echo "$SCORE > 80" | bc)" -eq 1 ]; then
        echo ""
        echo "✅ 识别成功！是主人回家"
    else
        echo ""
        echo "ℹ️  识别结果不是主人或相似度较低"
    fi
else
    echo ""
    MESSAGE=$(echo "$RESPONSE" | jq -r '.Message // "未知错误"')
    echo "❌ 测试失败：$MESSAGE"
    
    if echo "$MESSAGE" | grep -q "AccessPolicyDenied"; then
        echo ""
        echo "🔧 解决方案："
        echo "1. 确认 AccessKey Secret 填写正确"
        echo "2. 在 RAM 控制台确认已添加 AliyunVisionFullAccess 权限"
        echo "3. 等待 1-2 分钟让权限生效"
    fi
fi
