import hashlib
import hmac
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field
from construction_service.api.demo_access import (
    ACCESS_COOKIE, ACCESS_TTL, access_password, check_login_attempt,
    create_access_token, valid_access_token,
)

router = APIRouter(prefix="/api/access")


class LoginRequest(BaseModel):
    password: str = Field(min_length=1, max_length=128, repr=False)


@router.get("/session")
async def access_status(request: Request, response: Response) -> dict:
    response.headers["Cache-Control"] = "no-store"
    return {"authenticated": valid_access_token(request.cookies.get(ACCESS_COOKIE))}


@router.post("/login")
async def login(body: LoginRequest, request: Request, response: Response) -> dict:
    if request.headers.get("sec-fetch-site") == "cross-site":
        raise HTTPException(status_code=403, detail="不允许跨站登录。")
    check_login_attempt(request)
    provided = hashlib.sha256(body.password.encode()).digest()
    expected = hashlib.sha256(access_password().encode()).digest()
    if not hmac.compare_digest(provided, expected):
        raise HTTPException(status_code=401, detail="访问口令不正确。")
    response.headers["Cache-Control"] = "no-store"
    response.set_cookie(ACCESS_COOKIE, create_access_token(), max_age=ACCESS_TTL,
                        httponly=True, secure=request.url.scheme == "https", samesite="lax", path="/")
    return {"authenticated": True}
