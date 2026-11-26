const { test } = require("node:test");
const assert = require("node:assert/strict");

let pedido;
let calls;
const prisma = {
    $transaction: async (run) => run({
        pedidos: {
            updateMany: async (query) => {
                calls.push(query);
                const matches = pedido && pedido.id === query.where.id && pedido.estado === query.where.estado;
                if (matches) pedido.estado = query.data.estado;
                return { count: matches ? 1 : 0 };
            },
            findUnique: async () => pedido,
        },
    }),
};
require.cache[require.resolve("../src/prisma")] = { exports: prisma };
const router = require("../src/routes/pedidos");
const handler = router.stack.find((layer) => layer.route?.path === "/:id/estado").route.stack[0].handle;

async function request(id, body) {
    let status = 200;
    let data;
    await handler({ params: { id }, body }, {
        status(code) { status = code; return this; },
        json(value) { data = value; return this; },
    });
    return { status, data };
}

test("actualiza únicamente el estado esperado y rechaza repetir el cambio", async () => {
    pedido = { id: 2, estado: "Pendiente" };
    calls = [];
    assert.equal((await request("2", { estado: "Enviado", estado_anterior: "Pendiente" })).status, 200);
    assert.deepEqual(calls[0], { where: { id: 2, estado: "Pendiente" }, data: { estado: "Enviado" } });
    assert.equal((await request("2", { estado: "Enviado", estado_anterior: "Pendiente" })).status, 409);
});

test("rechaza estados e identificadores inválidos antes de escribir", async () => {
    calls = [];
    assert.equal((await request("-1", { estado: "Enviado", estado_anterior: "Pendiente" })).status, 400);
    assert.equal((await request("2", { estado: "Inventado", estado_anterior: "Pendiente" })).status, 400);
    assert.equal((await request("2", { estado: "Enviado" })).status, 400);
    assert.equal(calls.length, 0);
});

test("no sobrescribe un pedido modificado ni uno inexistente", async () => {
    calls = [];
    pedido = { id: 2, estado: "Entregado" };
    assert.equal((await request("2", { estado: "Enviado", estado_anterior: "Pendiente" })).status, 409);
    assert.equal(pedido.estado, "Entregado");
    pedido = null;
    assert.equal((await request("2", { estado: "Enviado", estado_anterior: "Pendiente" })).status, 404);
});
