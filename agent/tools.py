from langchain_core.tools import tool

from services.order_actions import StateChange, ReturnRequest, propose_state_change
from services.rag_service import vectorstore
from services.retrieval import retrieve_documents


@tool
def buscar_documentacion(query: str):
    """Busca información en los PDFs de la empresa e identifica sus fuentes."""
    return retrieve_documents(vectorstore, query)


@tool(args_schema=StateChange)
def proponer_cambio_estado(pedido_id: int, estado: str):
    """Prepara un cambio de estado. No escribe datos: requiere aprobación del usuario en el chat."""
    return propose_state_change(pedido_id, estado)


@tool(args_schema=ReturnRequest)
def proponer_devolucion(pedido_id: int):
    """Propone registrar un pedido como Devuelto con aprobación humana. No ejecuta reintegros de dinero."""
    return propose_state_change(pedido_id, "Devuelto")
