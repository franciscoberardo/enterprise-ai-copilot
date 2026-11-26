import { getDocumentUrl } from "../services/api";
import ActionApproval from "./ActionApproval";

export default function ChatMessage({ message, disabled, onResolve }) {
    const isUser = message.role === "user";

    return (
        <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
            <div
                className={`max-w-[90%] rounded-2xl px-4 py-3 text-sm leading-6 ${isUser ? "rounded-br-sm bg-emerald-800 text-white" : "rounded-bl-sm bg-stone-100 text-slate-700"}`}
            >
                <p className="mb-1 text-[10px] font-semibold tracking-wider uppercase opacity-60">
                    {isUser ? "Vos" : "Copilot"}
                </p>
                <p className="whitespace-pre-wrap break-words">
                    {isUser ? message.text : message.text.replace(/\\?\*/g, "")}
                </p>

                {message.sources?.length > 0 && (
                    <div className="mt-4 border-t border-stone-200 pt-3">
                        <p className="mb-2 text-xs font-medium text-slate-500">
                            Fuentes consultadas
                        </p>
                        <ul className="space-y-1">
                            {message.sources.map(({ document, page }) => (
                                <li key={`${document}:${page}`}>
                                    <a
                                        href={getDocumentUrl(document, page)}
                                        target="_blank"
                                        rel="noreferrer"
                                        className="text-xs text-emerald-800 underline underline-offset-4 hover:text-emerald-950"
                                    >
                                        {document} ·{" "}
                                        {page
                                            ? `página ${page}`
                                            : "página no disponible"}
                                    </a>
                                </li>
                            ))}
                        </ul>
                    </div>
                )}

                {message.actions?.map((action) => (
                    <ActionApproval
                        key={action.id}
                        action={action}
                        disabled={disabled}
                        onResolve={onResolve}
                    />
                ))}
            </div>
        </div>
    );
}
