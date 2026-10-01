from datetime import timedelta
import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import ACCESS_COOKIE, CSRF_COOKIE, REFRESH_COOKIE, get_current_user, require_csrf
from app.config import settings
from app.database import get_db
from app.models import Doctor, Patient, User
from app.schemas.auth import AuthResponse, LoginRequest, RegisterRequest, UserOut
from app.services.serializers import user_data
from app.utils.security import create_token, hash_password, hash_refresh_token, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


def set_auth_cookies(response: Response, user: User, refresh_token: str) -> None:
    access_token = create_token(
        str(user.id), "access", timedelta(minutes=settings.access_token_expire_minutes)
    )
    response.set_cookie(
        ACCESS_COOKIE,
        access_token,
        max_age=settings.access_token_expire_minutes * 60,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
        domain=settings.cookie_domain,
    )
    response.set_cookie(
        REFRESH_COOKIE,
        refresh_token,
        max_age=settings.refresh_token_expire_days * 86400,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/auth",
        domain=settings.cookie_domain,
    )
    response.set_cookie(
        CSRF_COOKIE,
        secrets.token_urlsafe(32),
        max_age=settings.refresh_token_expire_days * 86400,
        httponly=False,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
        domain=settings.cookie_domain,
    )


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)):
    if payload.role == "doctor" and not settings.allow_doctor_registration:
        raise HTTPException(status_code=403, detail="Doctor registration is closed")
    email = payload.email.strip().lower()
    existing = await db.scalar(select(User.id).where(User.email == email))
    if existing:
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    user = User(email=email, hashed_password=hash_password(payload.password), role=payload.role)
    if payload.role == "patient":
        profile = Patient(
            public_id=f"PT-{uuid.uuid4().hex[:8].upper()}",
            name=payload.name,
            date_of_birth=payload.date_of_birth,
            sex=payload.sex,
            blood_group=payload.blood_group,
            height_cm=payload.height_cm,
            weight_kg=payload.weight_kg,
            phone=payload.phone,
            email=email,
            user=user,
        )
        if profile.date_of_birth is None:
            from datetime import date

            profile.date_of_birth = date.today()
    else:
        user.doctor = Doctor(
            public_id=f"DR-{uuid.uuid4().hex[:8].upper()}",
            name=payload.name,
            specialty=payload.specialty,
            license_number=payload.license,
            phone=payload.phone,
            email=email,
            clinic=payload.clinic,
            working_days=payload.working_days,
            user=user,
        )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    loaded = await db.scalar(
        select(User)
        .options(selectinload(User.patient), selectinload(User.doctor))
        .where(User.id == user.id)
    )
    return UserOut.model_validate(user_data(loaded))


@router.post("/login", response_model=AuthResponse)
async def login(payload: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    user = await db.scalar(
        select(User)
        .options(selectinload(User.patient), selectinload(User.doctor))
        .where(User.email == payload.email.strip().lower())
    )
    if user is None or not user.is_active or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    refresh_token = create_token(
        str(user.id), "refresh", timedelta(days=settings.refresh_token_expire_days)
    )
    user.refresh_token_hash = hash_refresh_token(refresh_token)
    await db.commit()
    set_auth_cookies(response, user, refresh_token)
    return AuthResponse(user=UserOut.model_validate(user_data(user)))


@router.post("/refresh", response_model=AuthResponse, dependencies=[Depends(require_csrf)])
async def refresh(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    token = request.cookies.get(REFRESH_COOKIE)
    if not token:
        raise HTTPException(status_code=401, detail="Refresh token required")
    try:
        from jose import JWTError, jwt

        claims = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        if claims.get("type") != "refresh":
            raise JWTError("Invalid token type")
        user_id = uuid.UUID(claims["sub"])
    except (JWTError, ValueError, KeyError):
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token") from None
    user = await db.scalar(
        select(User)
        .options(selectinload(User.patient), selectinload(User.doctor))
        .where(User.id == user_id)
    )
    if user is None or not user.is_active or not user.refresh_token_hash:
        raise HTTPException(status_code=401, detail="Refresh token revoked")
    if not secrets.compare_digest(user.refresh_token_hash, hash_refresh_token(token)):
        raise HTTPException(status_code=401, detail="Refresh token has already been rotated")
    rotated_token = create_token(
        str(user.id), "refresh", timedelta(days=settings.refresh_token_expire_days)
    )
    rotation = await db.execute(
        update(User)
        .where(
            User.id == user.id,
            User.is_active.is_(True),
            User.refresh_token_hash == hash_refresh_token(token),
        )
        .values(refresh_token_hash=hash_refresh_token(rotated_token))
    )
    if rotation.rowcount != 1:
        await db.rollback()
        raise HTTPException(status_code=401, detail="Refresh token has already been rotated")
    await db.commit()
    set_auth_cookies(response, user, rotated_token)
    return AuthResponse(user=UserOut.model_validate(user_data(user)), message="Tokens refreshed")


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
    db: AsyncSession = Depends(get_db),
):
    user.refresh_token_hash = None
    await db.commit()
    response.delete_cookie(ACCESS_COOKIE, path="/", domain=settings.cookie_domain, secure=settings.cookie_secure, httponly=True, samesite="lax")
    response.delete_cookie(REFRESH_COOKIE, path="/auth", domain=settings.cookie_domain, secure=settings.cookie_secure, httponly=True, samesite="lax")
    response.delete_cookie(CSRF_COOKIE, path="/", domain=settings.cookie_domain, secure=settings.cookie_secure, samesite="lax")


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    return UserOut.model_validate(user_data(user))
