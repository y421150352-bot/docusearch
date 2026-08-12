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

## 当前开发进度（2026-08）

### 已完成

- **基础架构**：FastAPI + React/Vite 前端，MySQL 存储文献元数据、切片与历史记录，Qdrant 存储 Dense + Sparse 向量，Redis 存储缓存和任务状态。
- **文献处理链路**：上传单篇 PDF / TXT / MD 后，后台依次完成解析、目录噪声清理、MySQL 切片写入、Qdrant 向量写入，并将文献状态更新为“可用于问答”。
- **检索策略**：使用 Qdrant Dense Vector + BM25 Sparse Vector + RRF 融合检索；目录、连续点线页码等内容不会参与召回。
- **用户与权限**：已实现数据库 Session Token、Bearer Header 与 `admin` / `user` 角色。普通用户只能访问自己的文献、问答历史、缓存和检索结果。
- **管理员功能**：支持查看全部文献、删除指定用户文献、查看任务状态、查看问答反馈，以及在“RAG 评测”页面直接查看某个问题召回的原文切片。
- **前端页面**：普通用户拥有“新对话 / 我的文献库 / 历史记录”；管理员额外拥有“全部文献管理 / 任务 / RAG 评测”。
- **工程化**：Docker Compose 支持 MySQL、Qdrant、Redis 与前后端启动；已包含基础测试和 GitHub Actions CI。

### 当前注意事项

- 生成式问答目前通过 `/agent-chat` 运行 LangChain Tool Calling Agent。普通文献问题会经过工具选择、检索、生成与最终整理，响应时间可能较长。
- 大模型 Key 不再写入代码。请在本机 `.env` 中配置 `LLM_API_KEY`；不要提交 `.env`。
- 当前私有仓库保留了本地 PDF 与检索数据，适合作为个人备份；如果未来公开仓库，应移除真实文献、向量索引与所有密钥。

### 下一阶段计划

1. 将普通文献问答改为直接 RAG 流式输出，减少 Agent 多次串行调用导致的等待。
2. 增加“用户自带模型 Key（BYOK）”设置页与加密存储，避免所有用户共用平台 Key。
3. 完善 RAG 评测：增加固定问题集、召回率 / MRR 等指标和版本对比。
4. 增加多模态 PDF 图片、表格的解析与问答能力。
5. 增加用户注册、账号管理、审计日志与更细粒度的管理员权限。

## 建议的后续工程化工作

- 增加结构化日志与错误告警
- 为上传文档增加大小限制与审计记录
- 引入 CI，默认执行快速测试
- 将评测脚本接入定期回归
