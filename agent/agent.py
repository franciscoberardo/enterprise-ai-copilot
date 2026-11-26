from models import llm
from prompts import SYSTEM_PROMPT
from services.mcp_agent import MCPAgent
from tools import buscar_documentacion, proponer_cambio_estado, proponer_devolucion

agent = MCPAgent(
    model=llm,
    local_tools=[buscar_documentacion, proponer_cambio_estado, proponer_devolucion],
    prompt=SYSTEM_PROMPT,
)
