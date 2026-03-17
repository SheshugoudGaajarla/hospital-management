from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.user import User, UserRole


class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_username(self, username: str) -> User | None:
        statement = select(User).where(User.username == username)
        return self.db.execute(statement).scalar_one_or_none()

    def get_by_id(self, user_id: int) -> User | None:
        statement = select(User).where(User.id == user_id)
        return self.db.execute(statement).scalar_one_or_none()

    def count_users(self) -> int:
        statement = select(func.count(User.id))
        return int(self.db.execute(statement).scalar_one())

    def create_user(
        self,
        username: str,
        full_name: str,
        role: UserRole,
        password_hash: str,
    ) -> User:
        user = User(
            username=username,
            full_name=full_name,
            role=role,
            password_hash=password_hash,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
