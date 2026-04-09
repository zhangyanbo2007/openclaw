# 6，7卡打开，核心：H800双卡 + 891289上下文 + KV Cache全开 + FP16（平衡精度/显存）
python -m vllm.entrypoints.openai.api_server \
  --model /data/project/public/hub_repository/modelscope/hub/Qwen/Qwen3.5-27B \
  --tensor-parallel-size 2 \
  --pipeline-parallel-size 1 \
  --gpu-memory-utilization 0.97 \
  --dtype fp16 \
  --max-model-len 1048576 \
  --max-num-batched-tokens 1048576 \
  --max-num-seqs 1 \
  --enable-chunked-prefill True \
  --chunked-prefill-size 16384 \
  --trust-remote-code True \
  --host 0.0.0.0 \
  --port 8001