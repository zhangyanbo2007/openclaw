#!/usr/bin/env python3

import requests

# 配置
BASE_URL = "https://api.nonelinear.com/v1"
API_KEY = "sk-892c38e6e81f76ddd6169b7471b9d7a4"
MODEL = "Qwen3-Embedding-8B"

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
