import { NavLink } from "react-router-dom";
import Icon from "./Icon";

const links = [
    ["/", "AI Copilot", "spark"],
    ["/clientes", "Clientes", "users"],
    ["/productos", "Productos", "box"],
    ["/pedidos", "Pedidos", "orders"],
    ["/documentos", "Documentos", "file"],
    ["/politica-devolucion", "Política de devolución", "file"],
];

export default function Sidebar() {
    return (
        <aside className="flex shrink-0 flex-col bg-slate-950 p-5 text-slate-300 lg:sticky lg:top-0 lg:h-dvh lg:w-56 lg:overflow-y-auto lg:p-5">
            <NavLink
                to="/"
                className="flex items-center gap-3 px-2 py-3 text-white"
            >
                <span className="rounded-xl bg-emerald-400 p-2 text-slate-950">
                    <Icon name="spark" />
                </span>
                <span className="text-lg font-semibold tracking-tight">
                    enterprise<span className="text-emerald-400">.ai</span>
                </span>
            </NavLink>

            <p className="mt-7 mb-3 hidden px-3 text-[10px] font-semibold tracking-[0.2em] text-slate-500 uppercase lg:block">
                Espacio de trabajo
            </p>
            <nav
                aria-label="Menú principal"
                className="mt-4 flex shrink-0 gap-1 overflow-x-auto lg:mt-0 lg:flex-col lg:overflow-visible"
            >
                {links.map(([to, label, icon]) => (
                    <NavLink
                        key={to}
                        to={to}
                        end={to === "/"}
                        className={({ isActive }) =>
                            `flex shrink-0 items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition-colors ${isActive ? "bg-white/10 text-emerald-300" : "hover:bg-white/5 hover:text-white"}`
                        }
                    >
                        <Icon name={icon} />
                        {label}
                    </NavLink>
                ))}
            </nav>

            <div id="conversation-navigation" className="hidden lg:block" />
        </aside>
    );
}
