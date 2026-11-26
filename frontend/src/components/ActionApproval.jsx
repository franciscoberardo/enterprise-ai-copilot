const statuses = {
    pending: "Pendiente de tu confirmación",
    executing: "Confirmación en curso. Consultá el pedido si no termina.",
    executed: "Cambio realizado",
    cancelled: "Acción cancelada",
    failed: "No se pudo completar la confirmación",
};

export default function ActionApproval({ action, disabled, onResolve }) {
    const { pedido_id, estado_anterior, estado_nuevo } = action.payload;

    return (
        <div
            id={`approval-${action.id}`}
            className="mt-4 scroll-mt-4 rounded-xl border border-stone-200 bg-white p-4 text-slate-700"
        >
            <p className="text-xs font-semibold text-emerald-800">
                {statuses[action.status]}
            </p>
            <p className="mt-2 font-medium">Pedido {pedido_id}</p>
            <p className="mt-1 text-xs">
                {estado_anterior || "Sin estado"} → {estado_nuevo}
            </p>
            {estado_nuevo === "Devuelto" && (
                <p className="mt-2 text-xs text-slate-500">
                    Registra la devolución; no emite un reintegro de dinero.
                </p>
            )}
            {action.result && (
                <p className="mt-2 text-xs leading-5">{action.result}</p>
            )}
            {action.status === "pending" && (
                <div className="mt-4 flex flex-wrap gap-2">
                    <button
                        type="button"
                        disabled={disabled}
                        onClick={() => onResolve(action.id, true)}
                        className="rounded-lg bg-emerald-800 px-4 py-2 text-xs font-medium text-white hover:bg-emerald-900 disabled:opacity-40"
                    >
                        Confirmar
                    </button>
                    <button
                        type="button"
                        disabled={disabled}
                        onClick={() => onResolve(action.id, false)}
                        className="rounded-lg border border-stone-200 px-4 py-2 text-xs font-medium hover:bg-stone-50 disabled:opacity-40"
                    >
                        Cancelar
                    </button>
                </div>
            )}
        </div>
    );
}
