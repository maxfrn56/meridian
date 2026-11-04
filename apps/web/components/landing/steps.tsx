import { Check, CircleAlert, MessageSquareText, Plus, Search } from "lucide-react";
import type { CSSProperties, ReactNode } from "react";
import { ActionsList } from "@/components/landing/actions-list";
import { AUDIT_CHECKS, BRAND, SOURCES, TRACKED_QUESTIONS } from "@/components/landing/data";
import { CountUp, Reveal } from "@/components/landing/motion";
import { MaskedTitle } from "@/components/landing/masked-title";

const NEW_QUESTION = "Quelle carte de paiement entreprise pour une PME ?";

type Step = {
  title: string;
  text: string;
  details: string[];
  visual: ReactNode;
  summary: string;
};

const STEPS: Step[] = [
  {
    title: "Suivez les questions que se posent vos clients.",
    text: "Ajoutez vos propres questions ou partez de celles que Meridian déduit de votre site. Chacune est posée tous les jours à ChatGPT, Perplexity et Gemini.",
    details: ["Suggestions tirées de votre site et de votre secteur", "Questions par marque, par produit ou par usage"],
    visual: <QuestionsVisual />,
    summary: "Liste des questions suivies par Orvalis. Une question suggérée à partir de son site vient d'y être ajoutée : 121 questions suivies.",
  },
  {
    title: "Lisez chaque réponse, déjà analysée.",
    text: "Pour chaque réponse, Meridian relève si vous êtes cité, à quel rang, sur quel ton, et quels concurrents apparaissent à vos côtés.",
    details: ["Citation, rang et ton, réponse par réponse", "Historique complet, moteur par moteur"],
    visual: <AnswerVisual />,
    summary: "Réponse de ChatGPT où Orvalis est citée au rang 3, sur un ton positif, à côté de Notafix et Kalcéo.",
  },
  {
    title: "Voyez sur quelles sources s'appuient les IA.",
    text: "Les IA citent des comparatifs, des forums, des sites de marques. Meridian les classe par poids et montre lesquelles vous mentionnent, et lesquelles vous ignorent.",
    details: ["Domaines classés par part des réponses", "Sources où vos concurrents sont présents et pas vous"],
    visual: <SourcesVisual />,
    summary: "Classement des sources citées par les IA. forum-compta.fr apparaît dans 13 % des réponses sans mentionner Orvalis.",
  },
  {
    title: "Corrigez dans le bon ordre.",
    text: "L'audit vérifie que votre site est lisible par les IA. Meridian classe ensuite les actions selon leur effet attendu sur vos citations.",
    details: ["Audit de robots.txt, llms.txt et données structurées", "Actions classées par priorité, avec leur impact estimé"],
    visual: <AuditVisual />,
    summary: "Audit de lisibilité à 72 sur 100 et quatre actions classées par priorité.",
  },
];

