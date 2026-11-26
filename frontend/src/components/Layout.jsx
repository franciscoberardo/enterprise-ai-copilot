import Sidebar from "./Sidebar";

export default function Layout({ children }) {
    return (
        <div className="min-h-dvh lg:flex">
            <Sidebar />
            <div className="min-w-0 flex-1">
                <header className="flex h-14 items-center justify-between border-b border-stone-200 bg-white px-5 sm:px-8 lg:px-6">
                    <span className="text-sm text-slate-500">
                        <span className="font-semibold text-slate-800">
                            Enterprise AI Copilot
                        </span>
                    </span>
                    <span
                        className="flex size-8 items-center justify-center rounded-full bg-emerald-50 text-xs font-bold text-emerald-800"
                        aria-label="Enterprise AI"
                    >
                        EA
                    </span>
                </header>
                <main className="mx-auto max-w-[1600px] p-4 sm:p-5 lg:p-6">
                    {children}
                </main>
            </div>
        </div>
    );
}
