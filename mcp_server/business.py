from collections import Counter
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

import httpx
from fastmcp.exceptions import ToolError


class BusinessAPI:
    """Acceso limitado a los endpoints GET conocidos; no admite escrituras."""

    def __init__(self, base_url, timeout=10, transport=None):
        self.base_url = str(base_url).rstrip("/") + "/"
        self.timeout = timeout
        self.transport = transport

    async def get(self, path, params=None, expected=list):
        try:
            async with httpx.AsyncClient(
                base_url=self.base_url, timeout=self.timeout, transport=self.transport
            ) as client:
                response = await client.get(path, params=params)
                response.raise_for_status()
                data = response.json()
        except httpx.TimeoutException as error:
            raise ToolError("La API Express tardó demasiado en responder.") from error
        except httpx.HTTPStatusError as error:
            if error.response.status_code == 404:
                raise ToolError("No se encontró el registro solicitado.") from error
            raise ToolError("La API Express no pudo completar la consulta.") from error
        except httpx.RequestError as error:
            raise ToolError("No se pudo conectar con la API Express.") from error
        except ValueError as error:
            raise ToolError("La API Express devolvió una respuesta inválida.") from error

        if not isinstance(data, expected) or (
            expected is list and any(not isinstance(item, dict) for item in data)
        ):
            raise ToolError("La API Express devolvió datos con un formato inesperado.")
        return data

    async def clientes(self, **filters):
        return await self.get("clientes", params=self.filters(filters))

    async def productos(self, **filters):
        return await self.get("productos", params=self.filters(filters))

    async def pedidos(self, **filters):
        return await self.get("pedidos", params=self.filters(filters))

    async def pedido(self, pedido_id):
        pedido = await self.get(f"pedidos/{pedido_id}", expected=dict)
        if not {"id", "estado", "detalle_pedidos"} <= pedido.keys() or not isinstance(pedido["detalle_pedidos"], list):
            raise ToolError("La API Express devolvió un pedido incompleto.")
        return pedido

    @staticmethod
    def filters(values):
        return {name: value for name, value in values.items() if value is not None}


def sales_metrics(pedidos, desde=None, hasta=None):
    if desde and hasta and desde > hasta:
        raise ToolError("La fecha inicial no puede ser posterior a la fecha final.")

    selected = []
    try:
        for pedido in pedidos:
            if desde or hasta:
                fecha = date.fromisoformat(pedido["fecha"][:10])
                if (desde and fecha < desde) or (hasta and fecha > hasta):
                    continue
            selected.append(pedido)

        delivered = [pedido for pedido in selected if pedido.get("estado") == "Entregado"]
        amounts = [Decimal(str(pedido["total"])) for pedido in delivered]
        if any(not amount.is_finite() for amount in amounts):
            raise ValueError("Importe no finito")
        total = sum(amounts, Decimal("0"))
        average = total / len(delivered) if delivered else Decimal("0")
    except (KeyError, TypeError, ValueError, InvalidOperation) as error:
        raise ToolError("No se pueden calcular métricas: hay fechas o importes inválidos en los pedidos.") from error

    def money(value):
        return str(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

    return {
        "periodo": {"desde": str(desde) if desde else None, "hasta": str(hasta) if hasta else None},
        "criterio": "Ventas reconocidas: solo pedidos Entregado. Importes según el total registrado del pedido, sin recalcular sus detalles. Fechas inclusivas. Moneda no especificada por el sistema.",
        "pedidos_total": len(selected),
        "pedidos_por_estado": dict(Counter(pedido.get("estado") or "Sin estado" for pedido in selected)),
        "ventas_entregadas": len(delivered),
        "importe_entregado": money(total),
        "ticket_promedio_entregado": money(average),
    }
