import "./landing.css";

// Satoshi est chargée une fois pour tout le site, dans app/layout.tsx (variable --font-satoshi).

// Avant le premier affichage : n'active les états de départ des animations que si le mouvement est autorisé.
// Sans JavaScript ou avec prefers-reduced-motion, la page reste dans son état final.
const MOTION_GATE =
  "try{if(!window.matchMedia('(prefers-reduced-motion: reduce)').matches&&'IntersectionObserver' in window)document.documentElement.classList.add('lp-motion')}catch(e){}";

export default function SiteLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="landing">
      <script dangerouslySetInnerHTML={{ __html: MOTION_GATE }} />
      {children}
    </div>
  );
}
