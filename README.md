# DocuSearch Agent

面向内部知识库场景的 RAG 问答工具，包含：

- FastAPI 后端
- React + Vite + TypeScript 前端
- MySQL 元数据、问答历史与反馈
- Redis 缓存与后台任务状态
- BM25 + Qdrant 混合检索
- Docker Compose 本地部署

## 目标

这个项目现在按“可长期维护的内部工具”组织，重点是：

- 配置可移植
- 依赖健康可观测
- 测试可分快慢两层执行
- 运行时数据不混入代码仓库

## 目录结构

```text
app/        后端服务
frontend/   前端界面
tests/      pytest 测试
data/       本地数据库、上传文档、检索索引
docs/       补充文档
evals/      评测脚本与数据
scripts/    辅助脚本
```

## 环境准备

### 后端

1. 创建并激活虚拟环境
2. 安装依赖

```powershell
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install -r requirements-app.txt
```

3. 复制环境变量模板

```powershell
Copy-Item .env.example .env
```

4. 按需填写 `.env`

关键变量：

- `LLM_API_KEY`: 大模型 API Key
- `LLM_BASE_URL`: 大模型服务地址，默认 `https://api.deepseek.com`
- `LLM_MODEL`: 默认 `deepseek-chat`
- `DATABASE_URL`: MySQL SQLAlchemy 连接地址
- `QDRANT_URL` / `QDRANT_COLLECTION_NAME`
- `REDIS_HOST` / `REDIS_PORT`
- `EMBEDDING_MODEL_NAME`
- `USE_RERANKER`
- `RERANKER_MODEL_NAME`

### 前端

```powershell
cd frontend
npm install
Copy-Item .env.example .env
```

默认前端后端地址：

- Frontend: `http://127.0.0.1:5173`
- Backend: `http://127.0.0.1:8000`

## 本地启动

### 1. 启动 MySQL、Qdrant 和 Redis

```powershell
docker compose up -d mysql qdrant redis
```

### 2. 启动后端

```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. 启动前端

```powershell
cd frontend
npm run dev
```

## Docker 启动

```powershell
docker compose up --build
```

服务端口：

- Frontend: `http://127.0.0.1:5173`
- Backend: `http://127.0.0.1:8000`
- MySQL: `127.0.0.1:3307`
- Qdrant: `http://127.0.0.1:6333`
- Redis: `127.0.0.1:6379`

## 健康检查

后端提供 `GET /health`，会返回：

- API 服务状态
- MySQL 是否可用
- Qdrant 集合是否可用
- Redis 是否可达
- 检索索引文件是否存在
- LLM 是否已配置

状态分为：

- `ok`: 核心依赖全部可用
- `warning`: 核心依赖可用，但可选能力未就绪
- `degraded`: 核心依赖存在故障

前端 Dashboard 会直接展示这些组件状态。

## 测试

### 快速测试

默认只跑非集成测试：

```powershell
python -m pytest -q
```

### 集成测试

集成测试依赖 Redis 或外部 LLM 配置，需要显式开启：

```powershell
python -m pytest -q --run-integration -m integration
```

## 运行数据约定

以下内容属于运行时数据，不建议提交：

- `data/app.db`
- `data/index/`
- `frontend/node_modules/`
- `frontend/dist/`
- `.pytest_cache/`

如果需要保留演示文档，建议只提交经过筛选的样例文件，不把日常上传数据直接纳入版本库。

## 当前能力边界

- `/ask-stream` 当前使用 SSE 返回阶段状态和最终答案切片，已经改为非阻塞执行
- 前端主对话入口使用 `/agent-chat`，所有用户请求统一由 Agent 选择工具执行
- 如果需要真正的 token 级生成流式输出，建议下一步直接接入支持流式回调的 LLM 链路
- 如果未配置 `LLM_API_KEY`，基础页面、文档管理、任务和健康检查仍可运行，但问答能力会受限

## 建议的后续工程化工作

- 增加鉴权与权限模型
- 增加结构化日志与错误告警
- 为上传文档增加大小限制与审计记录
- 引入 CI，默认执行快速测试
- 将评测脚本接入定期回归
