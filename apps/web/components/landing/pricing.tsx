import { Check } from "lucide-react";
import { Reveal } from "@/components/landing/motion";
import { MaskedTitle } from "@/components/landing/masked-title";

const PLANS = [
  {
    name: "Essentiel",
    pitch: "Pour mesurer votre point de départ.",
    price: "79,9 €",
    period: "HT / mois",
    questions: "20 questions par jour",
    features: ["Concurrents repérés dans les réponses", "1 audit de site par mois", "2 utilisateurs", "Rapport mensuel en PDF"],
    cta: "Lancer l'audit gratuit",
    featured: false,
  },
  {
    name: "Croissance",
    pitch: "Pour gagner des places face à vos concurrents.",
    price: "189,9 €",
    period: "HT / mois",
    questions: "100 questions par jour",
    features: [
      "Concurrents repérés dans les réponses",
      "Audit de site chaque semaine",
      "5 utilisateurs",
      "Sources citées et actions priorisées",
      "Alerte quand un concurrent vous dépasse",
    ],
    cta: "Lancer l'audit gratuit",
    featured: true,
  },
  {
    name: "Référence",
    pitch: "Pour couvrir plusieurs produits et plusieurs zones.",
    price: "389,9 €",
    period: "HT / mois",
    questions: "200 questions par jour",
    features: [
      "Concurrents repérés dans les réponses",
      "Audits illimités",
      "Sources citées et actions priorisées",
      "Plusieurs produits et plusieurs zones",
    ],
    cta: "Lancer l'audit gratuit",
    featured: false,
  },
];

export function Pricing() {
  return (
    <section id="tarifs" className="lp-section" aria-labelledby="pricing-title">
      <div className="lp-container">
        <Reveal className="lp-section-head">
          <MaskedTitle id="pricing-title" className="lp-h2" text="Un forfait selon le nombre de questions envoyées." />
          <p className="lp-lead">
            Sept jours d&apos;essai, dix questions par jour, sans carte. Ensuite, chaque question est posée aux trois
            modèles choisis. Sans engagement, résiliable chaque mois.
          </p>
        </Reveal>

        <ul className="lp-plans">
          {PLANS.map((plan) => (
            <li key={plan.name} className={`lp-plan${plan.featured ? " lp-plan--featured" : ""}`}>
              <div className="lp-plan__top">
                <h3 className="lp-plan__name">{plan.name}</h3>
                {plan.featured ? <span className="lp-plan__badge">Recommandé</span> : null}
              </div>
              <p className="lp-plan__pitch">{plan.pitch}</p>
              <p className="lp-plan__price">
                <strong>{plan.price}</strong>
                {plan.period ? <span>{plan.period}</span> : null}
              </p>
              <p className="lp-plan__questions">{plan.questions}</p>
              <a href="#audit" className={`lp-btn ${plan.featured ? "lp-btn--accent" : "lp-btn--ghost"} lp-plan__cta`}>
                {plan.cta}
              </a>
              <ul className="lp-plan__features">
                {plan.features.map((feature) => (
                  <li key={feature}>
                    <Check aria-hidden="true" />
                    {feature}
                  </li>
                ))}
              </ul>
            </li>
          ))}
        </ul>
        <p className="lp-footnote">Prix hors taxes. L&apos;audit gratuit ne demande pas de carte bancaire.</p>
      </div>
    </section>
  );
}
