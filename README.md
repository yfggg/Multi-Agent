# LangGraph 多智能体（阿里云资源查询）

入口与交互流程说明：main.py
规划逻辑与回退策略：planning.py
LangGraph 执行图与节点职责：workflow.py
各 Agent 行为与分支：agents.py
问题解析与地域识别：helpers.py
OpenAPI/DashScope 调用封装：tools.py

这是阿里云多智能体教程的 LangGraph 版本复刻。
保持相同的结构（规划 -> 专项 Agent -> 汇总），不包含交互界面。

## 功能说明
- Planner 根据用户问题选择需要执行的 Agent。
- AliyunInfoAssistant 通过 OpenAPI 查询 ECS 实例与账户余额。
- InstanceTypeDetailAssistant 在需要规格/CPU/内存时，会优先使用 ECS 查询结果中的实例规格列表，再调用 DashScope RAG 应用查询详情（问题里已包含规格名也可直接查询）。
- SummaryAssistant 汇总各 Agent 输出给出最终答案。

## 安装与配置
1) 安装依赖：
```
pip install -r requirements.txt
```

2) 配置环境变量：
```
$env:DASHSCOPE_API_KEY = "YOUR_DASHSCOPE_API_KEY"
$env:ALIBABA_CLOUD_ACCESS_KEY_ID = "YOUR_ALIBABA_CLOUD_ACCESS_KEY_ID"
$env:ALIBABA_CLOUD_ACCESS_KEY_SECRET = "YOUR_ALIBABA_CLOUD_ACCESS_KEY_SECRET"
$env:RAG_APP_ID = "YOUR_RAG_APP_ID"
```

可选：
```
$env:DEFAULT_REGION_ID = "cn-hangzhou"
$env:DASHSCOPE_MODEL = "qwen-plus"
```

## 运行
```
python main.py "查询我在 cn-hangzhou 的 ECS 实例并返回余额"
```

更多测试命令示例：
```
python main.py "我的阿里云余额还有多少钱啊"
python main.py "我在杭州有哪些 ECS 实例"
python main.py "我想知道我在杭州的 ECS 实例，还有我的阿里云余额"
python main.py "我在杭州有哪些 ECS 实例，把每个实例规格的 CPU/内存告诉我"
python main.py "请介绍 ecs.e-c1m1.large 的实例规格（CPU/内存）"
```

如果问题中没有包含地域，请设置 `DEFAULT_REGION_ID`。

## .env 使用说明
- 推荐使用 `.env` 文件配置密钥，项目启动时会自动加载。
- 参考模板：`.env.example`，复制为 `.env` 后填入你的真实值。
