export type Provider = "openai" | "perplexity" | "gemini" | "claude" | "aistudio";
export type LlmMode = "mock" | "live" | "mixed";

export type User = {
  id: string;
  name: string;
  email: string;
  role: "client" | "admin";
  workspaceName: string;
  brandName: string;
  domain: string;
};

export type AuthResponse = {
  token: string;
  user: User;
};

export type Overview = {
  workspaceName: string;
  brandName: string;
  domain: string;
  sector: string;
  llmMode: LlmMode;
  methodology: string;
  kpis: {
    geoScore: number | null;
    geoScoreDelta: number | null;
    citationRate: number | null;
    citationRateDelta: number | null;
    shareOfVoice: number | null;
    shareOfVoiceDelta: number | null;
    queriesTracked: number;
    runsCompleted: number;
  };
  trend: {
    week: string;
    citationRate: number;
    shareOfVoice: number;
    geoScore: number | null;
  }[];
  shareOfVoice: {
    name: string;
    kind: "brand" | "competitor";
    share: number;
    mentions: number;
  }[];
  topDomains: {
    domain: string;
    citations: number;
    runsWithoutBrand: number;
  }[];
};

export type Citation = {
  url: string;
  domain: string;
  title: string | null;
  position: number;
};

export type Mention = {
  entityName: string;
  entityType: "brand" | "competitor";
  position: number;
  sentiment: number;
  excerpt: string;
  /** Renseigné seulement quand Claude a analysé la réponse. */
  stance: "recommended" | "compared" | "mentioned" | "discouraged" | null;
};

export type TrackingRun = {
  id: string;
  queryId: string;
  queryPrompt: string;
  provider: Provider;
  model: string;
  status: "completed" | "failed";
  source: "live" | "mock";
  cited: boolean;
  position: number | null;
  sentiment: number | null;
  error: string | null;
  responseText: string;
  citations: Citation[];
  analysis: "llm" | "keywords";
  mentions: Mention[];
  createdAt: string;
};

export type Tracking = {
  queries: {
    id: string;
    prompt: string;
    active: boolean;
    runs: Record<Provider, TrackingRun | null>;
  }[];
  providers: Provider[];
  llmMode: LlmMode;
};

export type Check = {
  id: string;
  label: string;
  status: "pass" | "warn" | "fail";
  score: number;
  detail: string;
};

export type Recommendation = {
  id: string;
  priority: "P1" | "P2" | "P3";
  category: "technical" | "semantic" | "authority";
  title: string;
  detail: string;
  effort: "low" | "medium" | "high";
  steps: string[];
};

export type Audit = {
  id: string;
  url: string;
  score: number;
  headingScore: number;
  schemaScore: number;
  factualScore: number;
  crawlerScore: number;
  pagesCrawled: string[];
  checks: Check[];
  recommendations: Recommendation[];
  createdAt: string;
};

/** Marque que les moteurs nomment sur les questions du client. Le domaine peut être vide. */
export type DiscoveredCompetitor = {
  name: string;
  domain: string;
  mentions: number;
  providers: string[];
};

export type AuditResponse = {
  audit: Audit | null;
  history: { week: string; score: number }[];
  discoveredCompetitors: DiscoveredCompetitor[];
};

export type Settings = {
  workspaceName: string;
  brandName: string;
  domain: string;
  sector: string;
  queries: { id: string; prompt: string; active: boolean }[];
  providers: Provider[];
};

export type ProspectStatus = "a_contacter" | "envoye" | "relance" | "rdv" | "devis" | "gagne" | "perdu";
export type ProspectChannel = "email" | "linkedin" | "telephone";

export type Prospect = {
  id: string;
  company: string;
  contactName: string;
  email: string;
  website: string;
  city: string;
  question: string;
  channel: ProspectChannel;
  status: ProspectStatus;
  sentOn: string | null;
  followUpOn: string | null;
  meetingOn: string | null;
  amountEur: number | null;
  nextStep: string;
  notes: string;
  createdAt: string;
  updatedAt: string;
};

export type ProspectInput = Omit<Prospect, "id" | "createdAt" | "updatedAt">;

export type ProspectList = {
  items: Prospect[];
  summary: {
    total: number;
    toContact: number;
    waiting: number;
    followUpsDue: number;
    meetings: number;
  };
};

export type CompareProviderStat = {
  provider: Provider;
  runs: number;
  mentions: number;
  visibility: number;
  averagePosition: number | null;
  sentiment: number | null;
  ownSourceRate: number;
  sourcedRate: number;
};

export type CompareEntity = {
  name: string;
  domain: string;
  kind: "brand" | "competitor";
  mentions: number;
  visibility: number;
  averagePosition: number | null;
  sentiment: number | null;
  positive: number;
  neutral: number;
  negative: number;
  ownSourceRate: number;
  sourcedRate: number;
  byProvider: CompareProviderStat[];
};

export type Comparison = {
  brandName: string;
  domain: string;
  week: string | null;
  runs: number;
  providers: Provider[];
  entities: CompareEntity[];
  prompts: {
    queryId: string;
    prompt: string;
    runs: number;
    brandMentioned: boolean;
    cells: {
      name: string;
      hits: { provider: Provider; position: number; sentiment: number }[];
    }[];
  }[];
  sources: {
    domain: string;
    citations: number;
    runs: number;
    runsWithBrand: number;
    runsWithoutBrand: number;
    ownedBy: string | null;
    entities: string[];
  }[];
  gaps: { title: string; detail: string }[];
  methodology: string;
};

export type Plan = {
  id: string;
  name: string;
  priceEur: number;
  questionsPerDay: number;
  detail: string;
};

export type AdminOverview = {
  accounts: number;
  verifiedAccounts: number;
  subscriptions: number;
  monthlyRevenueEur: number;
  questionsUsed: number;
  plans: {
    id: string;
    name: string;
    priceEur: number;
    subscribers: number;
    monthlyEur: number;
  }[];
  clients: {
    id: string;
    name: string;
    email: string;
    emailVerified: boolean;
    createdAt: string;
    workspaceName: string;
    brandName: string;
    domain: string;
    planId: string | null;
    planName: string | null;
    priceEur: number;
    questionsUsed: number;
    questionsPerDay: number;
  }[];
};

export type Subscription = {
  plan: Plan | null;
  questionsUsed: number;
  questionsRemaining: number;
  periodDay: string;
  plans: Plan[];
  trialActive: boolean;
  trialEndsAt: string | null;
};

export type SettingsInput = {
  workspaceName: string;
  brandName: string;
  domain: string;
  sector: string;
  queries: { prompt: string; active: boolean }[];
  providers: Provider[];
};
