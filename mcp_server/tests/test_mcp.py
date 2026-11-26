import asyncio
import importlib.util
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "agent"))

import anyio
import httpx
from fastapi.testclient import TestClient
from fastmcp.exceptions import ToolError
from langchain.mcp import MCPAdapter
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.documents import Document
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field

from mcp_server.business import BusinessAPI, sales_metrics
from mcp_server.server import create_server
from services.conversations import ConversationStore, content_text
from services.mcp_agent import MCPAgent, MCPUnavailable, READ_TOOLS, read_only_catalog

ORDERS = [
    {"id": 1, "estado": "Entregado", "fecha": "2026-07-01", "total": "0.10", "detalle_pedidos": [], "clientes": {"nombre": "Demo"}},
    {"id": 2, "estado": "Entregado", "fecha": "2026-07-02", "total": "0.20", "detalle_pedidos": [], "clientes": {"nombre": "Demo"}},
    {"id": 3, "estado": "Pendiente", "fecha": "2026-07-03", "total": "99.00", "detalle_pedidos": [], "clientes": {"nombre": "Demo"}},
]


class ToolModel(BaseChatModel):
    """Modelo determinista que ejercita LangGraph sin consultar a Gemini."""
    requested_tool: str = "buscar_pedidos"
    arguments: dict = Field(default_factory=lambda: {"estado": "Pendiente"})
    seen_tools: list = Field(default_factory=list)

    @property
    def _llm_type(self):
        return "test-only-model"

    def bind_tools(self, tools, **kwargs):
        self.seen_tools = [tool.name for tool in tools]
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        if messages[-1].type == "human":
            message = AIMessage(content="", tool_calls=[{
                "name": self.requested_tool, "args": self.arguments, "id": f"call-{len(messages)}",
            }])
        else:
            message = AIMessage(content="Resultado de prueba: " + content_text(messages[-1].content))
        return ChatResult(generations=[ChatGeneration(message=message)])


def local_tools():
    vectorstore = Mock()
    vectorstore.similarity_search.return_value = [Document(
        page_content="Devoluciones dentro de los 30 días.", metadata={"source": "/uploads/politica.pdf", "page": 0}
    )]
    spec = importlib.util.spec_from_file_location("test_local_tools", ROOT / "agent" / "tools.py")
    module = importlib.util.module_from_spec(spec)
    with patch.dict("sys.modules", {"services.rag_service": SimpleNamespace(vectorstore=vectorstore)}):
        spec.loader.exec_module(module)
    return [module.buscar_documentacion, module.proponer_cambio_estado, module.proponer_devolucion]


class MCPTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.requests = []

        def handle(request):
            self.requests.append(request)
            if request.url.path.startswith("/pedidos/"):
                order = next((item for item in ORDERS if str(item["id"]) == request.url.path.rsplit("/", 1)[-1]), None)
                return httpx.Response(200 if order else 404, json=order or {"error": "No encontrado"})
            return httpx.Response(200, json=ORDERS if request.url.path == "/pedidos" else [])

        self.api = BusinessAPI("http://fixture", transport=httpx.MockTransport(handle))
        self.server = create_server(self.api)

    async def call(self, name, args):
        async with MCPAdapter(self.server) as adapter:
            tools = {tool.name: tool for tool in await adapter.list_tools()}
            return await tools[name].ainvoke({"type": "tool_call", "id": "test", "name": name, "args": args})

    async def test_discovery_is_read_only_and_excludes_writes(self):
        async with MCPAdapter(self.server) as adapter:
            tools = await adapter.list_tools()
            self.assertEqual({tool.name for tool in read_only_catalog(tools)}, READ_TOOLS)
            self.assertTrue(all(tool.metadata["mcp"]["tool"]["annotations"]["read_only_hint"] for tool in tools))
            self.assertNotIn("proponer_cambio_estado", {tool.name for tool in tools})

    async def test_schemas_bind_to_gemini_without_calling_it(self):
        async with MCPAdapter(self.server) as adapter:
            tools = await adapter.list_tools()
            model = ChatGoogleGenerativeAI(
                model="gemini-3.1-flash-lite", api_key="test-placeholder-not-a-real-key"
            )
            bound = model.bind_tools([*tools, *local_tools()])
            self.assertIn("tools", bound.kwargs)

    async def test_filters_are_forwarded_to_express(self):
        await self.call("buscar_clientes", {"nombre": "Demo", "pais": "Argentina"})
        await self.call("buscar_productos", {"stock_min": 3})
        await self.call("buscar_pedidos", {"estado": "Pendiente", "cliente_id": 1})
        self.assertEqual(dict(self.requests[0].url.params), {"nombre": "Demo", "pais": "Argentina"})
        self.assertEqual(dict(self.requests[1].url.params), {"stockMin": "3"})
        self.assertEqual(dict(self.requests[2].url.params), {"estado": "Pendiente", "cliente": "1"})
        self.assertTrue(all(request.method == "GET" for request in self.requests))

    async def test_invalid_parameters_do_not_reach_api(self):
        for tool, args in [("obtener_detalle_pedido", {"pedido_id": -1}), ("buscar_pedidos", {"estado": "Inventado"}), ("buscar_productos", {"stock_min": -1})]:
            try:
                result = await self.call(tool, args)
                self.assertEqual(result.status, "error")
            except ValueError:
                pass  # Validación del esquema en el cliente.
        self.assertEqual(self.requests, [])

    async def test_missing_order_and_bad_json_are_tool_errors(self):
        missing = await self.call("obtener_detalle_pedido", {"pedido_id": 999})
        self.assertEqual(missing.status, "error")
        self.assertIn("No se encontró", content_text(missing.content))
        self.api.transport = httpx.MockTransport(lambda request: httpx.Response(200, text="not json"))
        invalid = await self.call("buscar_clientes", {})
        self.assertEqual(invalid.status, "error")
        self.assertIn("inválida", content_text(invalid.content))
        self.api.transport = httpx.MockTransport(lambda request: httpx.Response(200, json=["formato incorrecto"]))
        invalid = await self.call("buscar_clientes", {})
        self.assertEqual(invalid.status, "error")
        self.assertIn("formato inesperado", content_text(invalid.content))

    async def test_timeout_is_an_explicit_error(self):
        def timeout(request):
            raise httpx.ReadTimeout("test timeout")
        self.api.transport = httpx.MockTransport(timeout)
        result = await self.call("buscar_productos", {})
        self.assertEqual(result.status, "error")
        self.assertIn("tardó demasiado", content_text(result.content))

    async def test_metrics_are_exact_and_validate_date_range(self):
        result = await self.call("metricas_ventas", {"fecha_desde": "2026-07-01", "fecha_hasta": "2026-07-02"})
        data = json.loads(content_text(result.content))
        self.assertEqual(data["importe_entregado"], "0.30")
        self.assertEqual(data["ticket_promedio_entregado"], "0.15")
        self.assertEqual(data["pedidos_total"], 2)
        self.assertEqual(sales_metrics(ORDERS)["pedidos_por_estado"]["Pendiente"], 1)
        self.requests.clear()
        invalid = await self.call("metricas_ventas", {"fecha_desde": "2026-08-01", "fecha_hasta": "2026-07-01"})
        self.assertEqual(invalid.status, "error")
        self.assertEqual(self.requests, [])
        with self.assertRaises(ToolError):
            sales_metrics([{"estado": "Entregado", "total": "NaN"}])
        self.assertEqual(sales_metrics([])["ticket_promedio_entregado"], "0.00")

    async def test_graph_memory_rag_and_local_approval_are_preserved(self):
        model = ToolModel()
        runtime = MCPAgent(model, local_tools(), "Agente de prueba", target=self.server)
        with tempfile.TemporaryDirectory() as directory:
            store = ConversationStore(Path(directory) / "test.sqlite3")
            first = await anyio.to_thread.run_sync(lambda: store.reply(None, "Pedidos", runtime.invoke))
            second = await anyio.to_thread.run_sync(lambda: store.reply(first["id"], "Otra consulta", runtime.invoke))
            self.assertEqual(len(second["messages"]), 4)
            self.assertIn("metricas_ventas", model.seen_tools)
            self.assertIn("proponer_cambio_estado", model.seen_tools)
            self.assertEqual(second["context"][-1]["tool"], "buscar_pedidos")

            model.requested_tool, model.arguments = "buscar_documentacion", {"query": "Devoluciones"}
            rag = await anyio.to_thread.run_sync(lambda: store.reply(first["id"], "Política", runtime.invoke))
            self.assertEqual(rag["messages"][-1]["sources"], [{"document": "politica.pdf", "page": 1}])

            model.requested_tool = "proponer_cambio_estado"
            model.arguments = {"pedido_id": 3, "estado": "Enviado"}
            with patch("services.order_actions.requests.get") as read, patch("services.order_actions.requests.patch") as write:
                read.return_value.status_code = 200
                read.return_value.json.return_value = {"id": 3, "estado": "Pendiente"}
                proposal = await anyio.to_thread.run_sync(lambda: store.reply(first["id"], "Cambiar", runtime.invoke))
                action = proposal["messages"][-1]["actions"][0]
                self.assertEqual(action["status"], "pending")
                write.assert_not_called()
                cancelled = store.resolve(first["id"], action["id"], False, Mock())
                self.assertEqual(cancelled["messages"][-1]["text"], "Acción cancelada. No se modificó el pedido.")

    async def test_unavailable_or_incompatible_catalog_is_rejected(self):
        runtime = MCPAgent(ToolModel(), [], "test", target="http://127.0.0.1:1/mcp", timeout=0.1)
        with self.assertRaises(MCPUnavailable):
            await runtime.ainvoke({"messages": [{"role": "user", "content": "Hola"}]})
        with self.assertRaises(MCPUnavailable):
            read_only_catalog([])
        unsafe = SimpleNamespace(name="buscar_pedidos", metadata={"mcp": {"tool": {"annotations": {"read_only_hint": True, "destructive_hint": True}}}})
        with self.assertRaises(MCPUnavailable):
            read_only_catalog([unsafe])

    async def test_api_reports_mcp_unavailable_without_saving_a_turn(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ConversationStore(Path(directory) / "test.sqlite3")
            spec = importlib.util.spec_from_file_location("test_mcp_api", ROOT / "agent" / "main.py")
            module = importlib.util.module_from_spec(spec)
            unavailable = SimpleNamespace(agent=SimpleNamespace(invoke=Mock(side_effect=MCPUnavailable("Servidor MCP no disponible"))))
            with patch.dict("sys.modules", {"agent": unavailable}), patch("services.conversations.ConversationStore", return_value=store):
                spec.loader.exec_module(module)
            with TestClient(module.app) as client:
                response = client.post("/chat", json={"message": "Pedidos pendientes"})
                self.assertEqual(response.status_code, 503)
                self.assertIn("MCP", response.json()["detail"])
                self.assertEqual(client.get("/conversations").json(), [])


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def wait_for_port(port, process):
    deadline = time.monotonic() + 12
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("El servidor de prueba terminó antes de iniciar")
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                return
        except OSError:
            time.sleep(0.05)
    raise TimeoutError("El servidor de prueba no inició")


class HTTPIntegrationTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.processes = []
        cls.log = tempfile.TemporaryFile()
        cls.addClassCleanup(cls.log.close)
        cls.addClassCleanup(cls.stop_servers)
        api_port, mcp_port = free_port(), free_port()
        cls.api_url = f"http://127.0.0.1:{api_port}"
        cls.mcp_url = f"http://127.0.0.1:{mcp_port}/mcp"
        env = {**os.environ, "PORT": str(api_port), "BUSINESS_API_URL": cls.api_url, "MCP_PORT": str(mcp_port), "MCP_HOST": "127.0.0.1"}
        env.pop("GOOGLE_API_KEY", None)
        env.pop("GEMINI_API_KEY", None)
        api = subprocess.Popen(["node", "mcp_server/tests/express_fixture.cjs"], cwd=ROOT, env=env, stdout=cls.log, stderr=cls.log)
        cls.processes.append(api)
        wait_for_port(api_port, api)
        mcp = subprocess.Popen([sys.executable, "-m", "mcp_server.server"], cwd=ROOT, env=env, stdout=cls.log, stderr=cls.log)
        cls.processes.append(mcp)
        wait_for_port(mcp_port, mcp)

    @classmethod
    def stop_servers(cls):
        for process in reversed(cls.processes):
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)

    async def test_streamable_http_to_real_express_routes(self):
        async with MCPAdapter(self.mcp_url) as adapter:
            tools = {tool.name: tool for tool in await adapter.list_tools()}
            self.assertEqual(set(tools), READ_TOOLS)
            metrics = await tools["metricas_ventas"].ainvoke({"type": "tool_call", "id": "metrics", "name": "metricas_ventas", "args": {}})
            self.assertEqual(json.loads(content_text(metrics.content))["importe_entregado"], "0.30")
            await tools["buscar_clientes"].ainvoke({"nombre": "Demo"})
            await tools["buscar_productos"].ainvoke({"stock_min": 2})
            orders = await tools["buscar_pedidos"].ainvoke({"type": "tool_call", "id": "orders", "name": "buscar_pedidos", "args": {"estado": "Pendiente", "cliente_id": 1}})
            self.assertEqual(json.loads(content_text(orders.content))[0]["id"], 3)
            details = await tools["obtener_detalle_pedido"].ainvoke({"type": "tool_call", "id": "details", "name": "obtener_detalle_pedido", "args": {"pedido_id": 1}})
            self.assertEqual(len(json.loads(content_text(details.content))["detalle_pedidos"]), 1)

        async with httpx.AsyncClient() as client:
            requests = (await client.get(f"{self.api_url}/__requests")).json()
        self.assertTrue(all(request["method"] == "GET" for request in requests))
        self.assertTrue(any(request["query"] == {"estado": "Pendiente", "cliente": "1"} for request in requests))

    async def test_graph_over_http_without_a_real_model(self):
        runtime = MCPAgent(ToolModel(), local_tools(), "Agente de prueba", target=self.mcp_url)
        with tempfile.TemporaryDirectory() as directory:
            store = ConversationStore(Path(directory) / "test.sqlite3")
            first = await anyio.to_thread.run_sync(lambda: store.reply(None, "Pedidos pendientes", runtime.invoke))
            second = await anyio.to_thread.run_sync(lambda: store.reply(first["id"], "Otra vez", runtime.invoke))
            self.assertEqual(len(second["messages"]), 4)
            self.assertEqual(second["context"][-1]["tool"], "buscar_pedidos")


if __name__ == "__main__":
    unittest.main()
