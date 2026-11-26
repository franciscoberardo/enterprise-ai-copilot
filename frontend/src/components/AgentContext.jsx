import { getDocumentUrl } from "../services/api";
import { toolNames } from "../services/toolLabels";

function ContextSection({ title, empty, children }) {
    return (
        <section className="mt-5">
            <h3 className="mb-2 text-xs font-semibold text-slate-800">
                {title}
            </h3>
            {children || (
                <p className="rounded-lg bg-slate-50 px-3 py-3 text-xs leading-5 text-slate-500">
                    {empty}
                </p>
            )}
        </section>
    );
}

export default function AgentContext({ conversation }) {
    const {
        messages,
        context,
        context_summary: summary,
        summary_until: covered,
    } = conversation;
    const sources = [
        ...new Map(
            messages
                .flatMap((message) => message.sources || [])
                .map((source) => [`${source.document}:${source.page}`, source]),
        ).values(),
    ];
    const pending = messages
        .flatMap((message) => message.actions || [])
        .filter((action) => action.status === "pending");

    return (
        <aside
            aria-label="Contexto del agente"
            className="panel p-5 lg:h-[calc(100dvh-104px)] lg:overflow-y-auto"
        >
            <h2 className="border-b border-slate-200 pb-3 text-sm font-semibold">
                Contexto del agente
            </h2>
            <p className="mt-4 text-[10px] font-semibold tracking-wider text-slate-500 uppercase">
                Capacidades disponibles
            </p>
            <ul className="mt-3 space-y-2.5 text-xs text-slate-600">
                {[
                    "Consultas de negocio vía MCP",
                    "Análisis de pedidos",
                    "Métricas de ventas",
                    "Búsqueda semántica en PDFs (RAG)",
                    "Fuentes con documento y página",
                    "Memoria conversacional persistente",
                    "Resumen automático del contexto",
                    "Carga e indexación incremental de PDFs",
                    "Aprobación humana de operaciones",
                    "Cambios de estado y devoluciones",
                ].map((label) => (
                    <li key={label} className="flex items-center gap-2">
                        <span className="size-1.5 shrink-0 rounded-full bg-emerald-500" />
                        {label}
                    </li>
                ))}
            </ul>
            <div className="mt-5 border-t border-slate-200">
                <ContextSection
                    title="Ejecución de herramientas"
                    empty="Todavía no se ejecutaron herramientas."
                >
                    {context.length > 0 && (
                        <div className="space-y-2">
                            {context.map(({ tool, text }, index) => (
                                <details
                                    key={index}
                                    className="rounded-lg bg-slate-50 p-3 text-xs text-slate-600"
                                >
                                    <summary className="font-medium">
                                        {toolNames[tool] || tool}
                                    </summary>
                                    <pre className="mt-2 max-h-40 overflow-y-auto font-sans leading-5 whitespace-pre-wrap break-words">
                                        {text.replace(/\\?\*/g, "")}
                                    </pre>
                                </details>
                            ))}
                        </div>
                    )}
                </ContextSection>
                <ContextSection
                    title="Fuentes recuperadas"
                    empty="Todavía no se recuperaron fuentes."
                >
                    {sources.length > 0 && (
                        <ul className="space-y-2">
                            {sources.map(({ document, page }) => (
                                <li key={`${document}:${page}`}>
                                    <a
                                        href={getDocumentUrl(document, page)}
                                        target="_blank"
                                        rel="noreferrer"
                                        className="block rounded-lg bg-slate-50 p-3 text-xs leading-5 break-words text-emerald-800 hover:bg-emerald-50"
                                    >
                                        {document}
                                        <span className="block text-slate-500">
                                            {page
                                                ? `Página ${page}`
                                                : "Página no disponible"}
                                        </span>
                                    </a>
                                </li>
                            ))}
                        </ul>
                    )}
                </ContextSection>
                <ContextSection
                    title="Aprobaciones pendientes"
                    empty="No hay acciones pendientes."
                >
                    {pending.length > 0 && (
                        <ul className="space-y-2">
                            {pending.map((action) => (
                                <li
                                    key={action.id}
                                    className="rounded-lg border border-amber-100 bg-amber-50 p-3 text-xs leading-5"
                                >
                                    <p className="font-medium">
                                        Pedido {action.payload.pedido_id} →{" "}
                                        {action.payload.estado_nuevo}
                                    </p>
                                    <a
                                        href={`#approval-${action.id}`}
                                        className="text-emerald-800 underline underline-offset-2"
                                    >
                                        Revisar propuesta
                                    </a>
                                </li>
                            ))}
                        </ul>
                    )}
                </ContextSection>
                {messages.length > 0 && (
                    <ContextSection title="Memoria de la conversación">
                        <p className="text-xs text-slate-500">
                            {messages.length} mensajes en el historial
                        </p>
                        {summary && (
                            <details className="mt-2 rounded-lg bg-emerald-50 p-3 text-xs leading-5 text-slate-600">
                                <summary>
                                    Resumen activo · {covered} mensajes
                                    compactados
                                </summary>
                                <p className="mt-2 whitespace-pre-wrap">
                                    {summary.replace(/\\?\*/g, "")}
                                </p>
                            </details>
                        )}
                    </ContextSection>
                )}
            </div>
        </aside>
    );
}
