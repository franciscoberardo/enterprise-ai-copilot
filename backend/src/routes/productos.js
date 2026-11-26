const router = require("express").Router();
const prisma = require("../prisma");

// Obtener todos
router.get("/", async (req, res) => {
  try {
    const { nombre, categoria, stockMin } = req.query;

    const productos = await prisma.productos.findMany({
      where: {
        ...(nombre && {
          nombre: {
            contains: nombre,
            mode: "insensitive",
          },
        }),
        ...(categoria && { categoria }),
        ...(stockMin && {
          stock: {
            gte: Number(stockMin),
          },
        }),
      },
    });

    res.json(productos);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Obtener uno
router.get("/:id", async (req, res) => {
  try {
    const producto = await prisma.productos.findUnique({
      where: {
        id: Number(req.params.id),
      },
    });

    if (!producto)
      return res.status(404).json({ error: "Producto no encontrado" });

    res.json(producto);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Crear
router.post("/", async (req, res) => {
  try {
    const producto = await prisma.productos.create({
      data: req.body,
    });

    res.status(201).json(producto);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Actualizar
router.put("/:id", async (req, res) => {
  try {
    const producto = await prisma.productos.update({
      where: {
        id: Number(req.params.id),
      },
      data: req.body,
    });

    res.json(producto);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Eliminar
router.delete("/:id", async (req, res) => {
  try {
    await prisma.productos.delete({
      where: {
        id: Number(req.params.id),
      },
    });

    res.json({ mensaje: "Producto eliminado" });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

module.exports = router;