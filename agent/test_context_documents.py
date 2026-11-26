import importlib.util
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from langchain_core.documents import Document
from langchain_core.messages import AIMessage, HumanMessage

from services.context_manager import compact_context, model_context
from services.conversations import ConversationStore
from services.document_index import DocumentIndex


class ContextTests(unittest.IsolatedAsyncioTestCase):
    async def test_compacts_complete_turns_without_changing_history(self):
        messages = sum(([HumanMessage(content=f"Pedido {i} " + "x" * 500), AIMessage(content="y" * 500)] for i in range(10)), [])
        original = list(messages)
        model = SimpleNamespace(ainvoke=AsyncMock(return_value=AIMessage(content="Pedidos 0 al 7")))
        with patch("services.context_manager.settings", SimpleNamespace(context_token_limit=1000, context_recent_turns=2)):
            summary, covered = await compact_context(messages, model)
            self.assertEqual(covered, 16)
            self.assertEqual(messages, original)
            self.assertEqual(model_context(messages, summary, covered)[1:], messages[16:])
            await compact_context(messages, model, summary, covered)
            model.ainvoke.assert_awaited_once()

    async def test_summary_and_full_history_survive_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "chat.sqlite3"
            store = ConversationStore(path)
            def answer(state):
                return {"messages": [*state["messages"], AIMessage(content="Respuesta")], "context_summary": "Pedido 3", "summary_until": 0}
            result = store.reply(None, "Pregunta", answer)
            saved = ConversationStore(path).get(result["id"])
            self.assertEqual(saved["context_summary"], "Pedido 3")
            self.assertEqual(len(saved["messages"]), 2)
            self.assertEqual(result["context_summary"], "Pedido 3")


class FakeStore:
    def __init__(self):
        self.rows, self.embedded = {}, []

    def get(self, include=None):
        return {"ids": list(self.rows), "metadatas": [item.metadata for item in self.rows.values()]}

    def add_documents(self, documents, ids):
        self.embedded.extend(document.page_content for document in documents)
        self.rows.update(zip(ids, documents))

    def delete(self, ids):
        for key in ids:
            self.rows.pop(key, None)

    def similarity_search(self, query, k):
        return list(self.rows.values())[:k]


class IndexTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        self.uploads = root / "uploads"
        self.store = FakeStore()
        self.index = DocumentIndex(self.store, self.uploads, root / "index" / "documents.json")
        def load(loader):
            path = Path(loader.file_path)
            text = path.read_text()
            if "broken" in text:
                raise ValueError("PDF inválido")
            return [Document(page_content=text, metadata={"source": str(path), "page": 0})]
        patcher = patch("services.document_index.PyPDFLoader.load", autospec=True, side_effect=load)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_only_changed_files_are_embedded_and_removed_files_disappear(self):
        self.index.upload("a.pdf", b"%PDF-1.4 A")
        self.index.upload("b.pdf", b"%PDF-1.4 B")
        self.assertEqual(len(self.store.embedded), 2)
        self.index.sync()
        self.assertEqual(len(self.store.embedded), 2)
        self.index.upload("a.pdf", b"%PDF-1.4 A actualizado")
        self.assertEqual(len(self.store.embedded), 3)
        self.assertEqual(len(self.store.rows), 2)
        self.assertNotIn("%PDF-1.4 A", [item.page_content for item in self.store.rows.values()])
        (self.uploads / "b.pdf").unlink()
        self.index.sync()
        self.assertEqual(len(self.store.rows), 1)
        DocumentIndex(self.store, self.uploads, self.index.manifest).similarity_search("A", k=3)
        self.assertEqual(len(self.store.embedded), 3)

    def test_invalid_replacement_preserves_old_file_and_index(self):
        self.index.upload("a.pdf", b"%PDF-1.4 Original")
        with self.assertRaises(ValueError):
            self.index.upload("a.pdf", b"%PDF-1.4 broken")
        self.assertEqual((self.uploads / "a.pdf").read_bytes(), b"%PDF-1.4 Original")
        self.assertIn("Original", next(iter(self.store.rows.values())).page_content)
        with self.assertRaises(ValueError):
            self.index.upload("../escape.pdf", b"%PDF-1.4 Data")

    def test_real_chroma_updates_without_duplicate_chunks(self):
        from chromadb.config import Settings
        from langchain_community.vectorstores import Chroma
        from langchain_core.embeddings import DeterministicFakeEmbedding
        store = Chroma(
            persist_directory=str(self.uploads.parent / "chroma"),
            embedding_function=DeterministicFakeEmbedding(size=8),
            client_settings=Settings(anonymized_telemetry=False),
        )
        index = DocumentIndex(store, self.uploads, self.index.manifest)
        index.upload("real.pdf", b"%PDF-1.4 primera version")
        first_ids = store.get()["ids"]
        index.sync()
        self.assertEqual(store.get()["ids"], first_ids)
        index.upload("real.pdf", b"%PDF-1.4 nueva version")
        self.assertEqual(len(store.get()["ids"]), 1)
        self.assertNotEqual(store.get()["ids"], first_ids)

    def test_upload_api_lists_replaces_and_rejects_invalid_files(self):
        spec = importlib.util.spec_from_file_location("test_document_api", Path(__file__).with_name("main.py"))
        module = importlib.util.module_from_spec(spec)
        store = ConversationStore(self.uploads.parent / "chat.sqlite3")
        with patch.dict("sys.modules", {"agent": SimpleNamespace(agent=None), "services.rag_service": SimpleNamespace(vectorstore=self.index)}), patch("services.conversations.ConversationStore", return_value=store):
            spec.loader.exec_module(module)
            with TestClient(module.app) as client:
                response = client.post("/documents", files={"file": ("a.pdf", b"%PDF-1.4 Texto", "application/pdf")})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(client.get("/documents").json()[0]["name"], "a.pdf")
                response = client.post("/documents", files={"file": ("a.pdf", b"no es un pdf", "application/pdf")})
                self.assertEqual(response.status_code, 422)
                self.assertIn("Texto", (self.uploads / "a.pdf").read_text())

    def test_legacy_metadata_is_migrated(self):
        path = self.uploads / "a.pdf"
        path.write_text("%PDF-1.4 A")
        self.store.rows["legacy"] = Document(page_content="Antes", metadata={"source": str(path), "page": 0})
        self.index.sync()
        self.assertNotIn("legacy", self.store.rows)
        self.assertEqual(len(self.store.rows), 1)
        self.assertEqual(next(iter(self.store.rows.values())).metadata["page"], 0)


if __name__ == "__main__":
    unittest.main()
