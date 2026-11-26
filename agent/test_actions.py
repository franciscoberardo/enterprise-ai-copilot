import importlib.util
import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import requests
from langchain_core.documents import Document
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from pydantic import ValidationError

from services.conversations import ConversationStore, conversation_view
from services.order_actions import ActionExecutionError, execute_order_action, propose_state_change
from services.retrieval import retrieve_documents


class ApprovalTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "chat.sqlite3"
        self.store = ConversationStore(self.path)
        self.payload = {"pedido_id": 2, "estado_anterior": "Pendiente", "estado_nuevo": "Enviado"}

    def propose(self, state):
        return {"messages": [
            *state["messages"],
            AIMessage(content="", tool_calls=[{"name": "proponer_cambio_estado", "args": {}, "id": "call-1"}]),
            ToolMessage(content=json.dumps({"requires_approval": True, "action": self.payload}),
                        name="proponer_cambio_estado", tool_call_id="call-1"),
            AIMessage(content="Preparé la propuesta. Confirmala en el chat."),
        ]}

    def pending(self):
        result = self.store.reply(None, "Enviá el pedido 2", self.propose)
        return result["id"], result["messages"][-1]["actions"][0]["id"]

    def test_proposal_is_persistent_and_cancel_never_executes(self):
        conversation_id, action_id = self.pending()
        restarted = ConversationStore(self.path)
        execute = Mock()
        result = restarted.resolve(conversation_id, action_id, False, execute)
        execute.assert_not_called()
        self.assertEqual(result["messages"][1]["actions"][0]["status"], "cancelled")

    def test_confirm_executes_once_even_if_repeated_after_restart(self):
        conversation_id, action_id = self.pending()
        execute = Mock(return_value="Pedido 2 actualizado a Enviado.")
        self.store.resolve(conversation_id, action_id, True, execute)
        restarted = ConversationStore(self.path)
        result = restarted.resolve(conversation_id, action_id, True, execute)
        execute.assert_called_once_with(self.payload)
        self.assertEqual(result["messages"][1]["actions"][0]["status"], "executed")
        self.assertEqual(len(result["messages"]), 4)

    def test_parallel_confirmations_claim_only_once(self):
        conversation_id, action_id = self.pending()
        execute = Mock(return_value="Actualizado")
        restarted = ConversationStore(self.path)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = [pool.submit(store.resolve, conversation_id, action_id, True, execute)
                       for store in (self.store, restarted)]
            for result in results:
                result.result()
        execute.assert_called_once()

    def test_action_cannot_be_approved_from_another_conversation(self):
        conversation_id, action_id = self.pending()
        other_id, _ = self.pending()
        execute = Mock()
        with self.assertRaises(KeyError):
            self.store.resolve(other_id, action_id, True, execute)
        execute.assert_not_called()

    def test_stale_or_failed_action_is_not_retried(self):
        conversation_id, action_id = self.pending()
        execute = Mock(side_effect=ActionExecutionError("El pedido cambió"))
        self.store.resolve(conversation_id, action_id, True, execute)
        result = self.store.resolve(conversation_id, action_id, True, execute)
        execute.assert_called_once()
        self.assertEqual(result["messages"][1]["actions"][0]["status"], "failed")

    def test_new_proposal_replaces_previous_pending_action(self):
        conversation_id, previous_id = self.pending()
        self.payload["estado_nuevo"] = "Cancelado"
        self.store.reply(conversation_id, "Mejor cancelalo", self.propose)
        execute = Mock()
        self.store.resolve(conversation_id, previous_id, True, execute)
        execute.assert_not_called()
        actions = self.store.get(conversation_id)["actions"]
        self.assertEqual([item["status"] for item in actions], ["cancelled", "pending"])

    @patch("services.order_actions.requests.get")
    @patch("services.order_actions.requests.patch")
    def test_proposal_only_reads_and_validates(self, write, read):
        read.return_value.status_code = 200
        read.return_value.json.return_value = {"id": 2, "estado": "Pendiente"}
        result = propose_state_change(2, "Enviado")
        self.assertTrue(result["requires_approval"])
        self.assertEqual(result["action"], self.payload)
        write.assert_not_called()
        with self.assertRaises(ValidationError):
            propose_state_change(-1, "Enviado")
        with self.assertRaises(ValidationError):
            propose_state_change(2, "cualquier cosa")
        read.assert_called_once()

    @patch("services.order_actions.requests.patch")
    def test_execution_sends_expected_state_and_handles_conflict(self, write):
        write.return_value.status_code = 409
        with self.assertRaises(ActionExecutionError):
            execute_order_action(self.payload)
        self.assertEqual(write.call_args.kwargs["json"], {"estado": "Enviado", "estado_anterior": "Pendiente"})
        write.side_effect = requests.Timeout()
        with self.assertRaisesRegex(ActionExecutionError, "No se pudo confirmar"):
            execute_order_action(self.payload)

    def test_approval_api_validates_and_cannot_bypass_cancel(self):
        spec = importlib.util.spec_from_file_location("approval_api", Path(__file__).with_name("main.py"))
        module = importlib.util.module_from_spec(spec)
        fake_agent = SimpleNamespace(agent=SimpleNamespace(invoke=self.propose))
        with patch.dict("sys.modules", {"agent": fake_agent}), patch(
            "services.conversations.ConversationStore", return_value=self.store
        ):
            spec.loader.exec_module(module)
        execute = Mock(return_value="Pedido actualizado")
        module.execute_order_action = execute

        with TestClient(module.app) as client:
            first = client.post("/chat", json={"message": "Enviá el pedido 2"}).json()
            action_id = first["messages"][-1]["actions"][0]["id"]
            url = f"/conversations/{first['id']}/actions/{action_id}"
            execute.assert_not_called()
            self.assertEqual(client.post(url, json={"approve": "sí"}).status_code, 422)
            self.assertEqual(client.post(url, json={"approve": False}).status_code, 200)
            self.assertEqual(client.post(url, json={"approve": True}).status_code, 200)
            execute.assert_not_called()

            second = client.post("/chat", json={"message": "Enviá el pedido 2"}).json()
            action_id = second["messages"][-1]["actions"][0]["id"]
            url = f"/conversations/{second['id']}/actions/{action_id}"
            self.assertEqual(client.post(url, json={"approve": True}).status_code, 200)
            self.assertEqual(client.post(url, json={"approve": True}).status_code, 200)
            execute.assert_called_once()
            self.assertEqual(client.post(
                f"/conversations/{first['id']}/actions/{action_id}", json={"approve": True}
            ).status_code, 404)

            uploads = Path(self.directory.name) / "uploads"
            uploads.mkdir()
            (uploads / "policy.pdf").write_bytes(b"%PDF-1.4\n")
            module.UPLOADS = uploads.resolve()
            response = client.get("/documents/policy.pdf")
            self.assertEqual(response.status_code, 200)
            self.assertIn("inline", response.headers["content-disposition"])
            self.assertEqual(client.get("/documents/chat.sqlite3").status_code, 404)
            (uploads / "outside.pdf").symlink_to(self.path)
            self.assertEqual(client.get("/documents/outside.pdf").status_code, 404)


