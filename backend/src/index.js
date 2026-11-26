const express = require("express");
const cors = require("cors");

const clientes = require("./routes/clientes");
const productos = require("./routes/productos");
const pedidos = require("./routes/pedidos");

const app = express();

app.use(cors());
app.use(express.json());
app.get("/health", (req, res) => res.json({ status: "ok" }));

app.use("/clientes", clientes);
app.use("/productos", productos);
app.use("/pedidos", pedidos);

app.listen(3001, () => {
  console.log("Servidor en http://localhost:3001");
});