import PageHeading from "../components/PageHeading";

const condiciones = [
    {
        titulo: "Plazo para solicitarla",
        texto: "Los clientes pueden solicitar una devolución dentro de los 30 días posteriores a la compra.",
    },
    {
        titulo: "Estado del producto",
        texto: "El producto debe encontrarse en buen estado y con su embalaje original.",
    },
    {
        titulo: "Reintegro",
        texto: "Una vez aprobada la devolución, el reintegro se realizará dentro de los 5 días hábiles utilizando el mismo medio de pago.",
    },
    {
        titulo: "Productos excluidos",
        texto: "No se aceptan devoluciones de productos dañados por mal uso.",
    },
];

export default function PoliticaDevolucion() {
    return (
        <article className="mx-auto max-w-4xl">
            <PageHeading
                title="Política de devolución"
                description="Las condiciones para solicitar una devolución, en un solo lugar."
            />
            <div className="grid gap-4 sm:grid-cols-2">
                {condiciones.map(({ titulo, texto }, index) => (
                    <section key={titulo} className="panel p-6 sm:p-8">
                        <span className="mb-6 flex size-9 items-center justify-center rounded-xl bg-emerald-50 text-xs font-semibold text-emerald-800">
                            0{index + 1}
                        </span>
                        <h2 className="mb-3 text-lg font-semibold tracking-tight">
                            {titulo}
                        </h2>
                        <p className="text-sm leading-7 text-slate-500">
                            {texto}
                        </p>
                    </section>
                ))}
            </div>
            <p className="mt-6 text-xs text-slate-400">
                Fuente: politica_devoluciones.pdf
            </p>
        </article>
    );
}
