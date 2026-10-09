"""阿里云万相数字人(灵眸)会话客户端: 封装 CreateChatSession。

供前端 `lm-avatar-chat-sdk` 初始化云渲染数字人使用。
SDK 调用是阻塞的, 通过 `asyncio.to_thread` 包装成异步接口供 FastAPI 使用。

"""
from __future__ import annotations

import logging
import asyncio
import threading
import time
from typing import Any

try:
    from alibabacloud_lingmou20250527.client import Client as LingMouClient
    from alibabacloud_lingmou20250527 import models as lm_models
    from alibabacloud_tea_openapi import models as open_api_models
    from alibabacloud_tea_util import models as util_models
    LINGMOU_AVAILABLE = True
except ImportError:  # 未安装阿里云灵眸SDK时，自动禁用数字人功能（不影响核心客服对话）
    LingMouClient = None  # type: ignore
    lm_models = None  # type: ignore
    open_api_models = None  # type: ignore
    util_models = None  # type: ignore
    LINGMOU_AVAILABLE = False

from construction_service.config.settings import settings

logger = logging.getLogger(__name__)

_client: Any = None

# 单进程单访客租用；云端关闭成功后才允许转交给下一位访客。
_session: dict[str, Any] | None = None
_session_lock = threading.Lock()
_session_owner: str | None = None
_lease_deadline = 0.0
LEASE_TTL = 90


class AvatarBusyError(RuntimeError):
    pass


class AvatarOwnerError(RuntimeError):
    pass


class AvatarUnavailableError(RuntimeError):
    pass


def init_avatar_client() -> None:
    """在 FastAPI lifespan 中调用, 提前完成客户端初始化。"""
    global _client
    if not LINGMOU_AVAILABLE:
        logger.info("未安装阿里云灵眸SDK，跳过数字人初始化")
        return
    if _client is not None:
        return
    _client = _build_client()
    logger.info("Avatar client 初始化. endpoint=%s", settings.avatar_endpoint)


def _build_client() -> LingMouClient:
    config = open_api_models.Config(
        access_key_id=settings.avatar_access_key_id,
        access_key_secret=settings.avatar_access_key_secret,
    )
    config.endpoint = settings.avatar_endpoint
    return LingMouClient(config)


def _get_client() -> LingMouClient:
    global _client
    if _client is None:
        _client = _build_client()
    return _client


def _rtc_params_to_dict(rtc) -> dict[str, Any]:
    if rtc is None:
        return {}
    return {
        "appId": rtc.app_id,
        "channel": rtc.channel,
        "nonce": rtc.nonce,
        "timestamp": rtc.timestamp,
        "token": rtc.token,
        "gslb": rtc.gslb,
        "clientUserId": rtc.client_user_id,
        "serverUserId": rtc.server_user_id,
        "avatarUserId": rtc.avatar_user_id,
    }


def _do_create() -> dict[str, Any]:
    """对应官方 demo:
    client.create_chat_session_with_options(project_id, request, headers, runtime)
    project_id 是控制台项目主键(如 'C1rRS1KmS3WurHor8HXYlSkQ');
    request 里通常只填 instance_id, 其余 device_id 由调用方按需补。
    """
    client = _get_client()
    project_id = settings.avatar_project_id

    req = lm_models.CreateChatSessionRequest(instance_id= settings.avatar_instance_id)

    resp = client.create_chat_session_with_options(
        project_id, req, {}, util_models.RuntimeOptions()
    )
    data = getattr(resp.body, "data", None)
    if data is None:
       return {}
    return {
        "sessionId": data.session_id,
        "rtcParams": _rtc_params_to_dict(data.rtc_params),
    }


def _clear_locked() -> bool:
    global _session, _session_owner, _lease_deadline
    if _session and _session.get("sessionId"):
        _close_session_ids([_session["sessionId"]])
    existed = _session is not None
    _session = None
    _session_owner = None
    _lease_deadline = 0.0
    return existed


def _create_chat_session_sync(owner: str) -> dict[str, Any]:
    global _session, _session_owner, _lease_deadline
    with _session_lock:
        if _session is not None and time.monotonic() >= _lease_deadline:
            _clear_locked()
        if _session is not None:
            if _session_owner != owner:
                raise AvatarBusyError("数字人正在被另一位访客使用")
            _lease_deadline = time.monotonic() + LEASE_TTL
            return _session
        created = _do_create()
        if not created.get("sessionId"):
            raise AvatarUnavailableError("数字人服务不可用")
        _session = created
        _session_owner = owner
        _lease_deadline = time.monotonic() + LEASE_TTL
        return _session


async def create_chat_session(owner: str) -> dict[str, Any]:
    if not LINGMOU_AVAILABLE:
        raise AvatarUnavailableError("当前未启用数字人服务")
    return await asyncio.to_thread(_create_chat_session_sync, owner)


def _close_session_ids(session_ids: list[str]) -> int:
    """调用灵眸 CloseChatInstanceSessions 关闭一批会话, 返回成功提交的数量。"""
    if not session_ids:
        return 0
    instance_id = settings.avatar_instance_id

    client = _get_client()

    req = lm_models.CloseChatInstanceSessionsRequest(session_ids=session_ids)
    client.close_chat_instance_sessions_with_options(
        instance_id, req, {}, util_models.RuntimeOptions()
    )
    return len(session_ids)


def _stop_chat_session_sync(owner: str) -> bool:
    with _session_lock:
        if _session is None:
            return False
        if _session_owner != owner:
            raise AvatarOwnerError("不能释放其他访客的数字人会话")
        return _clear_locked()


async def stop_chat_session(owner: str) -> bool:
    if not LINGMOU_AVAILABLE:
        return False
    return await asyncio.to_thread(_stop_chat_session_sync, owner)


def _heartbeat_sync(owner: str) -> bool:
    global _lease_deadline
    with _session_lock:
        if _session is None or _session_owner != owner:
            raise AvatarOwnerError("数字人会话已释放或属于其他访客")
        if time.monotonic() >= _lease_deadline:
            _clear_locked()
            raise AvatarOwnerError("数字人会话已过期")
        _lease_deadline = time.monotonic() + LEASE_TTL
        return True


async def heartbeat(owner: str) -> bool:
    return await asyncio.to_thread(_heartbeat_sync, owner)


def _expire_sync() -> None:
    with _session_lock:
        if _session is not None and time.monotonic() >= _lease_deadline:
            _clear_locked()


async def expire_chat_session() -> None:
    await asyncio.to_thread(_expire_sync)


def _shutdown_sync() -> None:
    with _session_lock:
        _clear_locked()


async def shutdown_chat_session() -> None:
    await asyncio.to_thread(_shutdown_sync)
