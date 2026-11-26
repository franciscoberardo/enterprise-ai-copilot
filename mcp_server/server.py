from datetime import date
from typing import Annotated, Literal

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from pydantic import Field, StringConstraints
from starlette.responses import JSONResponse

from mcp_server.business import BusinessAPI, sales_metrics
from mcp_server.config import Settings

TextFilter = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
]
PositiveID = Annotated[int, Field(gt=0)]
OrderState = Literal["Pendiente", "Enviado", "Entregado", "Cancelado", "Devuelto"]
READ_ONLY = {
    "readOnlyHint": True, "destructiveHint": False,
    "idempotentHint": True, "openWorldHint": False,
}


def create_server(api=None):
    settings = Settings()
    api = api or BusinessAPI(settings.business_api_url, settings.api_timeout_seconds)
    server = FastMCP(
        "Enterprise AI Business",
        instructions="Herramientas de consulta del negocio. No realiza escrituras ni aprueba cambios de pedidos.",
    )

    @server.custom_route("/health", methods=["GET"])
    async def health(request):
        return JSONResponse({"status": "ok"})

    @server.tool(annotations=READ_ONLY)
    async def buscar_clientes(
        nombre: TextFilter | None = None,
        pais: TextFilter | None = None,
        email: TextFilter | None = None,
    ) -> list:
        """Consulta clientes. Permite filtrar por nombre, país o email en la API del negocio."""
        return await api.clientes(nombre=nombre, pais=pais, email=email)

    @server.tool(annotations=READ_ONLY)
    async def buscar_productos(
        nombre: TextFilter | None = None,
        categoria: TextFilter | None = None,
        stock_min: Annotated[int, Field(ge=0)] | None = None,
    ) -> list:
        """Consulta productos por nombre, categoría o stock mínimo."""
        return await api.productos(nombre=nombre, categoria=categoria, stockMin=stock_min)

    @server.tool(annotations=READ_ONLY)
    async def buscar_pedidos(
        estado: OrderState | None = None, cliente_id: PositiveID | None = None
    ) -> list:
        """Consulta pedidos, opcionalmente por estado o cliente. Incluye clientes y detalles."""
        return await api.pedidos(estado=estado, cliente=cliente_id)

    @server.tool(annotations=READ_ONLY)
    async def obtener_detalle_pedido(pedido_id: PositiveID) -> dict:
        """Obtiene un pedido con cliente, productos, cantidades y precios de sus detalles."""
        return await api.pedido(pedido_id)

    @server.tool(annotations=READ_ONLY)
    async def analizar_pedido(pedido_id: PositiveID) -> dict:
        """Reúne pedido y cliente para que el agente analice posibles inconsistencias. No modifica datos."""
        pedido = await api.pedido(pedido_id)
        return {"pedido": pedido, "cliente": pedido.get("clientes")}

    @server.tool(annotations=READ_ONLY)
    async def metricas_ventas(
        fecha_desde: date | None = None, fecha_hasta: date | None = None
    ) -> dict:
        """Calcula pedidos por estado, importe y ticket promedio de pedidos Entregado; fechas inclusivas, formato AAAA-MM-DD."""
        if fecha_desde and fecha_hasta and fecha_desde > fecha_hasta:
            raise ToolError("La fecha inicial no puede ser posterior a la fecha final.")
        return sales_metrics(await api.pedidos(), fecha_desde, fecha_hasta)

    return server


if __name__ == "__main__":
    settings = Settings()
    create_server().run(
        transport="http", host=settings.mcp_host, port=settings.mcp_port,
        path="/mcp", stateless_http=True,
    )
