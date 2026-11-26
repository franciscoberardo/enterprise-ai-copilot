// API Express real con Prisma simulado: las pruebas no acceden a PostgreSQL.
const express = require("../../backend/node_modules/express");
const app = express();
const requests = [];
const clients = [
    {
        id: 1,
        nombre: "Cliente Demo",
        pais: "Argentina",
        email: "demo@test.com",
    },
];
const products = [
    { id: 1, nombre: "Producto Demo", categoria: "Demo", stock: 5 },
];
const orders = [
    {
        id: 1,
        cliente_id: 1,
        estado: "Entregado",
        fecha: "2026-07-01",
        total: "0.10",
        clientes: clients[0],
        detalle_pedidos: [{ producto_id: 1, cantidad: 1 }],
    },
    {
        id: 2,
        cliente_id: 1,
        estado: "Entregado",
        fecha: "2026-07-02",
        total: "0.20",
        clientes: clients[0],
        detalle_pedidos: [],
    },
    {
        id: 3,
        cliente_id: 1,
        estado: "Pendiente",
        fecha: "2026-07-03",
        total: "99.00",
        clientes: clients[0],
        detalle_pedidos: [],
    },
];

function repository(rows) {
    return {
        findMany: async ({ where = {} }) =>
            rows.filter((row) =>
                Object.entries(where).every(([key, value]) => {
                    if (value && typeof value === "object") {
                        if ("contains" in value)
                            return String(row[key])
                                .toLowerCase()
                                .includes(value.contains.toLowerCase());
                        if ("gte" in value) return row[key] >= value.gte;
                    }
                    return row[key] === value;
                }),
            ),
        findUnique: async ({ where }) =>
            rows.find((row) => row.id === where.id) || null,
    };
}

const prismaPath = require.resolve("../../backend/src/prisma");
require.cache[prismaPath] = {
    exports: {
        clientes: repository(clients),
        productos: repository(products),
        pedidos: repository(orders),
    },
};
app.use(express.json());
app.get("/__requests", (req, res) => res.json(requests));
app.use((req, res, next) => {
    requests.push({ method: req.method, path: req.path, query: req.query });
    next();
});
app.use("/clientes", require("../../backend/src/routes/clientes"));
app.use("/productos", require("../../backend/src/routes/productos"));
app.use("/pedidos", require("../../backend/src/routes/pedidos"));
app.listen(Number(process.env.PORT), "127.0.0.1");
