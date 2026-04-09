#!/bin/bash

# 工具调用对比测试脚本
# 测试 vLLM 本地模型 vs 阿里云 Qwen3.5-Plus

set -e

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# API 配置
VLLM_BASE_URL="http://192.168.68.120:5555/v1"
VLLM_MODEL="qwen3.5-27b"
ALIYUN_BASE_URL="https://dashscope.aliyuncs.com/apps/anthropic"
ALIYUN_MODEL="qwen3.5-plus"
ALIYUN_API_KEY="sk-a2675c4123764e46880426a87bff42de"

# 测试提示词 - 需要调用多个工具
TEST_PROMPT="请先查询广州的天气，然后告诉我今天是星期几。请使用可用的工具来完成这两个任务。"

# 工具定义（OpenAI 格式）
TOOLS_OPENAI='[
  {
    "type": "function",
    "function": {
      "name": "get_weather",
      "description": "查询指定城市的天气预报",
      "parameters": {
        "type": "object",
        "properties": {
          "city": {
            "type": "string",
            "description": "城市名称，例如：广州、北京、上海"
          },
          "days": {
            "type": "integer",
            "description": "查询天数，默认 3 天",
            "default": 3
          }
        },
        "required": ["city"]
      }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "get_current_date",
      "description": "获取当前日期和星期几",
      "parameters": {
        "type": "object",
        "properties": {
          "format": {
            "type": "string",
            "description": "日期格式，例如：full, short",
            "enum": ["full", "short"],
            "default": "full"
          }
        },
        "required": []
      }
    }
  }
]'

# 工具定义（Anthropic 格式）
TOOLS_ANTHROPIC='[
  {
    "name": "get_weather",
    "description": "查询指定城市的天气预报",
    "input_schema": {
      "type": "object",
      "properties": {
        "city": {
          "type": "string",
          "description": "城市名称，例如：广州、北京、上海"
        },
        "days": {
          "type": "integer",
          "description": "查询天数，默认 3 天"
        }
      },
      "required": ["city"]
    }
  },
  {
    "name": "get_current_date",
    "description": "获取当前日期和星期几",
    "input_schema": {
      "type": "object",
      "properties": {
        "format": {
          "type": "string",
          "description": "日期格式，例如：full, short",
          "enum": ["full", "short"]
        }
      }
    }
  }
]'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   工具调用对比测试${NC}"
echo -e "${BLUE}   vLLM Qwen3.5-27B vs 阿里云 Qwen3.5-Plus${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 测试 vLLM 本地模型
echo -e "${YELLOW}[测试 1] vLLM 本地模型 (qwen3.5-27b)${NC}"
echo -e "API: ${VLLM_BASE_URL}"
echo -e "提示词：${TEST_PROMPT}"
echo ""

VLLM_START=$(date +%s%3N)

VLLM_RESPONSE=$(curl -s -X POST "${VLLM_BASE_URL}/chat/completions" \
  -H "Authorization: Bearer not-needed" \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"${VLLM_MODEL}\",
    \"messages\": [
      {\"role\": \"user\", \"content\": \"${TEST_PROMPT}\"}
    ],
    \"tools\": ${TOOLS_OPENAI},
    \"tool_choice\": \"auto\",
    \"stream\": false,
    \"max_tokens\": 2048
  }")

VLLM_END=$(date +%s%3N)
VLLM_LATENCY=$((VLLM_END - VLLM_START))

echo -e "${GREEN}响应时间：${VLLM_LATENCY}ms${NC}"
echo -e "完整响应:"
echo "${VLLM_RESPONSE}" | jq '.'
echo ""

# 提取 vLLM 的工具调用信息
VLLM_TOOL_CALLS=$(echo "${VLLM_RESPONSE}" | jq -r '.choices[0].message.tool_calls // [] | length')
echo -e "${GREEN}工具调用次数：${VLLM_TOOL_CALLS}${NC}"
echo ""

# 测试阿里云模型
echo -e "${YELLOW}[测试 2] 阿里云 Qwen3.5-Plus${NC}"
echo -e "API: ${ALIYUN_BASE_URL}"
echo -e "提示词：${TEST_PROMPT}"
echo ""

ALIYUN_START=$(date +%s%3N)

ALIYUN_RESPONSE=$(curl -s -X POST "${ALIYUN_BASE_URL}/v1/messages" \
  -H "X-API-Key: ${ALIYUN_API_KEY}" \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"${ALIYUN_MODEL}\",
    \"max_tokens\": 2048,
    \"messages\": [
      {\"role\": \"user\", \"content\": \"${TEST_PROMPT}\"}
    ],
    \"tools\": ${TOOLS_ANTHROPIC},
    \"tool_choice\": \"auto\"
  }")

ALIYUN_END=$(date +%s%3N)
ALIYUN_LATENCY=$((ALIYUN_END - ALIYUN_START))

echo -e "${GREEN}响应时间：${ALIYUN_LATENCY}ms${NC}"
echo -e "完整响应:"
echo "${ALIYUN_RESPONSE}" | jq '.'
echo ""

# 提取阿里云的工具调用信息（Anthropic 格式）
ALIYUN_TOOL_CALLS=$(echo "${ALIYUN_RESPONSE}" | jq -r '[.content[] | select(.type == "tool_use")] | length' 2>/dev/null || echo "0")
echo -e "${GREEN}工具调用次数：${ALIYUN_TOOL_CALLS}${NC}"
echo ""

# 对比总结
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   对比总结${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "指标                  vLLM 本地        阿里云"
echo -e "------------------------------------------------------------"
printf "%-20s  %8dms     %8dms\n" "响应时间" ${VLLM_LATENCY} ${ALIYUN_LATENCY}
printf "%-20s  %8d次     %8d次\n" "工具调用次数" ${VLLM_TOOL_CALLS} ${ALIYUN_TOOL_CALLS}
echo ""

# 保存详细结果
VLLM_RESULT_FILE="/tmp/vllm-tool-call-$(date +%Y%m%d-%H%M%S).json"
ALIYUN_RESULT_FILE="/tmp/aliyun-tool-call-$(date +%Y%m%d-%H%M%S).json"

echo "${VLLM_RESPONSE}" > "${VLLM_RESULT_FILE}"
echo "${ALIYUN_RESPONSE}" > "${ALIYUN_RESULT_FILE}"

echo -e "${GREEN}详细结果已保存:${NC}"
echo -e "  vLLM:   ${VLLM_RESULT_FILE}"
echo -e "  阿里云：${ALIYUN_RESULT_FILE}"
