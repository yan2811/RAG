"""
认证路由：用户注册、登录、个人信息管理、图形验证码
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token
from app.core.config import settings
from app.models.user import User
from app.models.role import Role, user_roles
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse, UserInfo
from app.middleware.auth import get_current_user, get_user_permissions, get_user_roles
from app.utils.captcha import generate_captcha, verify_captcha

router = APIRouter(prefix="/api/v1/auth", tags=["认证"])


@router.get("/captcha", summary="获取图形验证码")
def get_captcha():
    """
    生成图形验证码，返回 captcha_id 和 base64 编码的 PNG 图片
    验证码有效期 5 分钟，校验一次后立即失效
    """
    captcha_id, image_b64 = generate_captcha()
    return {"code": 0, "data": {"captcha_id": captcha_id, "image": image_b64}}


@router.post("/register", response_model=TokenResponse, summary="用户注册")
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    """
    用户注册接口：创建新用户账号，自动分配"普通用户"角色，返回 JWT Token
    """
    # 检查用户名是否已存在
    existing = db.query(User).filter(User.username == req.username).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在",
        )

    # 验证密码复杂度（字母+数字）
    if not (any(c.isalpha() for c in req.password) and any(c.isdigit() for c in req.password)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="密码必须同时包含字母和数字",
        )

    # 创建用户
    user = User(
        username=req.username,
        password_hash=hash_password(req.password),
        email=req.email,
    )
    db.add(user)
    db.flush()  # 刷新以获得 user.id

    # 分配默认角色（普通用户）
    default_role = db.query(Role).filter(Role.name == "user").first()
    if default_role:
        db.execute(user_roles.insert().values(user_id=user.id, role_id=default_role.id))

    db.commit()
    db.refresh(user)

    # 生成 JWT Token
    token = create_access_token(data={"user_id": user.id, "username": user.username})
    roles = get_user_roles(user, db)
    perms = get_user_permissions(user, db)

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=settings.JWT_EXPIRATION_HOURS * 3600,
        user=UserInfo(
            id=user.id,
            username=user.username,
            email=user.email,
            avatar=user.avatar,
            status=user.status,
            roles=roles,
            permissions=perms,
        ),
    )


@router.post("/login", response_model=TokenResponse, summary="用户登录")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    """
    用户登录接口：验证用户名密码，返回 JWT Token
    """
    # 查找用户
    user = db.query(User).filter(User.username == req.username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    # 检查账号状态
    if user.status == "disabled":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号已被禁用，请联系管理员",
        )

    # 验证密码
    if not verify_password(req.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    # 验证图形验证码
    if not verify_captcha(req.captcha_id or "", req.captcha_code or ""):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="验证码错误或已过期",
        )

    # 生成 Token
    token = create_access_token(data={"user_id": user.id, "username": user.username})
    roles = get_user_roles(user, db)
    perms = get_user_permissions(user, db)

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=settings.JWT_EXPIRATION_HOURS * 3600,
        user=UserInfo(
            id=user.id,
            username=user.username,
            email=user.email,
            avatar=user.avatar,
            status=user.status,
            roles=roles,
            permissions=perms,
        ),
    )


@router.get("/me", response_model=UserInfo, summary="获取当前用户信息")
def get_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    获取当前登录用户的基本信息、角色和权限
    需要在请求头中携带有效的 JWT Token
    """
    roles = get_user_roles(current_user, db)
    perms = get_user_permissions(current_user, db)
    return UserInfo(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        avatar=current_user.avatar,
        status=current_user.status,
        roles=roles,
        permissions=perms,
    )
