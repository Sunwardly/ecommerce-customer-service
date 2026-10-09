"""演示入口口令与短期访问许可；真实口令只保存在本机应用数据目录。"""
import hashlib
import hmac
import os
import secrets
import time
from collections import defaultdict, deque
from functools import lru_cache
from pathlib import Path

from fastapi import HTTPException, Request
from construction_service.api.visitor_session import _signing_key
from construction_service.config.demo import DEMO_ACCESS_REQUIRED

ACCESS_COOKIE = "ecs_demo_access"
ACCESS_TTL = 8 * 60 * 60
_attempts: dict[str, deque] = defaultdict(deque)


@lru_cache(maxsize=1)
def access_password() -> str:
    base = Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local" / "share"))
    path = base / "ecommerce-customer-service" / "demo-access-password.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8") as file:
            file.write(secrets.token_urlsafe(18))
    except FileExistsError:
        pass
    value = path.read_text(encoding="utf-8").strip()
    if len(value) < 12 or len(value) > 128:
        raise RuntimeError("演示口令文件长度必须为 12 至 128 个字符")
    return value


def _signature(unsigned: str) -> str:
    # 修改口令并重启后，旧的访问许可也随之失效。
    password_hash = hashlib.sha256(access_password().encode()).hexdigest()
    return hmac.new(_signing_key(), f"demo-access:{password_hash}:{unsigned}".encode(), hashlib.sha256).hexdigest()


def create_access_token() -> str:
    unsigned = f"{secrets.token_hex(16)}.{int(time.time()) + ACCESS_TTL}"
    return f"{unsigned}.{_signature(unsigned)}"


def valid_access_token(token: str | None) -> bool:
    # 当前阶段取消口令准入；HTTP 与 WebSocket 共用此策略。
    if not DEMO_ACCESS_REQUIRED:
        return True
    if not token or len(token) > 160:
        return False
    try:
        nonce, expires, signature = token.split(".")
        if len(nonce) != 32 or int(expires) <= time.time():
            return False
        int(nonce, 16)
        return hmac.compare_digest(signature, _signature(f"{nonce}.{expires}"))
    except (ValueError, TypeError):
        return False


def require_access(request: Request) -> None:
    if not valid_access_token(request.cookies.get(ACCESS_COOKIE)):
        raise HTTPException(status_code=401, detail="请先输入访问口令。")


def check_login_attempt(request: Request) -> None:
    now = time.monotonic()
    # Uvicorn 仅信任本机代理转发的客户端地址，不读取用户自报的身份。
    address = request.client.host if request.client else "unknown"
    for key in list(_attempts):
        if not _attempts[key] or now - _attempts[key][-1] >= 60:
            del _attempts[key]
    attempts = _attempts[address]
    while attempts and now - attempts[0] >= 60:
        attempts.popleft()
    if len(attempts) >= 10:
        raise HTTPException(status_code=429, detail="尝试次数过多，请一分钟后重试。")
    attempts.append(now)
