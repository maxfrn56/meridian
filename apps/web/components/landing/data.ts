/**
 * Jeu de données d'exemple, partagé par toute la landing.
 * Orvalis (logiciel de notes de frais) est le client ; les autres marques sont ses concurrents.
 * Tout est fictif mais cohérent : 120 questions × 3 moteurs = 360 réponses par jour.
 */

export const BRAND = { name: "Orvalis", domain: "orvalis.fr" };

export const ENGINES = ["ChatGPT", "Perplexity", "Gemini"] as const;

/** Rang de la marque par moteur (ChatGPT, Perplexity, Gemini) ; null = non citée. */
export type Ranks = [number | null, number | null, number | null];

export const HERO_QUESTION = "Quel outil de notes de frais pour une PME de 80 salariés ?";

export const TRACKED_QUESTIONS: { question: string; ranks: Ranks; trend: number[] }[] = [
  { question: HERO_QUESTION, ranks: [3, 2, null], trend: [1, 1, 2, 1, 2, 2, 2, 3] },
  { question: "Logiciel de notes de frais connecté à la comptabilité", ranks: [1, 1, 2], trend: [2, 2, 3, 2, 3, 3, 3, 3] },
  { question: "Meilleure application de notes de frais pour freelances", ranks: [null, null, null], trend: [0, 0, 0, 0, 0, 0, 0, 0] },
  { question: "Alternative à Notafix pour une PME", ranks: [2, null, 3], trend: [0, 1, 1, 1, 1, 2, 1, 2] },
  { question: "Comment automatiser la saisie des tickets de caisse ?", ranks: [null, 3, null], trend: [0, 0, 0, 1, 0, 1, 1, 1] },
  { question: "Orvalis avis", ranks: [1, 1, 1], trend: [3, 3, 3, 3, 3, 3, 3, 3] },
];

export const KPIS = {
  score: 64,
  scoreDelta: "+5 sur 30 jours",
  citationRate: "38,3 %",
  citationRateBefore: "38,1 %",
  citedAnswers: 138,
  totalAnswers: 360,
  citationDelta: "+6 pts sur 30 jours",
  shareOfVoice: "24 %",
  shareRank: "2e sur 5 marques",
  averageRank: "2,4",
  averageRankDelta: "0,3 place gagnée",
};

export const SHARE_OF_VOICE = [
  { name: "Notafix", value: 31, client: false },
  { name: BRAND.name, value: 24, client: true },
  { name: "Kalcéo", value: 19, client: false },
  { name: "Spendia", value: 14, client: false },
  { name: "Fraisgo", value: 12, client: false },
];

/** Taux de citation hebdomadaire sur 90 jours (13 semaines, du 6 août au 4 novembre 2026), en %. */
export const CITATION_TREND = {
  client: [24, 25, 25, 27, 28, 29, 30, 31, 33, 34, 35, 37, 38.3],
  leader: [47, 47, 48, 47, 48, 48, 47, 48, 48, 49, 48, 48, 48],
  others: [22, 22, 23, 22, 22, 23, 23, 22, 23, 23, 23, 23, 23],
  months: [
    { label: "août", index: 0 },
    { label: "sept.", index: 4 },
    { label: "oct.", index: 8 },
    { label: "nov.", index: 12 },
  ],
};

export const OPPORTUNITIES = [
  {
    question: "Meilleure application de notes de frais pour freelances",
    instead: "Notafix, Kalcéo",
    missing: "3 moteurs",
    potential: "Élevé",
  },
  {
    question: "Comment automatiser la saisie des tickets de caisse ?",
    instead: "Spendia, Notafix",
    missing: "ChatGPT, Gemini",
    potential: "Élevé",
  },
  {
    question: "Alternative à Notafix pour une PME",
    instead: "Kalcéo",
    missing: "Perplexity",
    potential: "Moyen",
  },
];

export const SOURCES = [
  { domain: "comparatif-saas.fr", share: 24, mentionsYou: true, client: false },
  { domain: "notafix.com", share: 18, mentionsYou: false, client: false },
  { domain: "forum-compta.fr", share: 13, mentionsYou: false, client: false },
  { domain: BRAND.domain, share: 11, mentionsYou: true, client: true },
  { domain: "guide-pme.fr", share: 8, mentionsYou: false, client: false },
];

export const AUDIT_CHECKS = [
  { label: "robots.txt autorise GPTBot, PerplexityBot et Google-Extended", ok: true },
  { label: "Fichier llms.txt", ok: false, status: "Absent" },
  { label: "Données structurées Organization et Product", ok: false, status: "Partielles" },
  { label: "Pages tarifs lisibles sans JavaScript", ok: true },
];

export const ACTIONS = [
  { priority: "Haute", title: "Publier une page comparative Orvalis / Notafix", impact: "+4 pts" },
  { priority: "Haute", title: "Ajouter un fichier llms.txt", impact: "+2 pts" },
  { priority: "Moyenne", title: "Obtenir une mention sur forum-compta.fr", impact: "+2 pts" },
  { priority: "Basse", title: "Compléter le JSON-LD Product sur 12 pages", impact: "+1 pt" },
];