class SourcesTests(unittest.TestCase):
    def test_real_metadata_is_used_without_inventing_pages(self):
        vectorstore = Mock()
        vectorstore.similarity_search.return_value = [
            Document(page_content="30 días", metadata={"source": "/uploads/politica.pdf", "page": 0}),
            Document(page_content="Embalaje original", metadata={"source": "/uploads/politica.pdf", "page": 0}),
            Document(page_content="Sin página", metadata={"source": "/uploads/manual.pdf"}),
        ]
        data = retrieve_documents(vectorstore, "Devoluciones")
        vectorstore.similarity_search.assert_called_once_with("Devoluciones", k=3)
        messages = [
            HumanMessage(content="Política"),
            ToolMessage(content=json.dumps(data), name="buscar_documentacion", tool_call_id="doc-1"),
            AIMessage(content="Podés solicitarla dentro de los 30 días."),
        ]
        conversation = {"id": "test", "title": "Política", "messages": messages}
        view = conversation_view(conversation)
        self.assertEqual(view["messages"][-1]["sources"], [
            {"document": "politica.pdf", "page": 1}, {"document": "manual.pdf", "page": None},
        ])
        messages.extend([HumanMessage(content="Hola"), AIMessage(content="Hola")])
        self.assertEqual(conversation_view(conversation)["messages"][-1]["sources"], [])


if __name__ == "__main__":
    unittest.main()
