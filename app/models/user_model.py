from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    __tablename__ = "user"

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True, max_length=64)
    password_hash: str = Field(max_length=255)
    role: str = Field(default="user", max_length=32)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)