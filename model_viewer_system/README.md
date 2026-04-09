# vLLM 日志查看器系统

独立的日志查看器和代理服务控制系统。

## 目录结构

```
log_viewer_system/
├── server.py          # Web 服务器
├── index.html         # Web 界面
├── start.sh           # 启动脚本
├── proxy_config.json  # 代理配置
└── logs/              # 日志存储目录
```

## 快速启动

```bash
# 默认端口 9001
bash start.sh

# 自定义端口
bash start.sh 9002
```

## 访问地址

- 本地：http://localhost:9001/
- 局域网：http://192.168.68.120:9001/

## 功能

1. **代理服务控制**
   - 选择端口 (8888/9999)
   - 点击"启动代理服务"按钮启动
   - 实时日志显示

2. **历史会话**
   - 按日期浏览
   - 查看会话详情

3. **配置管理**
   - 在线编辑代理配置
   - 保存立即生效

## 移动到其他目录

整个 `log_viewer_system` 目录可以直接移动：

```bash
# 复制到任意位置
cp -r log_viewer_system /new/location/

# 启动
cd /new/location/log_viewer_system
bash start.sh
```

确保目标机器可以访问：
- vLLM 服务端口 (5555, 5557)
- Python 环境 `/root/anaconda3/envs/vllm/bin/python`
