import { toolNames } from "../services/toolLabels";

export default function ConversationContext({
    messages,
    context,
    summary,
    covered,
}) {
    if (!messages.length) return null;

    return (
        <details className="max-h-28 shrink-0 overflow-y-auto border-b border-stone-100 px-5 py-3 text-xs text-slate-500">
            <summary className="font-medium text-emerald-800">
                Contexto · {messages.length}{" "}
                {messages.length === 1 ? "mensaje" : "mensajes"} ·{" "}
                {context.length}{" "}
                {context.length === 1 ? "consulta" : "consultas"}
            </summary>
            <div className="mt-3 space-y-3">
                {summary && (
                    <div className="rounded-lg bg-emerald-50 p-3">
                        <p className="mb-2 font-medium">
                            Resumen activo · {covered} mensajes históricos
                            compactados
                        </p>
                        <p className="whitespace-pre-wrap">
                            {summary.replace(/\\?\*/g, "")}
                        </p>
                    </div>
                )}
                <p>
                    El agente recibe el historial de esta conversación y los
                    resultados de sus herramientas. Una conversación nueva
                    empieza sin ese contexto.
                </p>
                {context.length === 0 && (
                    <p>Todavía no se consultaron herramientas.</p>
                )}
                {context.map(({ tool, text }, index) => (
                    <details key={index} className="rounded-lg bg-stone-50 p-3">
                        <summary>{toolNames[tool] || tool}</summary>
                        <pre className="mt-2 font-sans leading-5 whitespace-pre-wrap break-words">
                            {text.replace(/\\?\*/g, "")}
                        </pre>
                    </details>
                ))}
            </div>
        </details>
    );
}
