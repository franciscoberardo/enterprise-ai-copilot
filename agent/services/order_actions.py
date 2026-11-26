from typing import Literal

import requests
from pydantic import BaseModel, Field

from services.settings import settings

API = str(settings.business_api_url).rstrip("/")
OrderState = Literal["Pendiente", "Enviado", "Entregado", "Cancelado", "Devuelto"]


class StateChange(BaseModel):
    pedido_id: int = Field(gt=0)
    estado: OrderState


class ReturnRequest(BaseModel):
    pedido_id: int = Field(gt=0)


class OrderAction(BaseModel):
    pedido_id: int = Field(gt=0)
    estado_anterior: str | None
    estado_nuevo: OrderState


def propose_state_change(pedido_id, estado):
    change = StateChange(pedido_id=pedido_id, estado=estado)
    try:
        response = requests.get(f"{API}/pedidos/{change.pedido_id}", timeout=(3, settings.api_timeout_seconds))
        if response.status_code == 404:
            return {"error": "Pedido no encontrado"}
        response.raise_for_status()
        pedido = response.json()
    except (requests.RequestException, ValueError):
        return {"error": "No se pudo consultar el pedido. Intentá nuevamente."}

    if pedido["estado"] == change.estado:
        return {"message": f"El pedido ya está en estado {change.estado}."}

    action = OrderAction(
        pedido_id=change.pedido_id,
        estado_anterior=pedido["estado"],
        estado_nuevo=change.estado,
    )
    return {
        "requires_approval": True,
        "message": "Propuesta preparada. El pedido NO se modificó. El usuario debe confirmar con el botón del chat.",
        "action": action.model_dump(),
    }


class ActionExecutionError(Exception):
    pass


def execute_order_action(payload):
    action = OrderAction.model_validate(payload)
    try:
        response = requests.patch(
            f"{API}/pedidos/{action.pedido_id}/estado",
            json={"estado": action.estado_nuevo, "estado_anterior": action.estado_anterior},
            timeout=(3, settings.api_timeout_seconds),
        )
        if response.status_code == 409:
            raise ActionExecutionError("El pedido cambió desde la propuesta. Consultalo y prepará una nueva solicitud.")
        if response.status_code == 404:
            raise ActionExecutionError("El pedido ya no existe.")
        response.raise_for_status()
    except requests.RequestException as error:
        raise ActionExecutionError(
            "No se pudo confirmar el resultado del cambio. Consultá el estado del pedido antes de volver a solicitarlo."
        ) from error

    text = f"Pedido {action.pedido_id} actualizado a {action.estado_nuevo}."
    if action.estado_nuevo == "Devuelto":
        text += " Se registró la devolución; no se ejecutó un reintegro de dinero."
    return text
