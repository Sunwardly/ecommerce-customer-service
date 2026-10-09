"""使用服务端签名的 HttpOnly Cookie 绑定访客对话，避免客户端冒充 sender_id。"""
import hashlib
import hmac
import os
import secrets
import time
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from construction_service.config.demo import DEMO_USER_ID

COOKIE_NAME = "ecs_visitor_session"
SESSION_TTL = 30 * 24 * 60 * 60


@lru_cache(maxsize=1)
def _signing_key() -> bytes:
    # 密钥保存在当前 Windows 用户的应用数据目录，不进入项目或 .env。
    base = Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local" / "share"))
    path = base / "ecommerce-customer-service" / "visitor-session.key"
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as file:
            file.write(secrets.token_bytes(32))
    except FileExistsError:
        pass
    key = path.read_bytes()
    if len(key) != 32:
        raise RuntimeError("访客会话签名密钥文件无效")
    return key


def create_session_token() -> tuple[str, str]:
    sender_id = "v_" + secrets.token_hex(16)
    unsigned = f"{sender_id}.{int(time.time()) + SESSION_TTL}"
    signature = hmac.new(_signing_key(), unsigned.encode(), hashlib.sha256).hexdigest()
    return sender_id, f"{unsigned}.{signature}"


def read_session_token(token: str | None) -> str | None:
    if not token or len(token) > 160:
        return None
    try:
        sender_id, expires, signature = token.split(".")
        if len(sender_id) != 34 or not sender_id.startswith("v_"):
            return None
        int(sender_id[2:], 16)
        if int(expires) <= time.time():
            return None
        unsigned = f"{sender_id}.{expires}"
        expected = hmac.new(_signing_key(), unsigned.encode(), hashlib.sha256).hexdigest()
        return sender_id if hmac.compare_digest(signature, expected) else None
    except (ValueError, TypeError):
        return None


def require_visitor(request: Request) -> str:
    from construction_service.api.demo_access import require_access
    require_access(request)
    sender_id = read_session_token(request.cookies.get(COOKIE_NAME))
    if sender_id is None:
        raise HTTPException(status_code=401, detail="访客会话已失效，请刷新页面。")
    return sender_id


def check_sender_id(provided: str | None, sender_id: str) -> None:
    if provided is not None and provided != sender_id:
        raise HTTPException(status_code=403, detail="不能访问其他访客的对话，请刷新页面同步当前会话。")


VisitorSessionDep = Annotated[str, Depends(require_visitor)]
