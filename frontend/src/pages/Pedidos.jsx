import RecordsPage from "../components/RecordsPage";
import { getPedidos } from "../services/api";

export default function Pedidos() {
    return (
        <RecordsPage
            title="Pedidos"
            description="Revisá tus pedidos y pedile al asistente que te ayude a analizarlos."
            load={getPedidos}
        />
    );
}
