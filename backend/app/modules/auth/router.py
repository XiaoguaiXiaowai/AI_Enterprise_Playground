from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from starlette.responses import Response

from app.config.settings import get_settings
from app.core.database import get_db
from app.models.auth import User
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.schemas import LoginRequest, RefreshRequest, RegisterRequest, TokenResponse, UserMeResponse
from app.modules.auth.service import authenticate_user, create_user_with_password, get_or_create_github_user, issue_tokens, rotate_refresh_token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    try:
        user = create_user_with_password(db, email=payload.email, password=payload.password)
    except ValueError as e:
        if str(e) == "email_exists":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="email_exists")
        raise

    access_token, refresh_token = issue_tokens(db, user=user)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = authenticate_user(db, email=payload.email, password=payload.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_credentials")
    access_token, refresh_token = issue_tokens(db, user=user)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> TokenResponse:
    try:
        access_token, refresh_token = rotate_refresh_token(db, refresh_token=payload.refresh_token)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_refresh_token")
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.get("/me", response_model=UserMeResponse)
def me(user: User = Depends(get_current_user)) -> UserMeResponse:
    roles = [r.name for r in user.roles]
    return UserMeResponse(id=user.id, email=user.email, roles=roles)


@router.get("/github/login")
async def github_login(request: Request) -> Response:
    settings = get_settings()
    if not settings.github_client_id or not settings.github_client_secret:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="github_oauth_not_configured")
    oauth = request.app.state.oauth
    return await oauth.github.authorize_redirect(request, settings.github_redirect_uri)


@router.get("/github/callback", response_model=TokenResponse)
async def github_callback(request: Request, db: Session = Depends(get_db)) -> TokenResponse:
    oauth = request.app.state.oauth
    token = await oauth.github.authorize_access_token(request)
    user_resp = await oauth.github.get("user", token=token)
    user_json = user_resp.json()

    emails_resp = await oauth.github.get("user/emails", token=token)
    email_value = None
    if emails_resp.status_code == 200:
        emails_json = emails_resp.json()
        for e in emails_json:
            if e.get("primary") and e.get("verified") and e.get("email"):
                email_value = e["email"]
                break
        if not email_value and emails_json:
            email_value = emails_json[0].get("email")

    user = get_or_create_github_user(
        db,
        github_id=str(user_json.get("id")),
        github_login=str(user_json.get("login") or ""),
        email=email_value,
    )
    access_token, refresh_token = issue_tokens(db, user=user)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)
