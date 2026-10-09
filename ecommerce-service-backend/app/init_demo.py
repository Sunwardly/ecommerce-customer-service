"""Create missing business tables and optionally add synthetic demo data."""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session

from app.models import Base, LogisticsRecord, LogisticsTrace, Order, OrderItem, Product, User


def seed_demo(session: Session) -> int:
    """Insert missing demo orders only; never update existing rows or delete data."""
    user = session.scalar(select(User).where(User.user_id == "u1001"))
    now = datetime(2026, 1, 1, 12)
    if user is None:
        user = User(user_id="u1001", nickname="演示用户", level="demo",
                    mobile_masked="不使用真实手机号", created_at=now)
        session.add(user)
        session.flush()
    inserted = 0
    for index, (status, title, price) in enumerate([
        ("待发货", "演示手机", "999.00"),
        ("待揽收", "演示耳机", "199.00"),
        ("运输中", "演示水壶", "149.00"),
        ("已完成", "演示背包", "89.00"),
        ("已取消", "演示台灯", "59.00"),
    ], start=1):
        order_id, product_id = f"DEMO-ORDER-{index:03d}", f"DEMO-PRODUCT-{index:03d}"
        existing = session.scalar(select(Order).where(Order.order_id == order_id))
        if existing is not None:
            if existing.user_id != user.id:
                raise ValueError("Demo order identifier belongs to another user; transaction cancelled.")
            continue
        product = session.scalar(select(Product).where(Product.product_id == product_id))
        if product is None:
            product = Product(product_id=product_id, title=title, description="纯虚构演示数据，不代表真实商品。",
                              price=Decimal(price), stock_status="有货", cover_url=None,
                              attributes_json={"用途": "功能演示"}, created_at=now)
            session.add(product)
            session.flush()
        order = Order(order_id=order_id, user_id=user.id, status=status,
                      status_desc=f"演示订单当前状态：{status}", amount=product.price,
                      created_at=now+timedelta(minutes=index), receiver_name="演示收件人",
                      receiver_phone_masked="不使用真实手机号", receiver_address="虚构演示地址")
        session.add(order)
        session.flush()
        session.add(OrderItem(order_id=order.id, product_id=product.id, title_snapshot=product.title,
                              quantity=1, price=product.price))
        if status in ("待揽收", "运输中", "已完成"):
            record = LogisticsRecord(order_id=order.id, logistics_company="演示物流",
                                     tracking_number=f"DEMO-TRACK-{index:03d}", status=status,
                                     status_desc=f"虚构物流：{status}", updated_at=now)
            session.add(record)
            session.flush()
            session.add(LogisticsTrace(logistics_record_id=record.id, trace_time=now,
                                       trace_desc=f"演示轨迹：{status}，不对应真实包裹"))
        inserted += 1
    return inserted


def initialize(engine: Engine, expected_database: str, seed: bool = False) -> int:
    if engine.url.database != expected_database:
        raise ValueError("Database name does not match --expected-database; no changes made.")
    Base.metadata.create_all(engine)
    if not seed:
        return 0
    with Session(engine) as session, session.begin():
        return seed_demo(session)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-database", required=True,
                        help="Must exactly match the configured dedicated business database name.")
    parser.add_argument("--seed", action="store_true", help="Add missing synthetic u1001 demo records.")
    args = parser.parse_args()
    from app.config import settings
    from sqlalchemy import create_engine

    engine = create_engine(make_url(settings.database_url), hide_parameters=True)
    try:
        count = initialize(engine, args.expected_database, args.seed)
    finally:
        engine.dispose()
    print(f"Business tables ready; {count} demo orders added. Existing data preserved.")


if __name__ == "__main__":
    main()
