import type { CSSProperties } from "react";

const RADIUS = 500;

/*
 * Un méridien de longitude λ, vu de face, est une ellipse de demi-largeur R·|sin λ|.
 * Chaque méridien est donc dessiné à pleine largeur puis aplati par scaleX(|sin λ|) :
 * le globe peut tourner en n'animant que transform (voir .lp-globe--spin dans landing.css).
 * 12 méridiens, tous les 15°, de 0° à 165°. --order les range du centre vers le bord,
 * pour qu'ils apparaissent dans cet ordre quand le globe se dessine.
 */
const MERIDIANS = Array.from({ length: 12 }, (_, index) => {
  const longitude = index * 15;
  const scale = Math.max(Math.abs(Math.sin((longitude * Math.PI) / 180)), 0.001);
  return { longitude, scale: Number(scale.toFixed(4)), phase: longitude / 180 };
})
  .sort((a, b) => a.scale - b.scale)
  .map((meridian, order) => ({ ...meridian, order }));

/**
 * Motif signature : les méridiens d'un globe, en filets clairs. Purement décoratif.
 * Le masque `id` permet au globe de se dessiner du pôle nord au pôle sud (transform seulement).
 */
export function Globe({ id, className, spin = false }: { id: string; className?: string; spin?: boolean }) {
  const mask = `lp-globe-wipe-${id}`;
  return (
    <svg
      className={`lp-globe ${className ?? ""}${spin ? " lp-globe--spin" : ""}`}
      viewBox="-502 -502 1004 1004"
      aria-hidden="true"
      focusable="false"
    >
      <defs>
        <mask id={mask} maskUnits="userSpaceOnUse" x="-502" y="-502" width="1004" height="1004">
          <rect className="lp-globe__wipe" x="-502" y="-502" width="1004" height="1004" fill="#fff" />
        </mask>
      </defs>
      <g mask={`url(#${mask})`} fill="none" stroke="currentColor" strokeWidth="1">
        <circle r={RADIUS} vectorEffect="non-scaling-stroke" />
        {MERIDIANS.map((meridian) => (
          <ellipse
            key={meridian.longitude}
            className="lp-meridian"
            rx={RADIUS}
            ry={RADIUS}
            vectorEffect="non-scaling-stroke"
            style={
              {
                transform: `scaleX(${meridian.scale})`,
                "--phase": meridian.phase,
                "--order": meridian.order,
              } as CSSProperties
            }
          />
        ))}
      </g>
    </svg>
  );
}

/** Logo : au survol, son méridien fait un demi-tour (voir .lp-logo__meridian). */
export function LogoMark({ className = "lp-logo__mark" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <g fill="none" stroke="currentColor" strokeWidth="1.6">
        <circle cx="12" cy="12" r="9.2" />
        <ellipse className="lp-logo__meridian" cx="12" cy="12" rx="4.4" ry="9.2" />
        <path d="M12 2.8v18.4" />
      </g>
    </svg>
  );
}
