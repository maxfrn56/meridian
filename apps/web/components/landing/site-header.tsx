import Link from "next/link";
import { LogoMark } from "@/components/landing/globe";

const NAV = [
  { href: "#fonctionnement", label: "Fonctionnement" },
  { href: "#produit", label: "Produit" },
  { href: "#tarifs", label: "Tarifs" },
  { href: "#faq", label: "FAQ" },
];

export function Logo() {
  return (
    <Link href="/" className="lp-logo" aria-label="Meridian, accueil">
      <LogoMark />
      <span>Meridian</span>
    </Link>
  );
}

export function SiteHeader() {
  return (
    <header className="lp-header">
      <div className="lp-container lp-header__inner">
        <Logo />
        <nav className="lp-nav" aria-label="Sections de la page">
          {NAV.map((item) => (
            <a key={item.href} href={item.href} className="lp-nav__link">
              {item.label}
            </a>
          ))}
        </nav>
        <div className="lp-header__actions">
          <Link href="/login" className="lp-nav__link">
            Connexion
          </Link>
          <a href="#audit" className="lp-btn lp-btn--accent lp-btn--sm">
            Audit gratuit
          </a>
        </div>
      </div>
    </header>
  );
}
