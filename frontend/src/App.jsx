import { Routes, Route } from "react-router-dom";

import Layout from "./components/Layout";

import Documentos from "./pages/Documentos";
import Home from "./pages/Home";
import Clientes from "./pages/Clientes";
import Productos from "./pages/Productos";
import Pedidos from "./pages/Pedidos";
import PoliticaDevolucion from "./pages/PoliticaDevolucion";

function App() {
    return (
        <Layout>
            <Routes>
                <Route path="/" element={<Home />} />
                <Route path="/clientes" element={<Clientes />} />
                <Route path="/productos" element={<Productos />} />
                <Route path="/pedidos" element={<Pedidos />} />
                <Route path="/documentos" element={<Documentos />} />
                <Route
                    path="/politica-devolucion"
                    element={<PoliticaDevolucion />}
                />
            </Routes>
        </Layout>
    );
}

export default App;
