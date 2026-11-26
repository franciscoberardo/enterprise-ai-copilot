import { useState } from "react";
import Icon from "./Icon";

const labels = {
    id: "ID",
    nombre: "Nombre",
    email: "Email",
    pais: "País",
    categoria: "Categoría",
    precio: "Precio",
    stock: "Stock",
    cliente_id: "Cliente ID",
    fecha: "Fecha",
    total: "Total",
    estado: "Estado",
    clientes: "Cliente",
    detalle_pedidos: "Detalle",
};

function Cell({ column, value }) {
    if (value == null) return <span className="text-slate-300">—</span>;

    if (column === "estado") {
        const colors = {
            Entregado: "bg-emerald-50 text-emerald-700",
            Pendiente: "bg-amber-50 text-amber-800",
            Enviado: "bg-blue-50 text-blue-700",
        };
        return (
            <span
                className={`rounded-full px-2.5 py-1 text-xs font-medium ${colors[value] || "bg-stone-100 text-slate-600"}`}
            >
                {value}
            </span>
        );
    }

    if (column === "fecha")
        return new Intl.DateTimeFormat("es-AR", { timeZone: "UTC" }).format(
            new Date(value),
        );
    if (column === "precio" || column === "total")
        return Number(value).toLocaleString("es-AR", {
            minimumFractionDigits: 2,
        });
    if (column === "clientes" && value.nombre) return value.nombre;

    if (typeof value === "object") {
        return (
            <details className="max-w-xs">
                <summary className="text-xs font-medium text-emerald-700">
                    Ver detalle
                    {Array.isArray(value) ? ` (${value.length})` : ""}
                </summary>
                <pre className="mt-2 max-h-48 overflow-auto rounded-lg bg-stone-50 p-3 text-xs">
                    {JSON.stringify(value, null, 2)}
                </pre>
            </details>
        );
    }

    return String(value);
}

export default function DataTable({ title, data }) {
    const [search, setSearch] = useState("");
    const columns = Object.keys(data[0] || {});
    const rows = data.filter((row) =>
        JSON.stringify(row)
            .toLocaleLowerCase()
            .includes(search.toLocaleLowerCase()),
    );

    return (
        <section className="panel min-w-0 overflow-hidden">
            <div className="flex flex-wrap items-center justify-between gap-4 border-b border-stone-100 p-5">
                <div className="flex items-center gap-2">
                    <h2 className="font-semibold">{title}</h2>
                    <span className="rounded-md bg-stone-100 px-2 py-0.5 text-xs text-slate-500">
                        {data.length}
                    </span>
                </div>
                <label className="flex items-center gap-2 rounded-lg border border-stone-200 px-3 py-2 text-slate-400">
                    <Icon name="search" className="size-4" />
                    <input
                        aria-label={`Buscar en ${title.toLowerCase()}`}
                        value={search}
                        onChange={(event) => setSearch(event.target.value)}
                        placeholder="Buscar…"
                        className="w-32 text-sm text-slate-700 outline-none sm:w-40"
                    />
                </label>
            </div>

            <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                    <thead className="bg-stone-50 text-xs text-slate-500">
                        <tr>
                            {columns.map((column) => (
                                <th
                                    scope="col"
                                    key={column}
                                    className="px-5 py-3 font-medium whitespace-nowrap"
                                >
                                    {labels[column] || column}
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-stone-100">
                        {rows.map((row, index) => (
                            <tr
                                key={row.id ?? index}
                                className="transition-colors hover:bg-stone-50/70"
                            >
                                {columns.map((column) => (
                                    <td
                                        key={column}
                                        className="px-5 py-4 align-top whitespace-nowrap"
                                    >
                                        <Cell
                                            column={column}
                                            value={row[column]}
                                        />
                                    </td>
                                ))}
                            </tr>
                        ))}
                    </tbody>
                </table>
                {!rows.length && (
                    <p className="p-10 text-center text-sm text-slate-500">
                        {search
                            ? "No hay resultados para tu búsqueda."
                            : "Todavía no hay registros."}
                    </p>
                )}
            </div>
        </section>
    );
}
