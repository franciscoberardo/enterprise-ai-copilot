const router = require("express").Router();
const prisma = require("../prisma");

// Obtener todos
router.get("/", async (req, res) => {
  try {
    const { nombre, pais, email } = req.query;

    const clientes = await prisma.clientes.findMany({
      where: {
        ...(nombre && {
          nombre: {
            contains: nombre,
            mode: "insensitive",
          },
        }),
        ...(pais && { pais }),
        ...(email && {
          email: {
            contains: email,
            mode: "insensitive",
          },
        }),
      },
    });

    res.json(clientes);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Obtener uno
router.get("/:id", async (req, res) => {
  try {
    const cliente = await prisma.clientes.findUnique({
      where: {
        id: Number(req.params.id),
      },
    });

    if (!cliente)
      return res.status(404).json({ error: "Cliente no encontrado" });

    res.json(cliente);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Crear
router.post("/", async (req, res) => {
  try {
    const cliente = await prisma.clientes.create({
      data: req.body,
    });

    res.status(201).json(cliente);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Actualizar
router.put("/:id", async (req, res) => {
  try {
    const cliente = await prisma.clientes.update({
      where: {
        id: Number(req.params.id),
      },
      data: req.body,
    });

    res.json(cliente);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Eliminar
router.delete("/:id", async (req, res) => {
  try {
    await prisma.clientes.delete({
      where: {
        id: Number(req.params.id),
      },
    });

    res.json({ mensaje: "Cliente eliminado" });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

module.exports = router;