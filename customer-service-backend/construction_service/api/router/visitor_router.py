"""建立或更新当前浏览器的访客聊天会话。"""
from fastapi import APIRouter, HTTPException, Request, Response
from construction_service.api.demo_access import require_access

from construction_service.api.visitor_session import (
    COOKIE_NAME, DEMO_USER_ID, SESSION_TTL, VisitorSessionDep,
    create_session_token, read_session_token,
)

router = APIRouter(prefix="/api/visitor")


def _new_session(request: Request, response: Response) -> dict:
    sender_id, token = create_session_token()
    response.set_cookie(
        COOKIE_NAME, token, max_age=SESSION_TTL, httponly=True,
        secure=request.url.scheme == "https", samesite="lax", path="/",
    )
    return {"sender_id": sender_id, "demo_user_id": DEMO_USER_ID}


@router.get("/session")
async def get_session(request: Request, response: Response) -> dict:
    require_access(request)
    response.headers["Cache-Control"] = "no-store"
    # 跨站页面不能通过图片等嵌入形式替换访客身份。
    if request.headers.get("sec-fetch-site") == "cross-site":
        raise HTTPException(status_code=403, detail="不允许跨站建立访客会话。")
    sender_id = read_session_token(request.cookies.get(COOKIE_NAME))
    if sender_id:
        return {"sender_id": sender_id, "demo_user_id": DEMO_USER_ID}
    return _new_session(request, response)


@router.post("/session")
async def start_new_session(request: Request, response: Response, visitor: VisitorSessionDep) -> dict:
    response.headers["Cache-Control"] = "no-store"
    if request.headers.get("sec-fetch-site") == "cross-site":
        raise HTTPException(status_code=403, detail="不允许跨站更新访客会话。")
    # 保留旧数据，只将当前浏览器绑定到新对话。
    return _new_session(request, response)
