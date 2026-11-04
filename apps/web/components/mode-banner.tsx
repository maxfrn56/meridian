import type { LlmMode } from "@/lib/types";

export function ModeBanner({ mode }: { mode: LlmMode }) {
  if (mode === "live") return null;
  const text =
    mode === "mixed"
      ? "Une partie des réponses vient des moteurs, l'autre est simulée faute de clé API."
      : "Réponses simulées. Ajoutez les clés OpenAI, Perplexity ou Gemini pour interroger les moteurs.";
  return (
    <p className="no-print mb-6 rounded-lg border border-accent/30 bg-accent/10 px-3 py-2 text-sm text-accent">
      {text}
    </p>
  );
}
