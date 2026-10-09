"""数字人云渲染相关 HTTP 路由。"""
from fastapi import APIRouter, HTTPException, Response
from construction_service.api.visitor_session import VisitorSessionDep, check_sender_id

from construction_service.api.schemas import AvatarSessionResponse
from construction_service.infrastructure import avatar

router = APIRouter()


@router.get("/api/avatar/session")
async def create_avatar_session(
    response: Response, visitor: VisitorSessionDep, sender_id: str | None = None,
) -> AvatarSessionResponse:
    """创建数字人云渲染会话, 给前端 SDK 初始化。"""
    check_sender_id(sender_id, visitor)
    response.headers["Cache-Control"] = "no-store"
    try:
        data = await avatar.create_chat_session(visitor)
    except avatar.AvatarBusyError:
        raise HTTPException(status_code=409, detail="数字人使用中，文字聊天仍可使用。") from None
    except avatar.AvatarUnavailableError:
        raise HTTPException(status_code=503, detail="当前数字人不可用，请使用文字聊天。") from None
    except Exception:
        raise HTTPException(status_code=502, detail="数字人连接暂时失败，请稍后重试。") from None
    return AvatarSessionResponse(**data)


@router.delete("/api/avatar/session")
async def release_avatar_session(visitor: VisitorSessionDep, sender_id: str | None = None) -> dict:
    """释放当前数字人会话, 归还并发位。"""
    check_sender_id(sender_id, visitor)
    try:
        released = await avatar.stop_chat_session(visitor)
    except avatar.AvatarOwnerError:
        raise HTTPException(status_code=403, detail="不能释放其他访客的数字人会话。") from None
    except Exception:
        raise HTTPException(status_code=502, detail="数字人释放失败，请稍后重试。") from None
    return {"released": released}


@router.post("/api/avatar/session/heartbeat")
async def avatar_heartbeat(visitor: VisitorSessionDep) -> dict:
    try:
        return {"active": await avatar.heartbeat(visitor)}
    except avatar.AvatarOwnerError:
        raise HTTPException(status_code=409, detail="数字人会话已结束，请重新启用。") from None
    except Exception:
        raise HTTPException(status_code=502, detail="数字人服务暂时不可用。") from None
