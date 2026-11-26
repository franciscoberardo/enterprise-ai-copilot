import importlib.util
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, ToolMessage

from services.conversations import ConversationStore, conversation_view


class ConversationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "conversations.sqlite3"
        self.store = ConversationStore(self.path)
        self.received = []

    def answer(self, state):
        self.received.append(state["messages"])
        return {"messages": [*state["messages"], AIMessage(content="Respuesta de prueba")]}

    def test_history_survives_restart_and_is_sent_to_agent(self):
        first = self.store.reply(None, "Revisá el pedido 3", self.answer)
        restarted = ConversationStore(self.path)
        result = restarted.reply(first["id"], "¿Quién lo compró?", self.answer)

        self.assertEqual([message.content for message in self.received[-1]], [
            "Revisá el pedido 3", "Respuesta de prueba", "¿Quién lo compró?",
        ])
        self.assertEqual(len(result["messages"]), 4)
        self.assertEqual(len(restarted.list()), 1)

    def test_new_conversation_has_no_previous_context(self):
        first = self.store.reply(None, "Pedido 3", self.answer)
        second = self.store.reply(None, "Hola", self.answer)

        self.assertNotEqual(first["id"], second["id"])
        self.assertEqual(len(self.received[-1]), 1)
        self.assertEqual(len(self.store.list()), 2)

    def test_tool_calls_and_results_are_preserved(self):
        def use_tool(state):
            return {"messages": [
                *state["messages"],
                AIMessage(content="", tool_calls=[{
                    "name": "buscar_pedidos", "args": {}, "id": "call-1",
                }]),
                ToolMessage(content='[{"id": 3}]', tool_call_id="call-1", name="buscar_pedidos"),
                AIMessage(content=[{"type": "text", "text": "Encontré el pedido 3"}]),
            ]}

        first = self.store.reply(None, "Buscá pedidos", use_tool)
        view = conversation_view(self.store.get(first["id"]))
        self.assertEqual(len(view["messages"]), 2)
        self.assertEqual(view["context"][0]["tool"], "buscar_pedidos")
        self.store.reply(first["id"], "¿Y el 3?", self.answer)
        self.assertEqual(self.received[-1][2].tool_call_id, "call-1")
        self.assertEqual(self.received[-1][1].tool_calls[0]["id"], "call-1")

    def test_failure_does_not_change_saved_history(self):
        first = self.store.reply(None, "Hola", self.answer)

        def fail(state):
            raise RuntimeError("Servicio no disponible")

        with self.assertRaises(RuntimeError):
            self.store.reply(first["id"], "Otra pregunta", fail)
        self.assertEqual(len(self.store.get(first["id"])["messages"]), 2)

    def test_api_create_reopen_continue_and_validate(self):
        spec = importlib.util.spec_from_file_location("conversation_api", Path(__file__).with_name("main.py"))
        module = importlib.util.module_from_spec(spec)
        fake_agent = SimpleNamespace(agent=SimpleNamespace(invoke=self.answer))

        with patch.dict("sys.modules", {"agent": fake_agent}), patch(
            "services.conversations.ConversationStore", return_value=self.store
        ):
            spec.loader.exec_module(module)

        with TestClient(module.app) as client:
            first = client.post("/chat", json={"message": "Pedido 3"})
            self.assertEqual(first.status_code, 200)
            conversation_id = first.json()["id"]
            self.assertEqual(len(client.get("/conversations").json()), 1)
            self.assertEqual(len(client.get(f"/conversations/{conversation_id}").json()["messages"]), 2)
            second = client.post("/chat", json={"message": "¿Y el cliente?", "conversation_id": conversation_id})
            self.assertEqual(len(second.json()["messages"]), 4)
            self.assertEqual(client.post("/chat", json={"message": "  "}).status_code, 422)
            self.assertEqual(client.get("/conversations/no-es-un-uuid").status_code, 422)
            self.assertEqual(client.post("/chat", json={
                "message": "Hola", "conversation_id": "00000000-0000-0000-0000-000000000000",
            }).status_code, 404)


if __name__ == "__main__":
    unittest.main()
