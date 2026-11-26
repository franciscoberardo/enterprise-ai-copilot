import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from uuid import uuid4

from langchain_core.messages import AIMessage, HumanMessage, messages_from_dict, messages_to_dict

from services.order_actions import ActionExecutionError, OrderAction

PROPOSAL_TOOLS = {"proponer_cambio_estado", "proponer_devolucion"}


def content_text(content):
    if isinstance(content, str):
        return content
    return "\n".join(
        block if isinstance(block, str) else block.get("text", "")
        for block in content
    )


def tool_data(message):
    try:
        data = json.loads(content_text(message.content))
        return data if isinstance(data, dict) else {}
    except (ValueError, TypeError):
        return {}


def conversation_view(conversation):
    visible = []
    sources = {}
    messages = conversation["messages"]

    for index, message in enumerate(messages):
        if message.type == "human":
            sources = {}
            visible.append({"role": "user", "text": content_text(message.content)})
        elif message.type == "tool" and message.name == "buscar_documentacion":
            for fragment in tool_data(message).get("fragments", []):
                document, page = fragment.get("document"), fragment.get("page")
                if document:
                    sources[(document, page)] = {"document": document, "page": page}
        elif message.type == "ai" and not message.tool_calls:
            visible.append({
                "role": "assistant",
                "text": content_text(message.content),
                "sources": list(sources.values()),
                "actions": [
                    action for action in conversation.get("actions", [])
                    if action["message_index"] == index
                ],
            })

    return {
        "id": conversation["id"],
        "title": conversation["title"],
        "context_summary": conversation.get("context_summary", ""),
        "summary_until": conversation.get("summary_until", 0),
        "messages": visible,
        "context": [
            {"tool": message.name, "text": content_text(message.content)}
            for message in messages if message.type == "tool"
        ],
    }


class ConversationStore:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = Lock()
        with closing(self.connect()) as connection, connection:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    messages TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS order_actions (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL REFERENCES conversations(id),
                    message_index INTEGER NOT NULL,
                    payload TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    result TEXT
                );
            """)

            columns = {row[1] for row in connection.execute("PRAGMA table_info(conversations)")}
            for name, definition in {
                "context_summary": "TEXT NOT NULL DEFAULT ''",
                "summary_until": "INTEGER NOT NULL DEFAULT 0",
            }.items():
                if name not in columns:
                    connection.execute(f"ALTER TABLE conversations ADD COLUMN {name} {definition}")

    def connect(self):
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def list(self):
        with closing(self.connect()) as connection:
            rows = connection.execute(
                "SELECT id, title, updated_at FROM conversations ORDER BY updated_at DESC"
            ).fetchall()
        return [dict(row) for row in rows]

    def get(self, conversation_id):
        with closing(self.connect()) as connection:
            row = connection.execute(
                "SELECT * FROM conversations WHERE id = ?", (conversation_id,)
            ).fetchone()
            actions = connection.execute(
                "SELECT * FROM order_actions WHERE conversation_id = ? ORDER BY rowid",
                (conversation_id,),
            ).fetchall()
        if row is None:
            raise KeyError(conversation_id)
        return {
            **dict(row),
            "messages": messages_from_dict(json.loads(row["messages"])),
            "actions": [{**dict(action), "payload": json.loads(action["payload"])} for action in actions],
        }

    def save(self, connection, conversation, messages):
        connection.execute("""
            INSERT INTO conversations (id, title, messages, updated_at, context_summary, summary_until)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                messages = excluded.messages,
                updated_at = excluded.updated_at,
                context_summary = excluded.context_summary,
                summary_until = excluded.summary_until
        """, (
            conversation["id"], conversation["title"],
            json.dumps(messages_to_dict(messages), ensure_ascii=False),
            datetime.now(timezone.utc).isoformat(),
            conversation.get("context_summary", ""), conversation.get("summary_until", 0),
        ))

    def reply(self, conversation_id, question, invoke):
        with self.lock:
            conversation = self.get(conversation_id) if conversation_id else {
                "id": str(uuid4()), "title": question[:70], "messages": [], "actions": [],
            }
            result = invoke({
                "messages": [*conversation["messages"], HumanMessage(content=question)],
                "context_summary": conversation.get("context_summary", ""),
                "summary_until": conversation.get("summary_until", 0),
            })
            messages = result["messages"]
            if not messages or messages[-1].type != "ai":
                raise ValueError("El agente no devolvió una respuesta")
            response = content_text(messages[-1].content)
            if not response.strip():
                raise ValueError("El agente devolvió una respuesta vacía")

            conversation.update(
                context_summary=result.get("context_summary", conversation.get("context_summary", "")),
                summary_until=result.get("summary_until", conversation.get("summary_until", 0)),
            )
            proposals = {}
            for message in messages[len(conversation["messages"]):]:
                if message.type == "tool" and message.name in PROPOSAL_TOOLS:
                    data = tool_data(message)
                    if data.get("requires_approval") is True and data.get("action"):
                        action = OrderAction.model_validate(data["action"])
                        proposals[action.pedido_id] = action

            with closing(self.connect()) as connection, connection:
                self.save(connection, conversation, messages)
                for action in proposals.values():
                    for previous in conversation["actions"]:
                        if previous["status"] == "pending" and previous["payload"]["pedido_id"] == action.pedido_id:
                            connection.execute(
                                "UPDATE order_actions SET status = 'cancelled', result = ? WHERE id = ? AND status = 'pending'",
                                ("Reemplazada por una nueva propuesta.", previous["id"]),
                            )
                    connection.execute("""
                        INSERT INTO order_actions (id, conversation_id, message_index, payload)
                        VALUES (?, ?, ?, ?)
                    """, (str(uuid4()), conversation["id"], len(messages) - 1, action.model_dump_json()))

            return {"response": response, **conversation_view(self.get(conversation["id"]))}

    def resolve(self, conversation_id, action_id, approve, execute):
        with self.lock:
            conversation = self.get(conversation_id)
            action = next((item for item in conversation["actions"] if item["id"] == action_id), None)
            if action is None:
                raise KeyError(action_id)
            if action["status"] != "pending":
                return conversation_view(conversation)

            # Reserva duradera antes de la escritura remota: no se reejecuta por doble clic.
            with closing(self.connect()) as connection, connection:
                claimed = connection.execute(
                    "UPDATE order_actions SET status = 'executing' WHERE id = ? AND status = 'pending'",
                    (action_id,),
                ).rowcount
            if not claimed:
                return conversation_view(self.get(conversation_id))

            payload = action["payload"]
            description = f"pedido {payload['pedido_id']}: {payload['estado_anterior'] or 'Sin estado'} → {payload['estado_nuevo']}"
            if not approve:
                status, text = "cancelled", "Acción cancelada. No se modificó el pedido."
            else:
                try:
                    text = execute(payload)
                    status = "executed"
                except ActionExecutionError as error:
                    status, text = "failed", str(error)
                except Exception:
                    status, text = "failed", "No se pudo confirmar el resultado. Consultá el pedido antes de volver a solicitar el cambio."

            messages = [
                *conversation["messages"],
                HumanMessage(content=f"{'Confirmé' if approve else 'Cancelé'} el cambio de {description}."),
                AIMessage(content=text),
            ]
            with closing(self.connect()) as connection, connection:
                connection.execute(
                    "UPDATE order_actions SET status = ?, result = ? WHERE id = ?",
                    (status, text, action_id),
                )
                self.save(connection, conversation, messages)
            return {"response": text, **conversation_view(self.get(conversation_id))}
