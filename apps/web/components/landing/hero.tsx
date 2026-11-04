import { Check } from "lucide-react";
import { DomainForm } from "@/components/landing/domain-form";
import { Globe } from "@/components/landing/globe";
import { HeroProduct } from "@/components/landing/hero-product";
import { ENGINES } from "@/components/landing/data";

const REASSURANCE = ["Gratuit", "Sans carte bancaire", "Premiers résultats en quelques minutes"];

export function Hero() {
  return (
    <section className="lp-hero" aria-labelledby="hero-title">
      <div className="lp-container">
        <div className="lp-hero__intro" id="audit">
          <h1 id="hero-title" className="lp-hero__title">
            Voyez ce que les IA disent de vous. <span>Puis changez la réponse.</span>
          </h1>
          <p className="lp-hero__lead">
            Chaque jour, Meridian pose à ChatGPT, Perplexity et Gemini les questions de vos clients. Vous savez si votre
            marque est citée, à quel rang, sur quel ton et face à qui, et quoi faire pour passer devant.
          </p>
          <div className="lp-hero__form">
            <DomainForm id="hero" />
            <ul className="lp-checks">
              {REASSURANCE.map((item) => (
                <li key={item}>
                  <Check aria-hidden="true" />
                  {item}
                </li>
              ))}
            </ul>
          </div>
        </div>

        <div className="lp-hero__stage">
          <Globe id="hero" className="lp-hero__globe" spin />
          <HeroProduct />
        </div>

        <p className="lp-engines">
          <span>Analyse quotidienne sur</span>
          {ENGINES.map((engine) => (
            <span key={engine} className="lp-engines__pill">
              {engine}
            </span>
          ))}
        </p>
      </div>
    </section>
  );
}
