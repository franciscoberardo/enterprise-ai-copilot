import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import AgentContext from "./AgentContext";
import useConversations from "../hooks/useConversations";
import ConversationMenu from "./ConversationMenu";
import ConversationContext from "./ConversationContext";
import Icon from "./Icon";
import ChatMessage from "./ChatMessage";

const suggestions = [
    {
        title: "Ventas y métricas",
        description: "Analizá los datos del negocio",
        question: "¿Cuánto suman los pedidos entregados?",
    },
    {
        title: "Gestión de pedidos",
        description: "Revisá los pedidos pendientes",
        question: "Mostrame los pedidos pendientes",
    },
    {
        title: "Inventario",
        description: "Explorá los productos y su stock",
        question: "Mostrame los productos y su stock",
    },
    {
        title: "Base de conocimiento",
        description: "Consultá los documentos internos",
        question: "¿Cuál es la política de devoluciones?",
    },
];

export default function Chat({ compact = false }) {
    const [input, setInput] = useState("");
    const [menuTarget, setMenuTarget] = useState(null);
    const {
        conversation,
        conversations,
        status,
        error,
        open,
        startNew,
        resolve,
        send: sendQuestion,
    } = useConversations();
    const { messages, context } = conversation;
    const loading = status === "sending";
    const disabled = Boolean(status);
    const endRef = useRef(null);

    useEffect(() => {
        setMenuTarget(document.getElementById("conversation-navigation"));
    }, []);

    useEffect(() => {
        endRef.current?.scrollIntoView({
            block: "nearest",
            behavior: "smooth",
        });
    }, [messages, loading]);

    async function send(question = input) {
        const text = question.trim();
        if (!text || disabled) return;

        setInput("");
        if (!(await sendQuestion(text))) setInput(text);
    }

    const menuProps = {
        conversations,
        currentId: conversation.id,
        disabled,
        onSelect: (id) => {
            setInput("");
            open(id);
        },
        onNew: () => {
            setInput("");
            startNew();
        },
    };

    return (
        <div
            className={
                compact
                    ? "min-w-0"
                    : "grid items-start gap-4 lg:grid-cols-[minmax(0,1fr)_260px]"
            }
        >
            {menuTarget &&
                createPortal(
                    <ConversationMenu {...menuProps} sidebar />,
                    menuTarget,
                )}
            <section
                aria-label="Chat con el asistente"
                className={`panel flex min-w-0 flex-col ${compact ? "h-[580px] min-h-[400px] xl:max-h-[calc(100dvh-280px)]" : "h-[620px] min-h-[480px] lg:h-[calc(100dvh-104px)]"}`}
            >
                {!compact && (
                    <div className="flex shrink-0 justify-end px-5 pt-4">
                        <button
                            type="button"
                            onClick={menuProps.onNew}
                            disabled={disabled}
                            className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs font-medium text-emerald-800 transition hover:bg-emerald-100 disabled:cursor-not-allowed disabled:opacity-40"
                        >
                            + Nueva conversación
                        </button>
                    </div>
                )}
                {(compact || messages.length > 0) && (
                    <header className="flex shrink-0 items-center gap-3 border-b border-stone-100 px-5 py-4">
                        <span className="rounded-xl bg-emerald-50 p-2 text-emerald-700">
                            <Icon name="spark" />
                        </span>
                        <div>
                            <h2 className="text-sm font-semibold">
                                Asistente de negocio
                            </h2>
                            <p className="mt-0.5 text-xs text-slate-400">
                                Consultá tus datos y documentos
                            </p>
                        </div>
                    </header>
                )}

                <div className="lg:hidden">
                    <ConversationMenu {...menuProps} />
                </div>
                {compact && (
                    <ConversationContext
                        messages={messages}
                        context={context}
                        summary={conversation.context_summary}
                        covered={conversation.summary_until}
                    />
                )}
                {error && (
                    <p
                        role="alert"
                        className="shrink-0 bg-red-50 px-5 py-3 text-xs text-red-800"
                    >
                        {error}
                    </p>
                )}

                <div
                    role="log"
                    aria-live="polite"
                    aria-busy={disabled}
                    className="min-h-0 flex-1 space-y-5 overflow-y-auto p-5 sm:p-6"
                >
                    {!messages.length && !disabled && (
                        <div className="mx-auto flex min-h-full w-full max-w-2xl flex-col items-center justify-center py-3 text-center">
                            <span className="mb-4 rounded-2xl bg-emerald-50 p-3 text-emerald-700">
                                <Icon name="spark" className="size-6" />
                            </span>
                            <h3 className="text-xl font-semibold tracking-tight">
                                ¿En qué te ayudo?
                            </h3>
                            {!compact && (
                                <p className="mt-2 max-w-sm text-sm leading-6 text-slate-500">
                                    Explorá los datos de tu negocio con IA.
                                </p>
                            )}
                            <div
                                className={`mt-6 grid w-full gap-3 text-left ${compact ? "grid-cols-1" : "sm:grid-cols-2"}`}
                            >
                                {suggestions.map(
                                    ({ title, description, question }) => (
                                        <button
                                            key={title}
                                            disabled={disabled}
                                            onClick={() => send(question)}
                                            className="group rounded-xl border border-slate-200 bg-slate-50/70 p-4 text-left transition hover:border-emerald-300 hover:bg-emerald-50 disabled:opacity-40"
                                        >
                                            <span className="mb-2 block size-2.5 rounded-full bg-emerald-500" />
                                            <span className="block text-sm font-semibold text-slate-800">
                                                {title}
                                            </span>
                                            <span className="mt-1 block text-xs leading-5 text-slate-500">
                                                {description}
                                            </span>
                                        </button>
                                    ),
                                )}
                            </div>
                        </div>
                    )}

                    {messages.map((message, index) => (
                        <ChatMessage
                            key={index}
                            message={message}
                            disabled={disabled}
                            onResolve={resolve}
                        />
                    ))}

                    {status === "resolving" && (
                        <p role="status" className="text-sm text-slate-500">
                            Aplicando tu decisión…
                        </p>
                    )}
                    {status === "opening" && (
                        <p role="status" className="text-sm text-slate-500">
                            Cargando conversación…
                        </p>
                    )}
                    {loading && (
                        <p
                            role="status"
                            className="animate-pulse text-sm text-slate-500"
                        >
                            Copilot está preparando tu respuesta…
                        </p>
                    )}
                    {messages.length > 0 && <div ref={endRef} />}
                </div>

                <form
                    onSubmit={(event) => {
                        event.preventDefault();
                        send();
                    }}
                    className="shrink-0 p-4 pt-2"
                >
                    <div className="flex items-center gap-2 rounded-xl border border-stone-200 bg-stone-50 p-2 focus-within:border-emerald-500">
                        <input
                            aria-label="Tu consulta"
                            value={input}
                            onChange={(event) => setInput(event.target.value)}
                            placeholder="Preguntá sobre tu negocio…"
                            className="min-w-0 flex-1 bg-transparent px-2 py-2 text-sm outline-none focus-visible:outline-none"
                        />
                        <button
                            type="submit"
                            disabled={disabled || !input.trim()}
                            aria-label="Enviar consulta"
                            className="rounded-lg bg-emerald-800 p-2.5 text-white transition hover:bg-emerald-900 disabled:cursor-not-allowed disabled:opacity-40"
                        >
                            <Icon name="arrow" />
                        </button>
                    </div>
                    <p className="mt-2 text-center text-[10px] text-slate-400">
                        La IA puede cometer errores. Verificá la información
                        importante.
                    </p>
                </form>
            </section>
            {!compact && <AgentContext conversation={conversation} />}
        </div>
    );
}
