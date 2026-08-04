from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile

from app.api.dependencies import require_admin
from app.models.user_model import User
from app.services.document_ingestion_service import run_document_ingestion_task
from app.services.document_service import (
    delete_document, delete_document_by_id, list_all_documents, list_documents,
    save_uploaded_document,
)
from app.services.feedback_service import delete_feedback, list_feedback
from app.services.index_task_service import run_rebuild_index_task
from app.services.task_service import (
    create_task_id,
    create_task_record,
    get_task_status,
)
from app.retrievers.vector_retriever import search_qdrant_index


admin_router = APIRouter(prefix="/admin", tags=["admin"])


def success_response(message: str = "success", data=None) -> dict:
    return {"code": 0, "message": message, "data": data}


@admin_router.get("/documents")
def get_admin_documents(
    current_user: User = Depends(require_admin),
):
    return success_response(data=list_documents(int(current_user.id)))


@admin_router.get("/all-documents")
def get_all_documents(current_user: User = Depends(require_admin)):
    return success_response(data=list_all_documents())


@admin_router.get("/retrieval-preview")
def retrieval_preview(
    question: str,
    top_k: int = 8,
    current_user: User = Depends(require_admin),
):
    normalized_question = question.strip()
    if not normalized_question:
        raise HTTPException(status_code=400, detail="问题不能为空")
    chunks = search_qdrant_index(
        query=normalized_question,
        owner_id=None,
        top_k=max(1, min(top_k, 20)),
    )
    return success_response(
        data={
            "question": normalized_question,
            "strategy": "Qdrant Dense + BM25 Sparse + RRF",
            "chunks": chunks,
        }
    )


@admin_router.delete("/all-documents/{document_id}")
def remove_any_document(
    document_id: int,
    current_user: User = Depends(require_admin),
):
    try:
        return success_response(
            message="文档删除成功", data=delete_document_by_id(document_id)
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@admin_router.post("/documents/upload")
async def upload_admin_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(require_admin),
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


@admin_router.delete("/documents/{document_name}")
def delete_admin_document(
    document_name: str,
    current_user: User = Depends(require_admin),
):
    try:
        return success_response(
            message="文档删除成功",
            data=delete_document(document_name, int(current_user.id)),
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@admin_router.post("/rebuild-index")
def rebuild_admin_index(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_admin),
):
    task_id = create_task_id()
    create_task_record(task_id=task_id, task_type="rebuild_index")
    background_tasks.add_task(run_rebuild_index_task, task_id)
    return success_response(
        message="索引重建任务已创建",
        data={"task_id": task_id, "status": "pending"},
    )


@admin_router.get("/task-status/{task_id}")
def get_admin_task_status(
    task_id: str,
    current_user: User = Depends(require_admin),
):
    status = get_task_status(task_id)
    if status is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return success_response(data=status)


@admin_router.get("/feedback")
def get_admin_feedback(
    limit: int = 100,
    current_user: User = Depends(require_admin),
):
    return success_response(data=list_feedback(limit=limit))


@admin_router.delete("/feedback/{feedback_id}")
def delete_admin_feedback(
    feedback_id: int,
    current_user: User = Depends(require_admin),
):
    try:
        return success_response(
            message="反馈删除成功",
            data=delete_feedback(feedback_id),
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
