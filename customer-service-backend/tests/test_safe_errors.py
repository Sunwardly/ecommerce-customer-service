import unittest
from unittest.mock import AsyncMock, patch

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.exceptions import OutputParserException
from construction_service.api.router import avatar_ws_router


class SafeErrorsTests(unittest.IsolatedAsyncioTestCase):
    async def test_invalid_llm_output_is_not_sent_or_logged(self):
        sentinel = "sentinel_private_llm_content"
        try:
            JsonOutputParser().parse(sentinel)
        except OutputParserException as error:
            upstream_error = error
        else:
            self.fail("Control must reproduce an invalid LLM JSON exception")
        self.assertIn(sentinel, str(upstream_error))
        socket = AsyncMock()
        with patch.object(avatar_ws_router, "get_engine", side_effect=upstream_error), \
                self.assertLogs(avatar_ws_router.logger, level="WARNING") as logs:
            await avatar_ws_router._run_turn(socket, {"sender_id": "v_test", "text": "hello"})
        self.assertNotIn(sentinel, "\n".join(logs.output))
        sent = "\n".join(call.args[0] for call in socket.send_text.await_args_list)
        self.assertNotIn(sentinel, sent)
        self.assertIn('"type": "user_ack"', sent)
        self.assertIn('"type": "error"', sent)
