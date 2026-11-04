import localFont from "next/font/local";
import "./landing.css";

// Satoshi (Indian Type Foundry, licence Fontshare), auto-hébergée : aucun appel externe au chargement.
const satoshi = localFont({
  src: "./fonts/Satoshi-Variable.woff2",
  weight: "300 900",
  variable: "--font-satoshi",
  display: "swap",
});

export default function SiteLayout({ children }: { children: React.ReactNode }) {
  return <div className={`landing ${satoshi.variable}`}>{children}</div>;
}
