"""公网演示业务网关：限定演示用户和最近列表中的对象，禁止业务写操作。"""
from fastapi import APIRouter, HTTPException, Response
from construction_service.api.visitor_session import DEMO_USER_ID, VisitorSessionDep
from construction_service.services.demo_commerce_service import DemoObjectDenied, fetch_demo_list, fetch_demo_object

router = APIRouter(prefix="/commerce")


async def _read(operation) -> dict:
    try:
        return await operation
    except DemoObjectDenied:
        raise HTTPException(status_code=403, detail="只能访问当前演示列表中的对象。") from None
    except Exception:
        raise HTTPException(status_code=502, detail="演示业务服务暂时不可用，请稍后重试。") from None


@router.get("/users/{user_id}/{kind}")
async def user_objects(user_id: str, kind: str, visitor: VisitorSessionDep, response: Response):
    response.headers["Cache-Control"] = "no-store"
    if user_id != DEMO_USER_ID or kind not in {"orders", "products"}:
        raise HTTPException(status_code=403, detail="只能访问指定演示用户的订单和商品。")
    return await _read(fetch_demo_list(kind))


@router.get("/orders/{object_id}")
@router.get("/orders/{object_id}/{section}")
async def order_info(object_id: str, visitor: VisitorSessionDep, response: Response, section: str | None = None):
    response.headers["Cache-Control"] = "no-store"
    if section not in {None, "status", "logistics"}:
        raise HTTPException(status_code=404, detail="演示接口不存在。")
    return await _read(fetch_demo_object("orders", object_id, section))


@router.get("/products/{object_id}")
async def product_info(object_id: str, visitor: VisitorSessionDep, response: Response):
    response.headers["Cache-Control"] = "no-store"
    return await _read(fetch_demo_object("products", object_id))


@router.api_route("/{path:path}", methods=["POST", "PUT", "PATCH", "DELETE"])
async def deny_business_write(path: str, visitor: VisitorSessionDep):
    raise HTTPException(status_code=403, detail="演示模式不执行退款、催发货或其他业务写操作。")
