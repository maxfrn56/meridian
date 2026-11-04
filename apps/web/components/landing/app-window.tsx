import { LayoutGrid, Link2, ListChecks, MessageSquareText, ScanSearch, Users } from "lucide-react";
import type { ReactNode } from "react";
import { LogoMark } from "@/components/landing/globe";
import { BRAND } from "@/components/landing/data";

const NAV = [
  { key: "overview", label: "Vue d'ensemble", icon: LayoutGrid },
  { key: "questions", label: "Questions suivies", icon: MessageSquareText, badge: "120" },
  { key: "competitors", label: "Concurrents", icon: Users },
  { key: "sources", label: "Sources", icon: Link2 },
  { key: "audit", label: "Audit", icon: ScanSearch },
  { key: "actions", label: "Actions", icon: ListChecks, badge: "4" },
] as const;

type NavKey = (typeof NAV)[number]["key"];

/** Fenêtre de l'application Meridian : barre, barre latérale, contenu. Illustration, sans élément interactif. */
export function AppWindow({ active, path, children }: { active: NavKey; path: string; children: ReactNode }) {
  return (
    <div className="lp-window">
      <div className="lp-window__bar">
        <span className="lp-window__dots">
          <i />
          <i />
          <i />
        </span>
        <span className="lp-window__url">app.meridian.fr/{path}</span>
      </div>
      <div className="lp-window__body">
        <div className="lp-side">
          <div className="lp-side__brand">
            <LogoMark />
            Meridian
          </div>
          <div className="lp-side__workspace">
            <span className="lp-side__avatar">O</span>
            <span>
              <strong>{BRAND.name}</strong>
              <small>{BRAND.domain}</small>
            </span>
          </div>
          <ul className="lp-side__nav">
            {NAV.map(({ key, label, icon: Icon, ...item }) => (
              <li key={key} className={key === active ? "is-active" : undefined}>
                <Icon aria-hidden="true" />
                {label}
                {"badge" in item ? <span className="lp-side__badge">{item.badge}</span> : null}
              </li>
            ))}
          </ul>
          <div className="lp-side__plan">
            <span>Forfait Croissance</span>
            <span className="lp-side__usage">120 / 200 questions</span>
            <span className="lp-meter">
              <i style={{ width: "60%" }} />
            </span>
          </div>
        </div>
        <div className="lp-app">{children}</div>
      </div>
    </div>
  );
}

/** Pastille de rang de la marque cliente ; un tiret quand elle n'est pas citée. */
export function RankPill({ rank }: { rank: number | null }) {
  if (rank === null) return <span className="lp-rank lp-rank--none">—</span>;
  return <span className="lp-rank">{rank}</span>;
}

export function Sparkline({ values, max, muted }: { values: number[]; max: number; muted?: boolean }) {
  const width = 64;
  const height = 20;
  const step = width / (values.length - 1);
  const points = values.map((value, index) => `${(index * step).toFixed(1)},${(height - 2 - (value / max) * (height - 4)).toFixed(1)}`);
  return (
    <svg className={`lp-spark${muted ? " lp-spark--muted" : ""}`} viewBox={`0 0 ${width} ${height}`} aria-hidden="true">
      <polyline points={points.join(" ")} fill="none" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
