const RADIUS = 500;
// Méridiens tous les 15° de longitude, vus de face : des ellipses de demi-largeur R·sin(λ).
const MERIDIANS = [15, 30, 45, 60, 75].map((deg) => Math.round(RADIUS * Math.sin((deg * Math.PI) / 180)));

/** Motif signature : les méridiens d'un globe, en filets très clairs. Purement décoratif. */
export function Globe({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="-502 -502 1004 1004" aria-hidden="true" focusable="false">
      <g fill="none" stroke="currentColor" strokeWidth="1" vectorEffect="non-scaling-stroke">
        <circle r={RADIUS} vectorEffect="non-scaling-stroke" />
        {MERIDIANS.map((rx) => (
          <ellipse key={rx} rx={rx} ry={RADIUS} vectorEffect="non-scaling-stroke" />
        ))}
        <line x1="0" y1={-RADIUS} x2="0" y2={RADIUS} vectorEffect="non-scaling-stroke" />
      </g>
    </svg>
  );
}

export function LogoMark() {
  return (
    <svg className="lp-logo__mark" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <g fill="none" stroke="currentColor" strokeWidth="1.6">
        <circle cx="12" cy="12" r="9.2" />
        <ellipse cx="12" cy="12" rx="4.4" ry="9.2" />
        <path d="M12 2.8v18.4" />
      </g>
    </svg>
  );
}
