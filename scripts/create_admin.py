from getpass import getpass

from sqlmodel import Session, select

from app.db.database import engine, init_db
from app.models.user_model import User
from app.services.password_service import hash_password


def main() -> None:
    # 确保 user 表已经创建
    init_db()

    username = input("管理员用户名（默认 root）: ").strip() or "root"
    password = getpass("管理员密码: ")

    if not username or not password:
        raise ValueError("用户名和密码不能为空")

    with Session(engine) as session:
        existing_user = session.exec(
            select(User).where(User.username == username)
        ).first()

        if existing_user:
            existing_user.role = "admin"
            existing_user.is_active = True
            session.add(existing_user)
            session.commit()
            print(f"用户 {username} 已设置为管理员")
            return

        admin = User(
            username=username,
            password_hash=hash_password(password),
            role="admin",
            is_active=True,
        )

        session.add(admin)
        session.commit()
        print(f"管理员 {username} 创建成功")


if __name__ == "__main__":
    main()
