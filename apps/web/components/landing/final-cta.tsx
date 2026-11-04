import Link from "next/link";
import { DomainForm } from "@/components/landing/domain-form";
import { Globe } from "@/components/landing/globe";
import { Logo } from "@/components/landing/site-header";

export function FinalCta() {
  return (
    <section className="lp-section" aria-labelledby="final-title">
      <div className="lp-container">
        <div className="lp-final">
          <Globe className="lp-final__globe" />
          <h2 id="final-title" className="lp-h2">
            Où en est votre marque dans les réponses des IA ?
          </h2>
          <p className="lp-lead">
            Saisissez votre domaine. Votre première mesure est prête en quelques minutes, sans carte bancaire.
          </p>
          <div className="lp-final__form">
            <DomainForm id="final" />
          </div>
        </div>
      </div>
    </section>
  );
}

export function SiteFooter() {
  return (
    <footer className="lp-footer">
      <div className="lp-container lp-footer__inner">
        <Logo />
        <nav className="lp-footer__nav" aria-label="Pied de page">
          <a href="#fonctionnement">Fonctionnement</a>
          <a href="#tarifs">Tarifs</a>
          <a href="#faq">FAQ</a>
          <Link href="/login">Connexion</Link>
        </nav>
        <p className="lp-footer__legal">© 2026 Meridian</p>
      </div>
    </footer>
  );
}
