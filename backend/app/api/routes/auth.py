"""
Routes d'authentification.
- POST /auth/register : Inscription avec hash bcrypt
- POST /auth/login    : Login → JWT access + refresh token
- GET  /auth/me       : Profil utilisateur connecté
- POST /auth/refresh  : Renouvellement du token
- POST /auth/logout   : Révocation du refresh token
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
    decode_token,
)
from app.db.postgres import get_db
from app.db.redis_client import (
    delete_refresh_token,
    get_refresh_token,
    store_refresh_token,
)
from app.models.user import User
from app.api.dependencies import get_current_user

router = APIRouter()


# ── Schémas Pydantic ─────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str

    model_config = {"json_schema_extra": {"example": {"email": "user@example.com", "password": "SecurePass123!"}}}


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    email: str

    model_config = {"from_attributes": True}


# ── Routes ───────────────────────────────────────────────────

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un compte utilisateur",
)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """
    Crée un nouvel utilisateur avec mot de passe hashé (bcrypt).
    Retourne 409 si l'email est déjà utilisé.
    """
    # Vérifier si l'email existe déjà
    result = await db.execute(select(User).where(User.email == payload.email))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Un compte avec cet email existe déjà.",
        )

    # Créer l'utilisateur
    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Connexion → JWT token",
)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    """
    Authentifie l'utilisateur et retourne un JWT access token + refresh token.
    Le refresh token est stocké dans Redis.
    """
    # Chercher l'utilisateur
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    # Vérification credentials (même message d'erreur pour éviter l'énumération d'emails)
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Générer les tokens
    access_token = create_access_token(subject=user.id)
    refresh_token = create_refresh_token(subject=user.id)

    # Stocker le refresh token dans Redis
    await store_refresh_token(
        user_id=user.id,
        token=refresh_token,
        expire_seconds=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 86400,
    )

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Profil de l'utilisateur connecté",
)
async def get_me(current_user: User = Depends(get_current_user)):
    """Retourne les informations de l'utilisateur connecté."""
    return current_user


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Renouveler le token d'accès",
)
async def refresh_token(refresh_token: str, db: AsyncSession = Depends(get_db)):
    """
    Valide le refresh token et émet un nouveau access token.
    """
    payload = decode_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token invalide ou expiré.",
        )

    user_id = payload.get("sub")

    # Vérifier que le token correspond à celui stocké en Redis
    stored_token = await get_refresh_token(user_id)
    if stored_token != refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token révoqué.",
        )

    # Vérifier que l'utilisateur existe toujours
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Utilisateur introuvable.")

    # Générer de nouveaux tokens
    new_access = create_access_token(subject=user.id)
    new_refresh = create_refresh_token(subject=user.id)
    await store_refresh_token(
        user_id=user.id,
        token=new_refresh,
        expire_seconds=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 86400,
    )

    return TokenResponse(access_token=new_access, refresh_token=new_refresh)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Déconnexion (révocation du refresh token)",
)
async def logout(current_user: User = Depends(get_current_user)):
    """Révoque le refresh token de l'utilisateur (logout côté serveur)."""
    await delete_refresh_token(current_user.id)
