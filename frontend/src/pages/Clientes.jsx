import RecordsPage from "../components/RecordsPage";
import { getClientes } from "../services/api";

export default function Clientes() {
    return (
        <RecordsPage
            title="Clientes"
            description="Conocé a tus clientes y consultá su información con el asistente."
            load={getClientes}
        />
    );
}
