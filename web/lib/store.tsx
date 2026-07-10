"use client";

/**
 * Client-side application state — the replacement for Streamlit's st.session_state.
 * Mockup-scale: claims live in memory. Production swaps this for the persistence
 * connector backed by an NZ-region datastore (see PRODUCTION-READINESS.md §G).
 */

import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import type { Claim, Role } from "./types";
import { auth, persistence } from "./connectors";
import { seedClaims, seedHistory, newClaim as makeClaim } from "./seed";

export type Tab = "admin" | "clin" | "review";

interface Store {
  claims: Claim[];
  role: Role;
  activeId: string | null;
  tab: Tab;
  /** Per-identity working set: the references the signed-in user created or opened. */
  touched: Set<string>;
  actorName: string;

  setRole: (r: Role) => void;
  setTab: (t: Tab) => void;
  openClaim: (id: string, tab?: Tab) => void;
  closeClaim: () => void;
  createClaim: () => void;
  /** Mutate a claim immutably; pass an action to persist an attributed version + audit event. */
  updateClaim: (id: string, mutate: (c: Claim) => void, action?: string) => void;
  activeClaim: Claim | null;
}

const Ctx = createContext<Store | null>(null);

export function useStore(): Store {
  const v = useContext(Ctx);
  if (!v) throw new Error("useStore must be used inside <StoreProvider>");
  return v;
}

/** Seed claims, their attributed history, and each creator's working set — exactly once. */
function bootstrap() {
  const claims = seedClaims();
  seedHistory(claims);
  const touched: Record<string, Set<string>> = {};
  for (const c of claims) (touched[c.created_by] ??= new Set()).add(c.reference);
  return { claims, touched };
}

export function StoreProvider({ children }: { children: ReactNode }) {
  const [boot] = useState(bootstrap);
  const [claims, setClaims] = useState<Claim[]>(boot.claims);
  const [touchedByUser, setTouchedByUser] = useState<Record<string, Set<string>>>(boot.touched);
  const [seq, setSeq] = useState(16457); // new claims continue after the seeded refs
  const [role, setRoleState] = useState<Role>("clinical");
  const [activeId, setActiveId] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("admin");

  const actorName = auth.currentUser(role).name;

  const touched = useMemo(
    () => touchedByUser[actorName] ?? new Set<string>(),
    [touchedByUser, actorName],
  );

  const markTouched = useCallback((reference: string, who: string) => {
    setTouchedByUser((prev) => {
      const cur = prev[who];
      if (cur?.has(reference)) return prev;
      const next = new Set(cur ?? []);
      next.add(reference);
      return { ...prev, [who]: next };
    });
  }, []);

  const activeClaim = useMemo(
    () => claims.find((c) => c.id === activeId) ?? null,
    [claims, activeId],
  );

  const openClaim = useCallback(
    (id: string, nextTab: Tab = "admin") => {
      const c = claims.find((x) => x.id === id);
      if (c) markTouched(c.reference, actorName); // opening adds it to your working set
      setActiveId(id);
      setTab(nextTab);
    },
    [claims, actorName, markTouched],
  );

  const closeClaim = useCallback(() => setActiveId(null), []);

  const createClaim = useCallback(() => {
    const c = makeClaim(seq, actorName);
    setSeq((s) => s + 1);
    setClaims((prev) => [...prev, c]);
    persistence.save(c, actorName, role, "claim created");
    markTouched(c.reference, actorName);
    setActiveId(c.id);
    setTab("admin");
  }, [seq, actorName, role, markTouched]);

  const updateClaim = useCallback(
    (id: string, mutate: (c: Claim) => void, action?: string) => {
      setClaims((prev) =>
        prev.map((c) => {
          if (c.id !== id) return c;
          const draft: Claim = structuredClone(c);
          mutate(draft);
          if (action) persistence.save(draft, actorName, role, action);
          return draft;
        }),
      );
    },
    [actorName, role],
  );

  const setRole = useCallback((r: Role) => {
    setRoleState(r);
    setActiveId(null); // identities have different working sets; land on their dashboard
  }, []);

  const value: Store = {
    claims, role, activeId, tab, touched, actorName,
    setRole, setTab, openClaim, closeClaim, createClaim, updateClaim, activeClaim,
  };

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}
