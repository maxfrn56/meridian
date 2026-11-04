import { ChevronDown } from "lucide-react";
import { Reveal } from "@/components/landing/motion";
import { MaskedTitle } from "@/components/landing/masked-title";

const QUESTIONS = [
  {
    q: "Qu'est-ce que le GEO ?",
    a: "Le Generative Engine Optimization regroupe tout ce qui aide une marque à être citée dans les réponses des IA génératives comme ChatGPT, Perplexity ou Gemini. Le SEO vise une position dans une liste de liens ; le GEO vise une place dans la réponse elle-même.",
  },
  {
    q: "En quoi est-ce différent du SEO ?",
    a: "Les IA ne renvoient pas dix liens : elles rédigent une réponse et y citent quelques marques et quelques sources. Un bon référencement aide, mais ne suffit pas. Meridian mesure ce qui compte ici : être cité, à quel rang, sur quel ton, et grâce à quelles sources.",
  },
  {
    q: "Les réponses des IA changent souvent. Comment obtenir une mesure fiable ?",
    a: "Meridian pose chaque question tous les jours à chaque moteur et suit des tendances plutôt qu'une réponse isolée. Les indicateurs sont calculés sur 7, 30 et 90 jours, pour distinguer un vrai mouvement d'une simple variation.",
  },
  {
    q: "Quels moteurs suivez-vous ?",
    a: "ChatGPT, Perplexity et Gemini, avec la recherche web activée quand le moteur la propose, c'est-à-dire dans les conditions où vos clients les utilisent.",
  },
  {
    q: "Que contient l'audit gratuit ?",
    a: "Une première mesure de votre visibilité sur des questions de votre secteur, un audit de la lisibilité de votre site par les IA (robots.txt, llms.txt, données structurées) et vos premières actions prioritaires.",
  },
  {
    q: "Combien de temps avant de voir des résultats ?",
    a: "La mesure est disponible dès le premier jour. L'effet des actions sur les réponses des IA se voit en général en quelques semaines, selon le moteur et la source concernée.",
  },
  {
    q: "Y a-t-il un engagement ?",
    a: "Non. Les forfaits sont mensuels et résiliables à tout moment. L'audit gratuit ne demande pas de carte bancaire.",
  },
];

export function Faq() {
  return (
    <section id="faq" className="lp-section lp-section--surface" aria-labelledby="faq-title">
      <div className="lp-container lp-faq">
        <Reveal className="lp-faq__head">
          <MaskedTitle id="faq-title" className="lp-h2" text="Questions fréquentes" />
          <p className="lp-lead">Ce qu&apos;il faut savoir avant de lancer votre premier audit.</p>
        </Reveal>
        <div className="lp-faq__list">
          {QUESTIONS.map((item) => (
            <details key={item.q} className="lp-faq__item">
              <summary>
                {item.q}
                <ChevronDown aria-hidden="true" />
              </summary>
              <p>{item.a}</p>
            </details>
          ))}
        </div>
      </div>
    </section>
  );
}
