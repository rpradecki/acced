"use client";

import { useEffect, useState } from "react";
import { StoreProvider, useStore } from "@/lib/store";
import { auth } from "@/lib/connectors";
import Sidebar from "@/components/Sidebar";
import Dashboard from "@/components/Dashboard";
import Workspace from "@/components/Workspace";
import { AuditDashboard, InspectView } from "@/components/Audit";

/** Router: audit role gets the audit views; everyone else gets dashboard/workspace. */
function Router() {
  const { role, activeClaim } = useStore();

  if (auth.isAudit(role)) {
    return activeClaim ? <InspectView claim={activeClaim} /> : <AuditDashboard />;
  }
  return activeClaim ? <Workspace claim={activeClaim} /> : <Dashboard />;
}

export default function Page() {
  // The seed allocates random encounter ids and reads today's date, so rendering it on the
  // server would not match the client. Mount first, then render.
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  if (!mounted) return null;

  return (
    <StoreProvider>
      <div className="app">
        <Sidebar />
        <main className="main">
          <div className="container">
            <Router />
          </div>
        </main>
      </div>
    </StoreProvider>
  );
}
