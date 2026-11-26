import { useEffect, useState } from "react";
import Chat from "./Chat";
import DataTable from "./DataTable";
import PageHeading from "./PageHeading";

export default function RecordsPage({ title, description, load }) {
    const [data, setData] = useState([]);
    const [status, setStatus] = useState("loading");

    useEffect(() => {
        let active = true;

        function refresh() {
            load()
                .then((records) => {
                    if (!Array.isArray(records))
                        throw new Error("Respuesta inválida");
                    if (active) {
                        setData(records);
                        setStatus("ready");
                    }
                })
                .catch(() => {
                    if (active) setStatus("error");
                });
        }

        refresh();
        window.addEventListener("orders-updated", refresh);

        return () => {
            active = false;
            window.removeEventListener("orders-updated", refresh);
        };
    }, [load]);

    return (
        <>
            <PageHeading title={title} description={description} />
            <div className="grid items-start gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
                {status === "ready" ? (
                    <DataTable title={title} data={data} />
                ) : (
                    <div
                        className="panel p-10 text-center text-sm text-slate-500"
                        role="status"
                    >
                        {status === "loading"
                            ? "Cargando registros…"
                            : "No se pudieron cargar los datos. Revisá la conexión con el backend y recargá la página."}
                    </div>
                )}
                <Chat compact />
            </div>
        </>
    );
}
