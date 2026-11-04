import { ArrowUp, ChevronDown } from "lucide-react";
import { AppWindow } from "@/components/landing/app-window";
import { BRAND, CITATION_TREND, KPIS, OPPORTUNITIES, SHARE_OF_VOICE } from "@/components/landing/data";

const Y_MAX = 60;
const Y_TICKS = [0, 20, 40, 60];

const SERIES = [
  { key: "leader", label: "Notafix", values: CITATION_TREND.leader, end: "48 %", className: "is-leader" },
  { key: "client", label: BRAND.name, values: CITATION_TREND.client, end: "38,3 %", className: "is-client" },
  { key: "others", label: "Autres concurrents", values: CITATION_TREND.others, end: "23 %", className: "is-others" },
];

const CAPTIONS = [
  {
    title: "Score GEO",
    text: "Une note sur 100 qui combine taux de citation, rang, ton des réponses et part de voix.",
  },
  {
    title: "Part de voix",
    text: "Votre part des mentions face aux concurrents que vous suivez, moteur par moteur.",
  },
  {
    title: "Opportunités",
    text: "Les questions où un concurrent est cité à votre place, classées par potentiel.",
  },
];

const x = (index: number) => (index / (CITATION_TREND.client.length - 1)) * 100;
const y = (value: number) => 100 - (value / Y_MAX) * 100;

