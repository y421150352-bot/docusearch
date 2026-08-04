from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class UserSession(SQLModel, table=True):
    __tablename__ = "user_session"

    id: Optional[int] = Field(default=None, primary_key=True)

    user_id: int = Field(
        foreign_key="user.id",
        index=True,
        nullable=False,
    )

    # 只保存 Token 的 SHA-256，不保存原始 Token
    token_hash: str = Field(
        index=True,
        unique=True,
        max_length=64,
    )

    expires_at: datetime = Field(
        index=True,
        nullable=False,
    )

    revoked_at: Optional[datetime] = Field(
        default=None,
        nullable=True,
    )

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        nullable=False,
    )