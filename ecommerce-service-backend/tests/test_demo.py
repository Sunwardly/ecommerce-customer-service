import unittest
import os
import subprocess
import sys
from sqlalchemy import create_engine, select, delete
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from sqlalchemy.schema import CreateTable
from fastapi.testclient import TestClient

from app.models import Base, Order, Product, User, OrderItem
from app.init_demo import initialize, seed_demo
from app.app import app
from app.database import get_db


class DemoTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        initialize(self.engine, None, seed=True)
        def db():
            with Session(self.engine) as session:
                yield session
        app.dependency_overrides[get_db] = db
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()
        self.engine.dispose()

    def test_mysql_all_tables_compile(self):
        for table in Base.metadata.sorted_tables:
            self.assertIn("CREATE TABLE", str(CreateTable(table).compile(dialect=mysql.dialect())))

    def test_environment_overrides_local_configuration(self):
        result = subprocess.run([sys.executable, '-c',
                                 "from app.config import settings; assert settings.database_url == 'sqlite://'; print('ok')"],
                                env={**os.environ, 'DATABASE_URL': 'sqlite://'}, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), 'ok')

    def test_empty_database_configuration_fails_without_default_credentials(self):
        result = subprocess.run([sys.executable, '-c', 'import app.config'],
                                env={**os.environ, 'DATABASE_URL': ''}, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('DATABASE_URL is required', result.stderr)
        self.assertNotIn('mysql+pymysql://', result.stderr)

    def test_seed_is_idempotent_and_preserves_existing_changes(self):
        with Session(self.engine) as session, session.begin():
            order = session.scalar(select(Order).where(Order.order_id == "DEMO-ORDER-001"))
            order.status_desc = "用户自行修改的数据"
        self.assertEqual(initialize(self.engine, None, seed=True), 0)
        with Session(self.engine) as session:
            self.assertEqual(len(session.scalars(select(Order)).all()), 5)
            self.assertEqual(len(session.scalars(select(Product)).all()), 5)
            self.assertEqual(session.scalar(select(Order).where(Order.order_id == "DEMO-ORDER-001")).status_desc,
                             "用户自行修改的数据")

    def test_wrong_database_rejected(self):
        with self.assertRaises(ValueError):
            initialize(self.engine, "other-db", seed=True)

    def test_seed_conflict_rolls_back(self):
        with Session(self.engine) as session, session.begin():
            owner = User(user_id="other", nickname="其他", level="demo", mobile_masked="无", created_at=__import__('datetime').datetime.now())
            session.add(owner)
            session.flush()
            session.scalar(select(Order).where(Order.order_id == "DEMO-ORDER-005")).user_id = owner.id
            first_id = session.scalar(select(Order.id).where(Order.order_id == "DEMO-ORDER-001"))
            session.execute(delete(OrderItem).where(OrderItem.order_id == first_id))
            session.execute(delete(Order).where(Order.id == first_id))
        with self.assertRaises(ValueError):
            initialize(self.engine, None, seed=True)
        with Session(self.engine) as session:
            self.assertIsNone(session.scalar(select(Order).where(Order.order_id == "DEMO-ORDER-001")))

    def test_demo_read_endpoints_and_absent_logistics(self):
        self.assertEqual(self.client.get("/health").status_code, 200)
        data = self.client.get("/users/u1001/orders").json()["data"]["orders"]
        self.assertEqual(len(data), 5)
        self.assertEqual(self.client.get("/users/u1001/products").status_code, 200)
        self.assertEqual(self.client.get("/orders/DEMO-ORDER-003").status_code, 200)
        self.assertEqual(self.client.get("/orders/DEMO-ORDER-003/logistics").status_code, 200)
        self.assertEqual(self.client.get("/orders/DEMO-ORDER-001/logistics").status_code, 404)
        self.assertEqual(self.client.get("/orders/missing").status_code, 404)
