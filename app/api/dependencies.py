import hashlib
from datetime import datetime

from fastapi import Depends, HTTPException
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
from sqlmodel import Session, select

from app.db.database import engine
from app.models.session_model import UserSession
from app.models.user_model import User


bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        bearer_scheme
    ),
) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="请先登录",
            headers={"WWW-Authenticate": "Bearer"},
        )

    raw_token = credentials.credentials
    token_hash = hashlib.sha256(
        raw_token.encode("utf-8")
    ).hexdigest()

    with Session(engine) as session:
        user_session = session.exec(
            select(UserSession).where(
                UserSession.token_hash == token_hash
            )
        ).first()

        if user_session is None:
            raise HTTPException(
                status_code=401,
                detail="登录凭证无效",
            )

        if user_session.revoked_at is not None:
            raise HTTPException(
                status_code=401,
                detail="登录凭证已注销",
            )

        if user_session.expires_at <= datetime.utcnow():
            raise HTTPException(
                status_code=401,
                detail="登录凭证已过期",
            )

        user = session.exec(
            select(User).where(User.id == user_session.user_id)
        ).first()

        if user is None or not user.is_active:
            raise HTTPException(
                status_code=401,
                detail="用户不存在或已被禁用",
            )

        return user


def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="只有管理员可以执行此操作",
        )

    return current_user