export function Dashboard() {
  return (
    <section id="produit" className="lp-section lp-section--surface" aria-labelledby="dashboard-title">
      <div className="lp-container">
        <div className="lp-section-head">
          <h2 id="dashboard-title" className="lp-h2">
            Toute votre visibilité dans les IA, sur un seul écran.
          </h2>
          <p className="lp-lead">
            Score GEO, taux de citation, part de voix face à vos concurrents, évolution et opportunités. Le tableau de
            bord se met à jour chaque matin.
          </p>
        </div>

        <figure className="lp-dashboard">
          <figcaption className="visually-hidden">
            Tableau de bord d&apos;{BRAND.name} sur 30 jours : score GEO 64 sur 100, taux de citation 38,3 %, part de voix
            24 % (deuxième sur cinq marques, derrière Notafix à 31 %), rang moyen 2,4. Sur 90 jours, le taux de citation
            d&apos;{BRAND.name} passe de 24 % à 38,3 %, quand Notafix reste autour de 48 % et la moyenne des autres
            concurrents autour de 23 %.
          </figcaption>
          <div aria-hidden="true">
            <AppWindow active="overview" path="vue-d-ensemble">
              <div className="lp-app__head">
                <div>
                  <p className="lp-app__title">Vue d&apos;ensemble</p>
                  <p className="lp-app__meta">Comparé à Notafix, Kalcéo, Spendia et Fraisgo</p>
                </div>
                <div className="lp-app__filters">
                  <span className="lp-chip">
                    30 derniers jours <ChevronDown />
                  </span>
                </div>
              </div>

              <div className="lp-tiles">
                <div className="lp-tile">
                  <span className="lp-tile__label">Score GEO</span>
                  <strong className="lp-tile__value">
                    {KPIS.score}
                    <small>/100</small>
                  </strong>
                  <span className="lp-meter lp-meter--client">
                    <i style={{ width: `${KPIS.score}%` }} />
                  </span>
                  <span className="lp-tile__delta">
                    <ArrowUp />
                    {KPIS.scoreDelta}
                  </span>
                </div>
                <div className="lp-tile">
                  <span className="lp-tile__label">Taux de citation</span>
                  <strong className="lp-tile__value">{KPIS.citationRate}</strong>
                  <span className="lp-tile__sub">
                    {KPIS.citedAnswers} réponses sur {KPIS.totalAnswers}
                  </span>
                  <span className="lp-tile__delta">
                    <ArrowUp />
                    {KPIS.citationDelta}
                  </span>
                </div>
                <div className="lp-tile">
                  <span className="lp-tile__label">Part de voix</span>
                  <strong className="lp-tile__value">{KPIS.shareOfVoice}</strong>
                  <span className="lp-tile__sub">{KPIS.shareRank}</span>
                  <span className="lp-tile__delta">
                    <ArrowUp />
                    +3 pts sur 30 jours
                  </span>
                </div>
                <div className="lp-tile">
                  <span className="lp-tile__label">Rang moyen</span>
                  <strong className="lp-tile__value">{KPIS.averageRank}</strong>
                  <span className="lp-tile__sub">quand vous êtes cité</span>
                  <span className="lp-tile__delta">
                    <ArrowUp />
                    {KPIS.averageRankDelta}
                  </span>
                </div>
              </div>

              <div className="lp-panels">
                <div className="lp-panel lp-panel--trend">
                  <div className="lp-panel__head">
                    <strong>Taux de citation, 90 jours</strong>
                    <ul className="lp-legend">
                      {SERIES.map((serie) => (
                        <li key={serie.key} className={serie.className}>
                          <i />
                          {serie.label}
                        </li>
                      ))}
                    </ul>
                  </div>
                  <div className="lp-line">
                    <div className="lp-line__plot">
                      {Y_TICKS.map((tick) => (
                        <span key={tick} className="lp-line__grid" style={{ top: `${y(tick)}%` }}>
                          <span>{tick} %</span>
                        </span>
                      ))}
                      <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="lp-line__svg">
                        {SERIES.map((serie) => (
                          <polyline
                            key={serie.key}
                            className={serie.className}
                            points={serie.values.map((value, index) => `${x(index)},${y(value)}`).join(" ")}
                            vectorEffect="non-scaling-stroke"
                          />
                        ))}
                      </svg>
                      {SERIES.map((serie) => {
                        const last = serie.values[serie.values.length - 1];
                        return (
                          <span key={serie.key} className={`lp-line__end ${serie.className}`} style={{ top: `${y(last)}%` }}>
                            <i />
                            <span>
                              {serie.label === "Autres concurrents" ? "Autres" : serie.label} <b>{serie.end}</b>
                            </span>
                          </span>
                        );
                      })}
                      {CITATION_TREND.months.map((month) => (
                        <span key={month.label} className="lp-line__month" style={{ left: `${x(month.index)}%` }}>
                          {month.label}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="lp-panel">
                  <div className="lp-panel__head">
                    <strong>Part de voix</strong>
                    <span className="lp-muted">5 marques</span>
                  </div>
                  <ul className="lp-sov">
                    {SHARE_OF_VOICE.map((brand) => (
                      <li key={brand.name} className={brand.client ? "is-client" : undefined}>
                        <span className="lp-sov__name">{brand.name}</span>
                        <span className="lp-sov__track">
                          <i style={{ width: `${(brand.value / SHARE_OF_VOICE[0].value) * 100}%` }} />
                        </span>
                        <span className="lp-num">{brand.value} %</span>
                      </li>
                    ))}
                  </ul>
                </div>

                <div className="lp-panel lp-panel--wide">
                  <div className="lp-panel__head">
                    <strong>Opportunités</strong>
                    <span className="lp-muted">Concurrents cités à votre place</span>
                  </div>
                  <table className="lp-otable">
                    <thead>
                      <tr>
                        <th>Question</th>
                        <th>Cités à votre place</th>
                        <th>Vous êtes absent de</th>
                        <th>Potentiel</th>
                      </tr>
                    </thead>
                    <tbody>
                      {OPPORTUNITIES.map((item) => (
                        <tr key={item.question}>
                          <td>{item.question}</td>
                          <td>{item.instead}</td>
                          <td className="lp-muted">{item.missing}</td>
                          <td>
                            <span className={`lp-prio lp-prio--${item.potential === "Élevé" ? "high" : "mid"}`}>
                              {item.potential}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </AppWindow>
          </div>
        </figure>

        <dl className="lp-captions">
          {CAPTIONS.map((caption) => (
            <div key={caption.title}>
              <dt>{caption.title}</dt>
              <dd>{caption.text}</dd>
            </div>
          ))}
        </dl>
      </div>
    </section>
  );
}
