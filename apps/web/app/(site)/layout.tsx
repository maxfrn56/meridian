import localFont from "next/font/local";
import "./landing.css";

// Satoshi (Indian Type Foundry, licence Fontshare), auto-hébergée : aucun appel externe au chargement.
const satoshi = localFont({
  src: "./fonts/Satoshi-Variable.woff2",
  weight: "300 900",
  variable: "--font-satoshi",
  display: "swap",
});

// Avant le premier affichage : n'active les états de départ des animations que si le mouvement est autorisé.
// Sans JavaScript ou avec prefers-reduced-motion, la page reste dans son état final.
const MOTION_GATE =
  "try{if(!window.matchMedia('(prefers-reduced-motion: reduce)').matches&&'IntersectionObserver' in window)document.documentElement.classList.add('lp-motion')}catch(e){}";

export default function SiteLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className={`landing ${satoshi.variable}`}>
      <script dangerouslySetInnerHTML={{ __html: MOTION_GATE }} />
      {children}
    </div>
  );
}
