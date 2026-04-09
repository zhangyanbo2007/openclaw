#!/usr/bin/env python3

import requests

# 配置
BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
API_KEY = "sk-c46672dd5e29441981b511123d2b8095"
MODEL = "text-embedding-v4"

# 测试文本
text = "这是一个测试"

# 调用 API
response = requests.post(
    f"{BASE_URL}/embeddings",
    headers={"Authorization": f"Bearer {API_KEY}"},
    json={"model": MODEL, "input": text}
)

# 输出结果
if response.status_code == 200:
    data = response.json()
    embedding = data["data"][0]["embedding"]
    print(f"✅ 成功")
    print(f"向量维度: {len(embedding)}")
    print(f"前5维: {embedding[:5]}")
else:
    print(f"❌ 失败: {response.text}")
