#!/bin/bash
# 测试阿里云 API - 使用新 AccessKey

# 请在这里填写你的新 AccessKey Secret
NEW_ACCESS_KEY_ID="LTAI4Fusnoh6zcArNqh2tecU"
NEW_ACCESS_KEY_SECRET="请替换为你的实际 Secret"

if [ "$NEW_ACCESS_KEY_SECRET" = "请替换为你的实际 Secret" ]; then
    echo "❌ 请先填写 AccessKey Secret"
    echo ""
    echo "获取 Secret 的方法："
    echo "1. 访问 https://ram.console.aliyun.com/manage/ak"
    echo "2. 找到 AccessKey ID: $NEW_ACCESS_KEY_ID"
    echo "3. 查看或重新生成 Secret"
    echo "4. 将 Secret 填写到此脚本中"
    exit 1
fi

echo "✅ 配置完成，准备测试..."
