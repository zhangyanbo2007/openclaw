import requests

API_URL = "https://cloudapi.proppt.link/v1/chat/completions"
API_KEY = "sk-BBamAQkA1MGk2biof2zTNyD5tWPuaZSY1ZoB3EpEQpVosEnV"

MODELS_URL = "https://cloudapi.proppt.link/v1/models"


def get_models() -> list:
    resp = requests.get(
        MODELS_URL,
        headers={"Authorization": f"Bearer {API_KEY}"},
        timeout=30,
    )
    resp.raise_for_status()
    return sorted([m["id"] for m in resp.json()["data"]])


def chat(model: str, messages: list) -> str:
    resp = requests.post(
        API_URL,
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
        json={"model": model, "messages": messages},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


if __name__ == "__main__":
    # 列出所有可用模型
    print("=== 可用模型列表 ===")
    models = get_models()
    for m in models:
        print(f"  - {m}")
    print(f"共 {len(models)} 个模型\n")

    # 测试 claude-sonnet-4-6
    print("=== 测试 claude-sonnet-4-6 ===")
    print(chat("claude-sonnet-4-6", [{"role": "user", "content": "你好，用一句话介绍自己"}]))

    # 测试 claude-3-7-sonnet-20250219
    print("\n=== 测试 claude-3-7-sonnet-20250219 ===")
    print(chat("claude-3-7-sonnet-20250219", [{"role": "user", "content": "你好，用一句话介绍自己"}]))
