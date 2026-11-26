const router = require("express").Router();
const prisma = require("../prisma");

// Obtener todos
router.get("/", async (req, res) => {
  try {
    const { estado, cliente } = req.query;

    const pedidos = await prisma.pedidos.findMany({
      where: {
        ...(estado && { estado }),
        ...(cliente && {
          cliente_id: Number(cliente),
        }),
      },
      include: {
        clientes: true,
        detalle_pedidos: {
          include: {
            productos: true,
          },
        },
      },
    });

    res.json(pedidos);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Obtener uno
router.get("/:id", async (req, res) => {
  try {
    const pedido = await prisma.pedidos.findUnique({
      where: {
        id: Number(req.params.id),
      },
      include: {
        clientes: true,
        detalle_pedidos: {
          include: {
            productos: true,
          },
        },
      },
    });

    if (!pedido)
      return res.status(404).json({ error: "Pedido no encontrado" });

    res.json(pedido);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Crear
router.post("/", async (req, res) => {
  try {
    const pedido = await prisma.pedidos.create({
      data: req.body,
    });

    res.status(201).json(pedido);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Aplica el cambio solo si el estado sigue siendo el que aprobó el usuario.
router.patch("/:id/estado", async (req, res) => {
  const id = Number(req.params.id);
  const { estado, estado_anterior } = req.body;
  const estados = ["Pendiente", "Enviado", "Entregado", "Cancelado", "Devuelto"];

  if (!Number.isSafeInteger(id) || id <= 0 || !estados.includes(estado) ||
      !Object.hasOwn(req.body, "estado_anterior") ||
      (estado_anterior !== null && typeof estado_anterior !== "string")) {
    return res.status(400).json({ error: "Pedido o estado inválido" });
  }

  try {
    const result = await prisma.$transaction(async (tx) => {
      const changed = await tx.pedidos.updateMany({
        where: { id, estado: estado_anterior },
        data: { estado },
      });
      const pedido = await tx.pedidos.findUnique({ where: { id } });
      return { changed: changed.count, pedido };
    });

    if (!result.pedido) return res.status(404).json({ error: "Pedido no encontrado" });
    if (!result.changed) return res.status(409).json({ error: "El estado del pedido cambió" });
    res.json(result.pedido);
  } catch {
    res.status(500).json({ error: "No se pudo actualizar el estado del pedido" });
  }
});

// Actualizar
router.put("/:id", async (req, res) => {
  try {
    const pedido = await prisma.pedidos.update({
      where: {
        id: Number(req.params.id),
      },
      data: req.body,
    });

    res.json(pedido);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Eliminar
router.delete("/:id", async (req, res) => {
  try {
    await prisma.pedidos.delete({
      where: {
        id: Number(req.params.id),
      },
    });

    res.json({ mensaje: "Pedido eliminado" });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});
module.exports = router;