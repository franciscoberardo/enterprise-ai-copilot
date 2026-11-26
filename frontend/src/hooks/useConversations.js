import { useEffect, useRef, useState } from "react";
import {
    getConversation,
    getConversations,
    sendMessage,
    resolveAction,
} from "../services/api";

const storageKey = "copilot.conversation";
const emptyConversation = { id: null, messages: [], context: [] };

export default function useConversations() {
    const [conversation, setConversation] = useState(emptyConversation);
    const [conversations, setConversations] = useState([]);
    const [status, setStatus] = useState("opening");
    const [error, setError] = useState("");
    const busy = useRef(true);

    useEffect(() => {
        let active = true;

        async function restore() {
            try {
                const list = await getConversations();
                const savedId = localStorage.getItem(storageKey);
                const saved = list.some(({ id }) => id === savedId)
                    ? await getConversation(savedId)
                    : emptyConversation;

                if (active) {
                    setConversations(list);
                    setConversation(saved);
                    if (!saved.id) localStorage.removeItem(storageKey);
                }
            } catch {
                if (active)
                    setError(
                        "No se pudo cargar el historial. Verificá que el agente esté funcionando.",
                    );
            } finally {
                if (active) {
                    busy.current = false;
                    setStatus(null);
                }
            }
        }

        restore();
        return () => {
            active = false;
        };
    }, []);

    function select(next) {
        setConversation(next);
        setError("");
        if (next.id) localStorage.setItem(storageKey, next.id);
        else localStorage.removeItem(storageKey);
    }

    function startNew() {
        if (!busy.current) select(emptyConversation);
    }

    async function open(id) {
        if (busy.current || id === conversation.id) return;
        if (!id) return startNew();

        busy.current = true;
        setStatus("opening");
        setError("");

        try {
            select(await getConversation(id));
        } catch {
            setError("No se pudo abrir la conversación. Intentá nuevamente.");
        } finally {
            busy.current = false;
            setStatus(null);
        }
    }

    async function send(text) {
        if (busy.current) return false;
        busy.current = true;
        setStatus("sending");
        setError("");
        setConversation({
            ...conversation,
            messages: [...conversation.messages, { role: "user", text }],
        });

        try {
            const result = await sendMessage(text, conversation.id);
            select(result);
            setConversations(result.conversations);
            return true;
        } catch (error) {
            setConversation(conversation);
            setError(
                error.message ||
                    "No se pudo obtener una respuesta. Podés volver a enviar tu consulta.",
            );
            return false;
        } finally {
            busy.current = false;
            setStatus(null);
        }
    }

    async function resolve(actionId, approve) {
        if (busy.current || !conversation.id) return;
        busy.current = true;
        setStatus("resolving");
        setError("");

        try {
            const result = await resolveAction(
                conversation.id,
                actionId,
                approve,
            );
            select(result);
            setConversations(result.conversations);
            window.dispatchEvent(new Event("orders-updated"));
        } catch {
            setError(
                "No se pudo verificar el resultado. Recargá la página para consultar el estado de la acción.",
            );
        } finally {
            busy.current = false;
            setStatus(null);
        }
    }

    return {
        conversation,
        conversations,
        status,
        error,
        open,
        startNew,
        send,
        resolve,
    };
}
