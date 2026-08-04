from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.db.database import init_db
from app.api.admin_routes import admin_router



app = FastAPI(
    title="DocuSearch Agent API",
    description="全栈私有知识库 RAG 智能问答平台",
    version="0.1.0",
)

app.include_router(admin_router)

@app.on_event("startup")
def on_startup():
    """
    后端服务启动时自动执行。

    这里主要做数据库初始化：
    1. 创建 data/app.db
    2. 根据 models 里的表结构创建数据库表
    3. 如果表已经存在，不会重复创建
    """
    init_db()


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(router)
