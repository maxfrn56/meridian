import type { Provider } from "@/lib/types";

export const PROVIDERS: { id: Provider; label: string }[] = [
  { id: "openai", label: "GPT-4o" },
  { id: "perplexity", label: "Perplexity" },
  { id: "gemini", label: "Gemini" },
];

export function providerLabel(provider: Provider) {
  return PROVIDERS.find((item) => item.id === provider)?.label ?? provider;
}

export function euros(value: number) {
  return `${value.toLocaleString("fr-FR", { minimumFractionDigits: 1, maximumFractionDigits: 1 })} €`;
}

export function percent(value: number | null | undefined) {
  if (value == null || Number.isNaN(value)) return "—";
  return `${Math.round(value * 100)} %`;
}

export function signedRate(value: number | null | undefined) {
  if (value == null) return "—";
  const points = Math.round(value * 100);
  if (points === 0) return "stable";
  return `${points > 0 ? "+" : "−"}${Math.abs(points)} pts`;
}

export function signedPoints(value: number | null | undefined) {
  if (value == null) return "—";
  if (value === 0) return "stable";
  return `${value > 0 ? "+" : "−"}${Math.abs(value)} pts`;
}

export function weekLabel(iso: string) {
  return new Intl.DateTimeFormat("fr-FR", { day: "numeric", month: "short" }).format(new Date(iso));
}

export function dateTimeLabel(iso: string) {
  return new Intl.DateTimeFormat("fr-FR", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(iso));
}

export function sentimentMeta(value: number | null) {
  if (value == null) return { label: "—", className: "text-muted-foreground" };
  if (value >= 0.25) return { label: "Positif", className: "text-success" };
  if (value <= -0.25) return { label: "Négatif", className: "text-destructive" };
  return { label: "Neutre", className: "text-muted-foreground" };
}

export function effortLabel(effort: "low" | "medium" | "high") {
  if (effort === "low") return "Effort faible";
  if (effort === "medium") return "Effort moyen";
  return "Effort élevé";
}

export function categoryLabel(category: "technical" | "semantic" | "authority") {
  if (category === "technical") return "Technique";
  if (category === "semantic") return "Sémantique";
  return "Autorité";
}
