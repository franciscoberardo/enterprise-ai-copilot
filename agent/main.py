from pathlib import Path
from uuid import UUID

from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, StrictBool

from agent import agent
from services.conversations import ConversationStore, conversation_view
from services.order_actions import execute_order_action
from services.mcp_agent import MCPUnavailable
from services.settings import settings

UPLOADS = (Path(__file__).parent.parent / "backend" / "uploads").resolve()

app = FastAPI()
conversations = ConversationStore(Path(__file__).parent / "data" / "conversations.sqlite3")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    conversation_id: UUID | None = None


@app.get("/conversations")
def list_conversations():
    return conversations.list()


@app.get("/conversations/{conversation_id}")
def get_conversation(conversation_id: UUID):
    try:
        return conversation_view(conversations.get(str(conversation_id)))
    except KeyError:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")


@app.post("/chat")
def chat(req: ChatRequest):
    question = req.message.strip()
    if not question:
        raise HTTPException(status_code=422, detail="Escribí una consulta")

    conversation_id = str(req.conversation_id) if req.conversation_id else None
    if conversation_id:
        try:
            conversations.get(conversation_id)
        except KeyError:
            raise HTTPException(status_code=404, detail="Conversación no encontrada")

    try:
        result = conversations.reply(conversation_id, question, agent.invoke)
    except MCPUnavailable as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail="No se pudo obtener una respuesta del agente. Intentá nuevamente.",
        ) from error

    return {**result, "conversations": conversations.list()}


class ApprovalRequest(BaseModel):
    approve: StrictBool


@app.post("/conversations/{conversation_id}/actions/{action_id}")
def resolve_action(conversation_id: UUID, action_id: UUID, req: ApprovalRequest):
    try:
        result = conversations.resolve(
            str(conversation_id), str(action_id), req.approve, execute_order_action
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Acción o conversación no encontrada")
    return {**result, "conversations": conversations.list()}


@app.get("/documents/{filename}")
def get_document(filename: str):
    path = (UPLOADS / filename).resolve()
    if path.parent != UPLOADS or path.suffix.lower() != ".pdf" or not path.is_file():
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    return FileResponse(path, media_type="application/pdf", filename=path.name, content_disposition_type="inline")


@app.get("/documents")
def list_documents():
    from services.rag_service import vectorstore
    try:
        return vectorstore.sync()
    except Exception as error:
        raise HTTPException(status_code=503, detail="No se pudieron sincronizar los documentos") from error


@app.post("/documents")
def upload_document(file: UploadFile = File(...)):
    from services.rag_service import vectorstore
    data = file.file.read(10 * 1024 * 1024 + 1)
    if len(data) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="El PDF debe pesar como máximo 10 MB")
    try:
        return vectorstore.upload(file.filename or "", data)
    except Exception as error:
        raise HTTPException(status_code=422, detail="No se pudo indexar el PDF. Verificá que contenga texto y no esté protegido.") from error


@app.get("/health")
def health():
    return {"status": "ok"}
