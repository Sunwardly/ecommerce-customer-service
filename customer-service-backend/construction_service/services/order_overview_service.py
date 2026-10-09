"""订单卡片的即时详情说明；只采用服务端演示业务数据，不调用 LLM。"""
from decimal import Decimal, InvalidOperation

import httpx

from construction_service.services.demo_commerce_service import DemoObjectDenied, fetch_demo_object


def _time_text(value) -> str:
    return str(value).replace('T', ' ') if value else '未提供'


def _money(value) -> str:
    try:
        amount = Decimal(str(value))
        return f'¥{amount:.2f}' if amount.is_finite() else '未提供'
    except (InvalidOperation, ValueError):
        return '未提供'


async def describe_order(order_id: str) -> tuple[str, bool]:
    try:
        order = (await fetch_demo_object('orders', order_id)).get('data')
        if not isinstance(order, dict) or order.get('order_id') != order_id:
            raise ValueError('Invalid order response')
    except DemoObjectDenied:
        return '这笔订单不在当前演示列表中，无法查询。请从右侧订单列表选择订单发送。', False
    except Exception:
        return '订单详情暂时查询失败，请稍后重新发送订单重试。', False

    lines = [f'已查询到这笔订单的当前详情（演示数据）：',
             f'订单号：{order_id}',
             f'当前状态：{order.get("status") or "未提供"}']
    if order.get('status_desc'):
        lines.append(f'状态说明：{order["status_desc"]}')
    items = order.get('items') or []
    if items:
        lines.append('商品明细：')
        for item in items:
            lines.append(f'• {item.get("title") or "未提供商品名称"} × {item.get("quantity", "未提供")}（单价 {_money(item.get("price"))}）')
    else:
        lines.append('商品明细：暂未提供')
    lines.extend([f'订单金额：{_money(order.get("amount"))}',
                  f'下单时间：{_time_text(order.get("created_at"))}'])

    try:
        logistics = (await fetch_demo_object('orders', order_id, 'logistics')).get('data')
        if not isinstance(logistics, dict) or logistics.get('order_id') != order_id:
            raise ValueError('Invalid logistics response')
        lines.append(f'物流状态：{logistics.get("status_desc") or logistics.get("status") or "未提供"}')
        if logistics.get('logistics_company'):
            lines.append(f'物流公司：{logistics["logistics_company"]}')
        if logistics.get('tracking_number'):
            lines.append(f'运单号：{logistics["tracking_number"]}')
        traces = logistics.get('traces') or []
        if traces:
            latest = max(traces, key=lambda trace: str(trace.get('time') or ''))
            lines.append(f'最新物流：{_time_text(latest.get("time"))}，{latest.get("desc") or "未提供轨迹说明"}')
        else:
            lines.append('最新物流：暂未提供物流轨迹')
    except httpx.HTTPStatusError as error:
        lines.append('物流信息：暂无物流记录' if error.response.status_code == 404 else '物流信息：暂时查询失败，请稍后重试')
    except Exception:
        lines.append('物流信息：暂时查询失败，请稍后重试')
    lines.append('你可以继续询问这笔订单的状态、物流或售后问题。')
    return '\n'.join(lines), True
