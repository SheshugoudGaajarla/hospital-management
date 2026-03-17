from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.metrics import metrics_store
from app.core.rate_limit import get_client_ip, limit_by_ip, rate_limiter
from app.core.security import (
    create_access_token,
    get_current_user,
    hash_password,
    require_roles,
    verify_password,
)
from app.db.session import get_db
from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository
from app.schemas.auth import BootstrapAdminRequest, LoginRequest, MeResponse, TokenResponse, UserCreateRequest

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post(
    "/bootstrap-admin",
    response_model=MeResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(
            limit_by_ip(
                scope="auth_bootstrap",
                limit=settings.rate_limit_bootstrap_per_hour,
                window_seconds=3600,
            )
        )
    ],
)
def bootstrap_admin(payload: BootstrapAdminRequest, db: Session = Depends(get_db)) -> MeResponse:
    user_repo = UserRepository(db)
    if user_repo.count_users() > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bootstrap is disabled after initial user creation",
        )

    user = user_repo.create_user(
        username=payload.username,
        full_name=payload.full_name,
        role=UserRole.ADMIN,
        password_hash=hash_password(payload.password),
    )
    return MeResponse(
        id=user.id,
        username=user.username,
        full_name=user.full_name,
        role=user.role.value,
    )


@router.post(
    "/login",
    response_model=TokenResponse,
)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)) -> TokenResponse:
    username = payload.username.strip().lower()
    ip = get_client_ip(request)
    key = f"auth_login_failed:{ip}:{username}"
    failed_count = rate_limiter.count(key, window_seconds=60)
    if settings.rate_limit_enabled and failed_count >= settings.rate_limit_login_per_minute:
        retry_after = rate_limiter.retry_after(key, window_seconds=60)
        metrics_store.record_auth_rate_limited("auth_login")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded for auth_login. Retry after {retry_after} seconds",
            headers={"Retry-After": str(retry_after)},
        )

    user_repo = UserRepository(db)
    user = user_repo.get_by_username(payload.username)
    if user is None or not verify_password(payload.password, user.password_hash):
        if settings.rate_limit_enabled:
            rate_limiter.add_event(key)
        metrics_store.record_auth_failure("invalid_credentials")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    rate_limiter.clear_key(key)
    return TokenResponse(
        access_token=create_access_token(subject=user.username),
        token_type="bearer",
        role=user.role.value,
    )


@router.get("/me", response_model=MeResponse)
def me(current_user: User = Depends(get_current_user)) -> MeResponse:
    return MeResponse(
        id=current_user.id,
        username=current_user.username,
        full_name=current_user.full_name,
        role=current_user.role.value,
    )


@router.get("/admin-only")
def admin_only(_: User = Depends(require_roles(UserRole.ADMIN))) -> dict[str, str]:
    return {"message": "Admin access granted"}


@router.get("/users", response_model=list[MeResponse])
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
) -> list[MeResponse]:
    users = db.query(User).order_by(User.created_at.desc()).all()
    return [
        MeResponse(id=user.id, username=user.username, full_name=user.full_name, role=user.role.value)
        for user in users
    ]


@router.post("/users", response_model=MeResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
) -> MeResponse:
    user_repo = UserRepository(db)
    normalized_username = payload.username.strip().lower()
    if user_repo.get_by_username(normalized_username) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")
    try:
        role = UserRole(payload.role.strip().lower())
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role") from exc
    user = user_repo.create_user(
        username=normalized_username,
        full_name=payload.full_name.strip(),
        role=role,
        password_hash=hash_password(payload.password),
    )
    return MeResponse(
        id=user.id,
        username=user.username,
        full_name=user.full_name,
        role=user.role.value,
    )
