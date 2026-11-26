import { useEffect, useState } from "react";
import PageHeading from "../components/PageHeading";
import { getDocuments, uploadDocument, getDocumentUrl } from "../services/api";

export default function Documentos() {
    const [documents, setDocuments] = useState([]);
    const [file, setFile] = useState(null);
    const [busy, setBusy] = useState(true);
    const [error, setError] = useState("");
    const [notice, setNotice] = useState("");

    useEffect(() => {
        let active = true;
        getDocuments()
            .then((data) => {
                if (active) setDocuments(data);
            })
            .catch((error) => {
                if (active) setError(error.message);
            })
            .finally(() => {
                if (active) setBusy(false);
            });
        return () => {
            active = false;
        };
    }, []);

    async function upload(event) {
        event.preventDefault();
        if (!file || busy) return;
        if (file.size > 10 * 1024 * 1024) {
            setError("El PDF debe pesar como máximo 10 MB");
            return;
        }
        setBusy(true);
        setError("");
        setNotice("");
        try {
            setDocuments(await uploadDocument(file));
            setNotice("PDF indexado. Ya podés consultarlo en el chat.");
            setFile(null);
            event.target.reset();
        } catch (error) {
            setError(error.message);
        } finally {
            setBusy(false);
        }
    }

    return (
        <div className="mx-auto max-w-4xl">
            <PageHeading
                title="Documentos"
                description="Agregá PDFs al conocimiento del asistente. Un archivo con el mismo nombre reemplaza su versión anterior; los demás no se vuelven a indexar."
            />
            <form onSubmit={upload} className="panel mb-6 space-y-4 p-6">
                <label className="block text-sm font-medium" htmlFor="document">
                    Subir PDF con texto · máximo 10 MB
                </label>
                <input
                    id="document"
                    type="file"
                    accept=".pdf,application/pdf"
                    disabled={busy}
                    onChange={(event) => setFile(event.target.files[0] || null)}
                    className="block w-full text-sm file:mr-4 file:rounded-lg file:border-0 file:bg-emerald-50 file:px-4 file:py-2 file:text-emerald-800"
                />
                <button
                    disabled={busy || !file}
                    className="rounded-lg bg-emerald-800 px-4 py-2 text-sm text-white disabled:opacity-40"
                >
                    {busy ? "Sincronizando…" : "Subir e indexar"}
                </button>
                {error && (
                    <p role="alert" className="text-sm text-red-700">
                        {error}
                    </p>
                )}
                {notice && (
                    <p role="status" className="text-sm text-emerald-700">
                        {notice}
                    </p>
                )}
            </form>
            <section className="panel divide-y divide-stone-100">
                {!documents.length && !busy && (
                    <p className="p-6 text-sm text-slate-500">
                        Todavía no hay PDFs indexados.
                    </p>
                )}
                {documents.map(({ name, pages, chunks }) => (
                    <div
                        key={name}
                        className="flex flex-wrap items-center justify-between gap-3 p-5 text-sm"
                    >
                        <a
                            href={getDocumentUrl(name, 1)}
                            target="_blank"
                            rel="noreferrer"
                            className="break-all font-medium text-emerald-800 underline underline-offset-4"
                        >
                            {name}
                        </a>
                        <span className="text-xs text-slate-500">
                            {pages} páginas · {chunks} fragmentos
                        </span>
                    </div>
                ))}
            </section>
        </div>
    );
}
