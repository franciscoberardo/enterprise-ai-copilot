export default function ConversationMenu({
    conversations,
    currentId,
    disabled,
    onSelect,
    onNew,
    sidebar = false,
}) {
    if (sidebar) {
        return (
            <section
                aria-label="Conversaciones"
                className="mt-6 border-t border-white/10 pt-5"
            >
                <h2 className="mb-3 px-3 text-[10px] font-semibold tracking-[0.18em] text-slate-500 uppercase">
                    Conversaciones
                </h2>
                <button
                    onClick={onNew}
                    disabled={disabled}
                    className="mb-2 w-full rounded-lg px-3 py-2 text-left text-sm font-medium text-emerald-300 hover:bg-white/5 disabled:opacity-40"
                >
                    + Nueva conversación
                </button>
                <div className="max-h-[32dvh] space-y-1 overflow-y-auto">
                    {conversations.map(({ id, title }) => (
                        <button
                            key={id}
                            onClick={() => onSelect(id)}
                            disabled={disabled}
                            title={title}
                            aria-current={id === currentId ? "true" : undefined}
                            className={`block w-full truncate rounded-lg px-3 py-2 text-left text-xs transition disabled:opacity-40 ${id === currentId ? "bg-white/10 text-white" : "text-slate-400 hover:bg-white/5 hover:text-white"}`}
                        >
                            {title}
                        </button>
                    ))}
                    {!conversations.length && (
                        <p className="px-3 text-xs leading-5 text-slate-500">
                            Tus conversaciones aparecerán acá.
                        </p>
                    )}
                </div>
            </section>
        );
    }

    return (
        <div className="flex shrink-0 items-center gap-2 border-b border-stone-100 px-4 py-3">
            <select
                aria-label="Conversaciones guardadas"
                value={currentId || ""}
                disabled={disabled}
                onChange={(event) => onSelect(event.target.value)}
                className="min-w-0 flex-1 rounded-lg border border-stone-200 bg-stone-50 p-2 text-xs text-slate-600 disabled:opacity-50"
            >
                <option value="">Nueva conversación</option>
                {conversations.map(({ id, title }) => (
                    <option key={id} value={id}>
                        {title}
                    </option>
                ))}
            </select>
            <button
                onClick={onNew}
                disabled={disabled}
                className="rounded-lg px-3 py-2 text-xs font-medium text-emerald-800 hover:bg-emerald-50 disabled:opacity-40"
            >
                + Nueva
            </button>
        </div>
    );
}
