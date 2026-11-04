"use client";

import { ArrowUp, ChevronDown, MessageSquareText } from "lucide-react";
import { Fragment, useEffect, useRef, useState } from "react";
import { AppWindow, RankPill, Sparkline } from "@/components/landing/app-window";
import { BRAND, ENGINES, HERO_QUESTION, KPIS, TRACKED_QUESTIONS } from "@/components/landing/data";

const ANSWER =
  "Pour une PME de cette taille, trois outils reviennent souvent. " +
  "Notafix est apprécié pour sa carte de paiement intégrée. " +
  "Orvalis se distingue par la lecture automatique des justificatifs et l'export direct vers les logiciels comptables. " +
  "Kalcéo reste l'option la moins chère, avec moins d'intégrations.";

const WORDS = ANSWER.split(" ");
const START_DELAY = 500;

type Phase = "idle" | "typing" | "done";

/**
 * Le moment fort de la page : une réponse de Perplexity s'écrit, Meridian y repère la marque,
 * puis le rang apparaît et le tableau de bord se met à jour.
 */
export function HeroProduct() {
  const rootRef = useRef<HTMLDivElement>(null);
  const answerRef = useRef<HTMLDivElement>(null);
  const [shown, setShown] = useState(0);
  const [phase, setPhase] = useState<Phase>("idle");
  const done = phase === "done";

  useEffect(() => {
    const root = rootRef.current;
    if (!root) return;
    // Cadence lue dans les tokens CSS : 0 ms quand prefers-reduced-motion est actif.
    const interval = parseFloat(getComputedStyle(root).getPropertyValue("--type-word")) || 0;
    let start: number | undefined;
    let ticker: number | undefined;

    function play() {
      if (interval === 0) {
        setShown(WORDS.length);
        setPhase("done");
        return;
      }
      setPhase("typing");
      let count = 0;
      ticker = window.setInterval(() => {
        count += 1;
        setShown(count);
        if (count >= WORDS.length) {
          window.clearInterval(ticker);
          setPhase("done");
        }
      }, interval);
    }

    const observer = new IntersectionObserver(
      (entries) => {
        if (!entries.some((entry) => entry.isIntersecting)) return;
        observer.disconnect();
        start = window.setTimeout(play, interval === 0 ? 0 : START_DELAY);
      },
      { threshold: 0.6 },
    );
    // On attend que la carte de réponse soit bien visible : c'est elle qui porte le moment fort.
    observer.observe(answerRef.current ?? root);

    return () => {
      observer.disconnect();
      window.clearTimeout(start);
      window.clearInterval(ticker);
    };
  }, []);

  return (
    <div ref={rootRef} className="lp-hero__product" data-phase={phase}>
      <p className="visually-hidden">
        Aperçu de Meridian. À la question « {HERO_QUESTION} », Perplexity cite {BRAND.name} au rang 2, après Notafix et
        devant Kalcéo. Le taux de citation de la marque passe à {KPIS.citationRate} sur les 30 derniers jours.
      </p>

      <div className="lp-hero__window" aria-hidden="true">
        <AppWindow active="questions" path="questions">
          <div className="lp-app__head">
            <div>
              <p className="lp-app__title">Questions suivies</p>
              <p className="lp-app__meta">120 questions · 3 moteurs · mise à jour ce matin</p>
            </div>
            <div className="lp-app__filters">
              <span className="lp-chip">
                30 derniers jours <ChevronDown />
              </span>
              <span className="lp-chip">
                Tous les moteurs <ChevronDown />
              </span>
            </div>
          </div>

          <div className="lp-app__stats">
            <div>
              <span>Score GEO</span>
              <strong>
                {KPIS.score}
                <small>/100</small>
              </strong>
            </div>
            <div>
              <span>Rang moyen</span>
              <strong>{KPIS.averageRank}</strong>
            </div>
            <div>
              <span>Part de voix</span>
              <strong>{KPIS.shareOfVoice}</strong>
            </div>
          </div>

          <table className="lp-qtable">
            <thead>
              <tr>
                <th>Question</th>
                {ENGINES.map((engine) => (
                  <th key={engine} className="lp-qtable__engine">
                    {engine}
                  </th>
                ))}
                <th className="lp-qtable__trend">30 jours</th>
              </tr>
            </thead>
            <tbody>
              {TRACKED_QUESTIONS.map((row, rowIndex) => (
                <tr key={row.question}>
                  <td className="lp-qtable__question">{row.question}</td>
                  {row.ranks.map((rank, engineIndex) => {
                    const live = rowIndex === 0 && engineIndex === 1;
                    return (
                      <td key={engineIndex} className="lp-qtable__engine">
                        {live && !done ? (
                          <span className="lp-rank lp-rank--pending">Analyse</span>
                        ) : (
                          <span className={live ? "lp-pop" : undefined}>
                            <RankPill rank={rank} />
                          </span>
                        )}
                      </td>
                    );
                  })}
                  <td className="lp-qtable__trend">
                    <Sparkline values={row.trend} max={3} muted={row.ranks.every((rank) => rank === null)} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </AppWindow>
      </div>

      <div ref={answerRef} className="lp-float lp-answer" aria-hidden="true">
        <div className="lp-answer__head">
          <span className="lp-answer__engine">
            <span className="lp-answer__glyph">
              <MessageSquareText />
            </span>
            <span>
              <strong>Perplexity</strong>
              <small>Aujourd&apos;hui, 09:12</small>
            </span>
          </span>
          {done ? (
            <span className="lp-status lp-status--cited lp-pop">Citée · rang 2</span>
          ) : (
            <span className="lp-status">Analyse en cours</span>
          )}
        </div>
        <p className="lp-answer__question">{HERO_QUESTION}</p>
        <p className="lp-answer__text">
          {WORDS.map((word, index) => {
            const pending = index >= shown;
            const last = phase === "typing" && index === shown - 1;
            return (
              <Fragment key={index}>
                {index > 0 ? " " : null}
                <span className={`lp-word${pending ? " is-pending" : ""}${last ? " is-last" : ""}`}>
                  {word === BRAND.name ? <mark className="lp-hit">{word}</mark> : word}
                </span>
              </Fragment>
            );
          })}
        </p>
        <div className="lp-answer__sources">
          <span className="lp-source">notafix.com</span>
          <span className="lp-source lp-source--client">
            <i />
            {BRAND.domain}
          </span>
          <span className="lp-source">comparatif-saas.fr</span>
        </div>
      </div>

      <div className="lp-float lp-kpi" aria-hidden="true">
        <span className="lp-kpi__label">Taux de citation</span>
        <strong className="lp-kpi__value">
          <span key={done ? "after" : "before"} className={done ? "lp-tick" : undefined}>
            {done ? KPIS.citationRate : KPIS.citationRateBefore}
          </span>
        </strong>
        <span className="lp-kpi__detail">
          {done ? KPIS.citedAnswers : KPIS.citedAnswers - 1} réponses sur {KPIS.totalAnswers}
        </span>
        <svg className="lp-kpi__chart" viewBox="0 0 200 48" aria-hidden="true">
          <polyline
            points="0,40 17,39 33,39 50,36 67,35 83,33 100,31 117,30 133,26 150,24 167,22 183,17 200,14"
            fill="none"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <circle cx="196" cy="14.5" r="4" />
        </svg>
        <span className="lp-kpi__delta">
          <ArrowUp aria-hidden="true" />
          {KPIS.citationDelta}
        </span>
      </div>
    </div>
  );
}
