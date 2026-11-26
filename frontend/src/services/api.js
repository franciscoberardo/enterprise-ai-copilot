const API = import.meta.env.VITE_API_URL || "http://localhost:3001";
const AGENT_API = import.meta.env.VITE_AGENT_API_URL || "http://localhost:8000";

async function request(url, options) {
    const response = await fetch(url, options);

    if (!response.ok) {
        const body = await response.json().catch(() => null);
        const detail = typeof body?.detail === "string" ? body.detail : null;
        throw new Error(
            detail || `Error al consultar el servicio (${response.status})`,
        );
    }

    return response.json();
}

export const getClientes = () => request(`${API}/clientes`);
export const getProductos = () => request(`${API}/productos`);
export const getPedidos = () => request(`${API}/pedidos`);

export const getConversations = () => request(`${AGENT_API}/conversations`);
export const getConversation = (id) =>
    request(`${AGENT_API}/conversations/${id}`);

export function sendMessage(message, conversationId = null) {
    return request(`${AGENT_API}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message, conversation_id: conversationId }),
    });
}

export function resolveAction(conversationId, actionId, approve) {
    return request(
        `${AGENT_API}/conversations/${conversationId}/actions/${actionId}`,
        {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ approve }),
        },
    );
}

export function getDocumentUrl(document, page) {
    const anchor = Number.isInteger(page) && page > 0 ? `#page=${page}` : "";
    return `${AGENT_API}/documents/${encodeURIComponent(document)}${anchor}`;
}

export const getDocuments = () => request(`${AGENT_API}/documents`);

export function uploadDocument(file) {
    const body = new FormData();
    body.append("file", file);
    return request(`${AGENT_API}/documents`, { method: "POST", body });
}
