"use client";

import type { ReactNode } from "react";
import type { Claim, Diagnosis } from "@/lib/types";
import {
  STATUS_LABEL, daysLeft, daysSinceAccident, LODGE_LIMIT_DAYS, readiness,
} from "@/lib/domain";

export function Panel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="panel">
      <div className="panelhdr">{title}</div>
      <div className="panel-body">{children}</div>
    </section>
  );
}

export function Card({ title, children }: { title?: string; children: ReactNode }) {
  return (
    <section className="panel">
      <div className="panel-body">
        {title && <div className="sec">{title}</div>}
        {children}
      </div>
    </section>
  );
}

export function Banner({ kind, children }: { kind: "ok" | "err" | "warn" | "info"; children: ReactNode }) {
  return <div className={`bnr ${kind}`}>{children}</div>;
}

export function StatusPill({ status }: { status: Claim["status"] }) {
  const s = STATUS_LABEL[status];
  return <span className={s.cls}>{s.label}</span>;
}

export function ReadinessPill({ claim }: { claim: Claim }) {
  const r = readiness(claim);
  return <span className={`pill ${r.cls}`}>{r.label}</span>;
}

/** Post-lodgement repair-window countdown (submitted claims only). */
export function WindowPill({ claim }: { claim: Claim }) {
  const d = daysLeft(claim);
  if (d === null) return null;
  if (d <= 0) return <span className="pill err">Repair window expired</span>;
  const cls = d <= 3 ? "err" : d <= 7 ? "warn" : "blue";
  return (
    <span className={`pill ${cls}`}>
      {d} {d === 1 ? "day" : "days"} left to revise
    </span>
  );
}

/** Timeliness of lodging an unsubmitted claim, relative to the accident date. */
export function LodgementNote({ claim }: { claim: Claim }) {
  const n = daysSinceAccident(claim);
  if (n === null) return <span className="mono">accident date not set</span>;
  if (n >= LODGE_LIMIT_DAYS) return <span className="pill err">Delayed lodgement &gt;12mo — extra records</span>;
  if (n >= LODGE_LIMIT_DAYS - 65) return <span className="pill warn">Approaching 12-month limit</span>;
  return (
    <span className="mono">
      {n} {n === 1 ? "day" : "days"} since accident
    </span>
  );
}

export function DxTable({ diagnoses, withStatus = true }: { diagnoses: Diagnosis[]; withStatus?: boolean }) {
  return (
    <table className="tbl">
      <thead>
        <tr>
          <th>Diagnosis</th>
          <th>Side</th>
          <th>ACC?</th>
          {withStatus && <th>Status</th>}
        </tr>
      </thead>
      <tbody>
        {diagnoses.map((d) => (
          <tr key={d.id}>
            <td>
              {d.display} <span className="mono">{d.code}</span>
              {d.primary && <span className="pill blue" style={{ marginLeft: 6 }}>primary</span>}
            </td>
            <td>{d.side}</td>
            <td>{d.acc ? <span className="pill ok">Yes</span> : <span className="pill err">Not eligible</span>}</td>
            {withStatus && (
              <td>
                <span className="pill">{d.status}</span>
              </td>
            )}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="field">
      <label>{label}</label>
      {children}
    </div>
  );
}

/** Segmented Yes/No (and general single-select) control. */
export function Segmented<T extends string>({
  options, value, onChange, disabled, render,
}: {
  options: readonly T[];
  value: T;
  onChange: (v: T) => void;
  disabled?: boolean;
  render?: (v: T) => string;
}) {
  return (
    <div className="seg">
      {options.map((o) => (
        <button
          key={o || "—"}
          type="button"
          aria-pressed={value === o}
          disabled={disabled}
          onClick={() => onChange(o)}
        >
          {render ? render(o) : o || "—"}
        </button>
      ))}
    </div>
  );
}

export function Modal({
  title, onClose, children, footer,
}: {
  title: string;
  onClose: () => void;
  children: ReactNode;
  footer: ReactNode;
}) {
  return (
    <div className="backdrop" onClick={onClose} role="presentation">
      <div
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onClick={(e) => e.stopPropagation()}
      >
        <header>{title}</header>
        <div className="body">{children}</div>
        <footer>{footer}</footer>
      </div>
    </div>
  );
}

export function DefList({ pairs }: { pairs: [string, ReactNode][] }) {
  return (
    <div className="dlgrid">
      {pairs.map(([k, v]) => (
        <div className="dl" key={k}>
          <span className="dt">{k}</span>
          <span className="dd">{v === "" || v === null || v === undefined ? "—" : v}</span>
        </div>
      ))}
    </div>
  );
}

export function WideRow({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="dl" style={{ border: 0 }}>
      <span className="dt">{label}</span>
      <span className="dd">{value || "—"}</span>
    </div>
  );
}
