import unittest
from unittest.mock import AsyncMock, patch

from sqlalchemy.dialects import mysql
from sqlalchemy.schema import CreateTable

from construction_service.model.state_record import DialogueStateRecord


class DatabaseSchemaTests(unittest.IsolatedAsyncioTestCase):
    def test_mysql_state_table_has_bounded_sender(self):
        ddl = str(CreateTable(DialogueStateRecord.__table__).compile(dialect=mysql.dialect()))
        self.assertIn("VARCHAR(64)", ddl)
        self.assertIn("PRIMARY KEY", ddl)
        self.assertEqual(DialogueStateRecord.__table__.c.state_json.default.arg, "{}")

    async def test_engine_never_logs_dialogue_parameters(self):
        from construction_service.infrastructure import db
        old_engine, old_factory = db.engine, db.session_factory
        try:
            with patch.object(db, "create_async_engine") as create, patch.object(db, "async_sessionmaker"):
                await db.init_db_engine()
                self.assertFalse(create.call_args.kwargs["echo"])
                self.assertTrue(create.call_args.kwargs["hide_parameters"])
        finally:
            db.engine, db.session_factory = old_engine, old_factory

    async def test_initializer_rejects_wrong_database_before_connecting(self):
        from construction_service.init_db import initialize
        with self.assertRaises(ValueError), patch("sqlalchemy.ext.asyncio.create_async_engine") as create:
            await initialize("not-the-configured-database")
        create.assert_not_called()
