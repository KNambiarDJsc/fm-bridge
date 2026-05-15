"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState, useEffect } from "react";
import { useCapitalStore } from "@/store/trading";
import { useCapitalShield, useSessionCtx } from "@/lib/api";

const makeClient = () =>
    new QueryClient({
        defaultOptions: {
            queries: { retry: 1, refetchOnWindowFocus: false, staleTime: 10_000 },
        },
    });

function BridgeSync() {
    const { data: shield } = useCapitalShield();
    const { data: session } = useSessionCtx();
    const { setShield, setSession } = useCapitalStore();
    useEffect(() => { if (shield) setShield(shield); }, [shield, setShield]);
    useEffect(() => { if (session) setSession(session); }, [session, setSession]);
    return null;
}

export function Providers({ children }: { children: React.ReactNode }) {
    const [client] = useState(makeClient);
    return (
        <QueryClientProvider client={client}>
            <BridgeSync />
            {children}
        </QueryClientProvider>
    );
}
