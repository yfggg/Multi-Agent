# 多智能体客服（资源查询 + 智能导购）

本项目支持两类核心任务：
- 资源查询：Planner 选择 AliyunInfoAssistant / InstanceTypeDetailAssistant / ChatAssistant 的执行顺序，并由 Summary 汇总。
- 智能导购：Router 决定是否进入导购流程，Guide 负责需求收集，Recommend 基于 RAG 给出推荐。

## 代码结构
- 统一入口与交互：`main.py`
- LangGraph 编排入口：`workflow.py`
- 顶层任务路由：`planning.py`
- 导购流程实现：`shopping_flow.py`
- 资源查询流程实现：`resource_flow.py`
- 通用/规格助手：`agents.py`
- 对话辅助：`helpers.py`
- DashScope 调用与 OpenAPI 封装：`tools.py`

## 安装与配置
1) 安装依赖：
```
pip install -r requirements.txt
```

2) 配置环境变量：
```
$env:DASHSCOPE_API_KEY = "YOUR_DASHSCOPE_API_KEY"
$env:RAG_APP_ID = "YOUR_RAG_APP_ID"
```

可选：
```
$env:DEFAULT_REGION_ID = "cn-hangzhou"
$env:DASHSCOPE_MODEL = "qwen-plus"
```

如需查询账号余额或 ECS 实例，请再配置：
```
$env:ALIBABA_CLOUD_ACCESS_KEY_ID = "YOUR_ALIBABA_CLOUD_ACCESS_KEY_ID"
$env:ALIBABA_CLOUD_ACCESS_KEY_SECRET = "YOUR_ALIBABA_CLOUD_ACCESS_KEY_SECRET"
```

## 运行
进入多轮对话：
```
python main.py
```

从一句话开始：
```
python main.py "我想选一台适合 Web 服务的实例"
```

指定会话 ID：
```
python main.py --session-id user-123 "我想选一台适合 Web 服务的实例"
```

交互指令：
- 输入 `exit/quit/退出` 结束对话
- 输入 `reset` 重置导购状态

## 示例
资源查询：
```
我的阿里云余额还有多少？
我在杭州有哪些 ECS 实例？
介绍一下 ecs.g8i.large 的规格
```

导购：
```
我要选型，预算每月 500 元，2-4 核，内存 8-16GB
```
