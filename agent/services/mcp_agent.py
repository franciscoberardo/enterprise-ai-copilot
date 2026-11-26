import asyncio
from contextlib import AsyncExitStack

from anyio import from_thread
from fastmcp import Client
from fastmcp.exceptions import ClientError, MCPError
from langchain.mcp import MCPAdapter
from langgraph.prebuilt import create_react_agent

from services.settings import settings
from services.context_manager import compact_context, model_context

READ_TOOLS = {
    "buscar_clientes", "buscar_productos", "buscar_pedidos",
    "obtener_detalle_pedido", "analizar_pedido", "metricas_ventas",
}


class MCPUnavailable(Exception):
    """No se pudo descubrir un catálogo MCP de lectura válido."""


def read_only_catalog(tools):
    selected = []
    for tool in tools:
        if tool.name not in READ_TOOLS:
            continue
        metadata = (tool.metadata or {}).get("mcp", {})
        annotations = metadata.get("tool", {}).get("annotations", {})
        if (annotations.get("read_only_hint") is not True
                or annotations.get("destructive_hint") is not False):
            raise MCPUnavailable("El servidor MCP no anunció herramientas de solo lectura válidas.")
        selected.append(tool)
    if {tool.name for tool in selected} != READ_TOOLS:
        raise MCPUnavailable("El catálogo del servidor MCP está incompleto. Revisá su versión y configuración.")
    return selected


class MCPAgent:
    def __init__(self, model, local_tools, prompt, target=None, timeout=None):
        self.model = model
        self.local_tools = local_tools
        self.prompt = prompt
        self.target = target if target is not None else str(settings.mcp_server_url)
        self.timeout = timeout if timeout is not None else settings.mcp_timeout_seconds

    async def ainvoke(self, state):
        # Una sesión por turno mantiene las llamadas async en el mismo event loop.
        async with AsyncExitStack() as stack:
            try:
                async with asyncio.timeout(self.timeout):
                    client = Client(self.target, timeout=self.timeout, init_timeout=self.timeout)
                    adapter = await stack.enter_async_context(MCPAdapter(client))
                    tools = read_only_catalog(await adapter.list_tools())
            except MCPUnavailable:
                raise
            except Exception as error:
                raise MCPUnavailable(
                    "No se pudo conectar con el servidor MCP. Inicialo y revisá MCP_SERVER_URL antes de reintentar."
                ) from error

            summary, covered = await compact_context(
                state["messages"], self.model,
                state.get("context_summary", ""), state.get("summary_until", 0),
            )
            graph = create_react_agent(
                model=self.model, tools=[*tools, *self.local_tools], prompt=self.prompt,
                pre_model_hook=lambda current: {
                    "llm_input_messages": model_context(current["messages"], summary, covered)
                },
            )
            try:
                result = await graph.ainvoke({"messages": state["messages"]}, config={"recursion_limit": 25})
                return {**result, "context_summary": summary, "summary_until": covered}
            except (ClientError, MCPError, TimeoutError, ConnectionError) as error:
                raise MCPUnavailable("Se interrumpió la conexión MCP. Verificá el servidor y volvé a enviar la consulta.") from error

    def invoke(self, state):
        # Reutiliza el event loop de FastAPI desde su worker síncrono.
        # Evita reutilizar el cliente async del modelo entre loops ya cerrados.
        return from_thread.run(self.ainvoke, state)
