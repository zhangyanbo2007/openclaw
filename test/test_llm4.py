import requests

API_URL = "https://api.siliconflow.cn/v1/chat/completions"
API_KEY = "sk-ftwkhnczvdiliywzptityoqvlgxxggzoznwzwmsabamxzvwj"


def list_models() -> list:
    resp = requests.get(
        "https://api.siliconflow.cn/v1/models",
        headers={"Authorization": f"Bearer {API_KEY}"},
        timeout=30
    )
    resp.raise_for_status()
    return [m["id"] for m in resp.json()["data"]]

print("=== 可用模型列表 ===")
for m in list_models():
    print(f"  - {m}")
print()

# 可用模型列表：
#
# | 模型 ID |
# |---------|
# | DeepSeek-R1-Distill-Qwen-7B |
# | DeepSeek-R1-Distill-Qwen-32B |
# | DeepSeek-R1-671B |
# | DeepSeek-R1-Distill-Llama-70B |
# | QwQ-32B |
# | Qwen3-30B-A3B |
# | Qwen3-235B-A22B |
# | Qwen3-Embedding-8B |
# | Qwen3-Coder-480B-A35B-Instruct |
# | Qwen3-235B-A22B-Thinking-2507 |
# | MiniMax-M2 |
# | DeepSeek-V3.2 |
# | Qwen3-30B-A3B-Instruct-2507 |
# | DeepSeek-R1-0528 |
# | OCR |
# | **MiniMax-M2.5** |
# | MiniMax-M2.5-Tencent |
# | MiniMax-M2.5-ZD |
# | MiniMax-M2.5-VIP |
#
# 总计 **19 个模型**，涵盖推理、编码、Embedding、OCR 等类型。
#
def chat(model: str, messages: list) -> str:
    resp = requests.post(
        API_URL,
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
        json={"model": model, "messages": messages},
        timeout=60
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]

# 测试 GPT-5.4
print("=== 测试 gpt ===")
print(chat("Pro/MiniMaxAI/MiniMax-M2.5", [{"role": "user", "content": "你好，用一句话介绍自己"}]))
