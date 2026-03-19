from datetime import UTC, datetime

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.refresh_token import RefreshToken
from app.models.role import Role
from app.models.user import User


class AuthRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def find_user_for_login(self, username_or_email: str) -> User | None:
        stmt = (
            select(User)
            .options(
                joinedload(User.roles).joinedload(Role.permissions),
                joinedload(User.direct_permissions),
            )
            .where(or_(User.username == username_or_email, User.email == username_or_email), User.is_active.is_(True))
        )
        return self.db.execute(stmt).unique().scalar_one_or_none()

    def get_user_by_id(self, user_id: str) -> User | None:
        stmt = (
            select(User)
            .options(
                joinedload(User.roles).joinedload(Role.permissions),
                joinedload(User.direct_permissions),
            )
            .where(User.id == user_id, User.is_active.is_(True))
        )
        return self.db.execute(stmt).unique().scalar_one_or_none()

    def create_refresh_token(self, refresh_token: RefreshToken) -> RefreshToken:
        self.db.add(refresh_token)
        self.db.flush()
        return refresh_token

    def find_valid_refresh_token(self, token_hash: str) -> RefreshToken | None:
        stmt = (
            select(RefreshToken)
            .options(
                joinedload(RefreshToken.user).joinedload(User.roles).joinedload(Role.permissions),
                joinedload(RefreshToken.user).joinedload(User.direct_permissions),
            )
            .where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked_at.is_(None),
                RefreshToken.expires_at > datetime.now(UTC),
                RefreshToken.is_active.is_(True),
            )
        )
        return self.db.execute(stmt).unique().scalar_one_or_none()

    def revoke_refresh_token(self, token: RefreshToken) -> None:
        token.revoked_at = datetime.now(UTC)
        self.db.flush()

    def revoke_session(self, session_id: str) -> None:
        stmt = select(RefreshToken).where(RefreshToken.session_id == session_id, RefreshToken.revoked_at.is_(None))
        for token in self.db.scalars(stmt):
            token.revoked_at = datetime.now(UTC)
        self.db.flush()