export function Steps() {
  return (
    <section id="fonctionnement" className="lp-section" aria-labelledby="steps-title">
      <div className="lp-container">
        <Reveal className="lp-section-head">
          <MaskedTitle id="steps-title" className="lp-h2" text="De la question de vos clients à l'action à mener." />
          <p className="lp-lead">
            Meridian suit le même chemin que vos clients : il interroge les IA, lit leurs réponses, remonte à leurs
            sources et vous dit quoi corriger en premier.
          </p>
        </Reveal>

        <ol className="lp-steps">
          {STEPS.map((step, index) => (
            <li key={step.title} className="lp-step">
              <Reveal className="lp-step__text">
                <span className="lp-step__num" aria-hidden="true">
                  <svg className="lp-step__ring" viewBox="0 0 32 32">
                    <circle cx="16" cy="16" r="15.5" pathLength={1} />
                  </svg>
                  <span className="lp-step__digit">{index + 1}</span>
                </span>
                <h3 className="lp-h3">{step.title}</h3>
                <p className="lp-step__body">{step.text}</p>
                <ul className="lp-step__details">
                  {step.details.map((detail) => (
                    <li key={detail}>
                      <Check aria-hidden="true" />
                      {detail}
                    </li>
                  ))}
                </ul>
              </Reveal>
              <Reveal as="figure" className="lp-stage">
                <div aria-hidden="true" className="lp-stage__inner">
                  {step.visual}
                </div>
                <figcaption className="visually-hidden">{step.summary}</figcaption>
              </Reveal>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}

function QuestionsVisual() {
  return (
    <div className="lp-frag lp-frag--questions">
      <div className="lp-card">
        <div className="lp-card__head">
          <strong>Questions suivies</strong>
          <span className="lp-muted lp-swap">
            <span className="lp-swap__old">120</span>
            <span className="lp-swap__new">121</span>
          </span>
        </div>
        <div className="lp-fake-input">
          <Search />
          Ajouter une question…
        </div>
        <div className="lp-qlist-viewport">
          <ul className="lp-qlist">
            <li className="lp-qlist__new">
              <span>{NEW_QUESTION}</span>
              <span className="lp-tag">3 moteurs</span>
            </li>
            {TRACKED_QUESTIONS.slice(0, 4).map((row) => (
              <li key={row.question}>
                <span>{row.question}</span>
                <span className="lp-tag">3 moteurs</span>
              </li>
            ))}
          </ul>
        </div>
        <p className="lp-card__sub">Suggérées à partir de {BRAND.domain}</p>
        <div className="lp-suggestions">
          {["Notes de frais dans le BTP", "Indemnités kilométriques"].map((label) => (
            <span key={label} className="lp-tag lp-tag--add">
              <Plus />
              {label}
            </span>
          ))}
          <span className="lp-tag lp-tag--add lp-tag--picked">
            <span className="lp-tag__icons">
              <Plus className="lp-tag__plus" />
              <Check className="lp-tag__check" />
            </span>
            Carte de paiement entreprise
          </span>
        </div>
      </div>
      <div className="lp-card lp-card--note">
        <strong>360 réponses analysées</strong>
        <span className="lp-muted">ce matin, à 06:00</span>
      </div>
    </div>
  );
}

function AnswerVisual() {
  const rows = [
    { term: "Citée", value: <>Oui</> },
    {
      term: "Rang",
      value: (
        <>
          <span className="lp-rank">3</span> sur 3
        </>
      ),
    },
    { term: "Ton", value: <>Positif</> },
    { term: "Concurrents", value: <>Notafix, Kalcéo</> },
  ];
  return (
    <div className="lp-frag lp-frag--answer">
      <div className="lp-card">
        <div className="lp-card__head">
          <span className="lp-answer__engine">
            <span className="lp-answer__glyph">
              <MessageSquareText />
            </span>
            <span>
              <strong>ChatGPT</strong>
              <small>Aujourd&apos;hui, 09:04</small>
            </span>
          </span>
        </div>
        <p className="lp-answer__question">Quel outil de notes de frais pour une PME de 80 salariés ?</p>
        <p className="lp-answer__text">
          Plusieurs solutions conviennent à une PME. Notafix est souvent recommandé pour sa carte de paiement. Kalcéo
          propose l&apos;offre la plus économique. <mark className="lp-hit lp-hit--on">Orvalis</mark> est apprécié pour la
          lecture automatique des justificatifs et son export comptable.
        </p>
      </div>
      <dl className="lp-card lp-card--float lp-annot">
        {rows.map((row, index) => (
          <div key={row.term} style={{ "--i": index } as CSSProperties}>
            <dt>{row.term}</dt>
            <dd>{row.value}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

function SourcesVisual() {
  const max = Math.max(...SOURCES.map((source) => source.share));
  // Les barres poussent dans l'ordre du tableau, celle du client en dernier.
  const others = SOURCES.filter((source) => !source.client);
  const order = SOURCES.map((source) => (source.client ? SOURCES.length - 1 : others.indexOf(source)));
  return (
    <div className="lp-frag lp-frag--sources">
      <div className="lp-card">
        <div className="lp-card__head">
          <strong>Sources citées par les IA</strong>
          <span className="lp-muted">30 jours</span>
        </div>
        <table className="lp-stable">
          <thead>
            <tr>
              <th>Domaine</th>
              <th>Part des réponses</th>
              <th>Vous cite</th>
            </tr>
          </thead>
          <tbody>
            {SOURCES.map((source, index) => (
              <tr
                key={source.domain}
                className={source.client ? "is-client" : undefined}
                style={{ "--i": order[index] } as CSSProperties}
              >
                <td>{source.domain}</td>
                <td>
                  <span className="lp-hbar">
                    <span className="lp-hbar__track">
                      <i
                        className={source.client ? "is-client" : undefined}
                        style={{ width: `${(source.share / max) * 100}%` }}
                      />
                    </span>
                    <span className="lp-num">{source.share} %</span>
                  </span>
                </td>
                <td>
                  {source.client ? (
                    <span className="lp-muted">Votre site</span>
                  ) : source.mentionsYou ? (
                    <Check className="lp-icon-ok" />
                  ) : (
                    <span className="lp-muted">—</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="lp-card lp-card--float lp-callout">
        <span className="lp-tag">Opportunité</span>
        <p>
          <strong>forum-compta.fr</strong> apparaît dans 13 % des réponses et ne vous mentionne jamais.
        </p>
      </div>
    </div>
  );
}

function AuditVisual() {
  return (
    <div className="lp-frag lp-frag--audit">
      <div className="lp-card">
        <div className="lp-card__head">
          <strong>Lisibilité par les IA</strong>
          <span className="lp-score">
            <CountUp value={72} />
            <small>/100</small>
          </span>
        </div>
        <ul className="lp-checklist">
          {AUDIT_CHECKS.map((check, index) => (
            <li key={check.label} style={{ "--i": index } as CSSProperties}>
              {check.ok ? <Check className="lp-icon-ok" /> : <CircleAlert className="lp-icon-warn" />}
              <span>{check.label}</span>
              <span className="lp-muted lp-checklist__status">{check.ok ? "OK" : check.status}</span>
            </li>
          ))}
        </ul>
      </div>
      <div className="lp-card lp-card--float lp-actions">
        <strong className="lp-actions__title">Actions prioritaires</strong>
        <ActionsList />
      </div>
    </div>
  );
}
