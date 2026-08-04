from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from app.agents.agent_schema import AgentChatRequest
from app.agents.agent_service import run_agent_chat
from app.schemas.ask_schema import AskRequest
from app.schemas.feedback_schema import FeedbackCreateRequest
from app.services.document_service import delete_document, list_documents, save_uploaded_document
from app.services.document_ingestion_service import run_document_ingestion_task
from app.services.feedback_service import create_feedback, delete_feedback, list_feedback
from app.services.health_service import get_health_report
from app.services.history_service import clear_chat_history, delete_chat_history, list_chat_history
from app.services.index_task_service import run_rebuild_index_task
from app.services.qa_service import answer_question
from app.services.qa_stream_service import stream_answer
from app.services.task_service import create_task_id, create_task_record, get_task_status
import secrets
from datetime import datetime, timedelta
from app.schemas.auth_schema import LoginRequest
from app.services.password_service import verify_password
import hashlib
from fastapi.security import HTTPAuthorizationCredentials
from sqlmodel import Session, select
from app.api.dependencies import (
    bearer_scheme,
    get_current_user,
    require_admin,
)
from app.db.database import engine
from app.models.session_model import UserSession
from app.models.user_model import User
router = APIRouter()


def success_response(message: str = "success", data=None) -> dict:
    return {"code": 0, "message": message, "data": data}

@router.get("/auth/me")
def get_me(
    current_user: User = Depends(get_current_user),
):
    return success_response(
        message="当前用户获取成功",
        data={
            "id": current_user.id,
            "username": current_user.username,
            "role": current_user.role,
        },
    )

@router.post("/auth/logout")
def logout(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        bearer_scheme
    ),
    current_user: User = Depends(get_current_user),
):
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="请先登录",
        )

    raw_token = credentials.credentials

    token_hash = hashlib.sha256(
        raw_token.encode("utf-8")
    ).hexdigest()

    with Session(engine) as session:
        user_session = session.exec(
            select(UserSession).where(
                UserSession.token_hash == token_hash,
                UserSession.user_id == current_user.id,
            )
        ).first()

        if user_session is not None:
            user_session.revoked_at = datetime.utcnow()
            session.add(user_session)
            session.commit()

    return success_response(
        message="退出登录成功",
        data=None,
    )
@router.get("/")
def root():
    return success_response(
        data={
            "name": "DocuSearch Agent",
            "description": "Private knowledge base RAG platform",
            "version": "0.1.0",
            "status": "running",
        }
    )


@router.get("/health")
def health_check():
    return success_response(data=get_health_report())


@router.get("/ping")
def ping():
    return success_response(message="pong", data=None)


@router.get("/ask")
def ask(
    question: str,
    document_name: str | None = None,
    current_user: User = Depends(get_current_user),
):
    return answer_question(question, int(current_user.id), document_name)


@router.post("/ask-stream")
def ask_stream(
    request: AskRequest,
    current_user: User = Depends(get_current_user),
):
    return stream_answer(
        question=request.question,
        document_name=request.document_name,
        owner_id=int(current_user.id),
    )


@router.get("/documents")
def get_documents(current_user: User = Depends(get_current_user)):
    return success_response(data=list_documents(int(current_user.id)))


@router.post("/documents/upload")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    try:
        document = await save_uploaded_document(file, int(current_user.id))
        task_id = create_task_id()
        create_task_record(task_id=task_id, task_type="document_ingestion")
        background_tasks.add_task(
            run_document_ingestion_task,
            task_id,
            document["document_name"],
            document["storage_path"],
            int(current_user.id),
        )
        return success_response(
            message="上传完成，正在解析并写入知识库",
            data={
                "document": document,
                "task_id": task_id,
                "status": "processing",
            },
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/documents/{document_name}")
def remove_document(
    document_name: str,
    current_user: User = Depends(get_current_user),
):
    try:
        result = delete_document(document_name, int(current_user.id))
        return success_response(message="document deleted, please rebuild index", data=result)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/rebuild-index")
def rebuild_index(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_admin),
):
    task_id = create_task_id()
    create_task_record(task_id=task_id, task_type="rebuild_index")
    background_tasks.add_task(run_rebuild_index_task, task_id)
    return success_response(
        message="index rebuild task created",
        data={"task_id": task_id, "status": "pending"},
    )


@router.get("/task-status/{task_id}")
def task_status(
    task_id: str,
    current_user: User = Depends(require_admin),
):
    status = get_task_status(task_id)
    if status is None:
        raise HTTPException(status_code=404, detail="task not found")
    return success_response(data=status)


@router.get("/chat-history")
def get_chat_history(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
):
    return success_response(
        data=list_chat_history(owner_id=int(current_user.id), limit=limit)
    )


@router.delete("/chat-history/{history_id}")
def remove_chat_history(
    history_id: int,
    current_user: User = Depends(get_current_user),
):
    try:
        result = delete_chat_history(history_id, int(current_user.id))
        return success_response(message="chat history deleted", data=result)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.delete("/chat-history")
def remove_all_chat_history(current_user: User = Depends(get_current_user)):
    return success_response(
        message="chat history cleared",
        data=clear_chat_history(int(current_user.id)),
    )


@router.post("/agent-chat")
def agent_chat(
    request: AgentChatRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
):
    result = run_agent_chat(
        request=request,
        background_tasks=background_tasks,
        owner_id=int(current_user.id),
    )
    return success_response(data=result.model_dump())


@router.post("/feedback")
def submit_feedback(request: FeedbackCreateRequest):
    return success_response(message="feedback created", data=create_feedback(request))


@router.get("/feedback")
def get_feedback(
    limit: int = 100,
    current_user: User = Depends(require_admin),
):
    return success_response(data=list_feedback(limit=limit))


@router.delete("/feedback/{feedback_id}")
def remove_feedback(
    feedback_id: int,
    current_user: User = Depends(require_admin),
):
    try:
        result = delete_feedback(feedback_id)
        return success_response(message="feedback deleted", data=result)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

SESSION_EXPIRE_SECONDS = 60 * 60 * 24
@router.post("/auth/login")
def login(request: LoginRequest):
    with Session(engine) as session:
        user = session.exec(
            select(User).where(User.username == request.username)
        ).first()

        if user is None:
            raise HTTPException(
                status_code=401,
                detail="用户名或密码错误",
            )

        if not user.is_active:
            raise HTTPException(
                status_code=403,
                detail="账号已被禁用",
            )

        if not verify_password(request.password, user.password_hash):
            raise HTTPException(
                status_code=401,
                detail="用户名或密码错误",
            )

        # 生成原始 Token，只返回给前端一次
        raw_token = secrets.token_urlsafe(32)

        # 数据库只保存 Token 哈希
        token_hash = hashlib.sha256(
            raw_token.encode("utf-8")
        ).hexdigest()

        expires_at = datetime.utcnow() + timedelta(
            seconds=SESSION_EXPIRE_SECONDS
        )

        user_session = UserSession(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
        )

        session.add(user_session)
        session.commit()

        return success_response(
            message="登录成功",
            data={
                "access_token": raw_token,
                "token_type": "bearer",
                "expires_in": SESSION_EXPIRE_SECONDS,
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "role": user.role,
                },
            },
        )
