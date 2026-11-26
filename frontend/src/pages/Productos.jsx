import RecordsPage from "../components/RecordsPage";
import { getProductos } from "../services/api";

export default function Productos() {
    return (
        <RecordsPage
            title="Productos"
            description="Explorá el catálogo, los precios y el stock disponible."
            load={getProductos}
        />
    );
}
