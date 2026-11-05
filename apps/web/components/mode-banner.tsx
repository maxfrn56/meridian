import { Info } from "lucide-react";
import type { LlmMode } from "@/lib/types";

export function ModeBanner({ mode }: { mode: LlmMode }) {
  if (mode === "live") return null;
  const text =
    mode === "mixed"
      ? "Une partie des réponses vient des moteurs, l'autre est simulée faute d'accès configuré."
      : "Réponses simulées. Ajoutez les identifiants DataForSEO pour interroger les moteurs.";
  return (
    <p className="no-print mb-6 flex items-start gap-2 rounded-xl border border-border bg-muted px-4 py-3 text-sm text-foreground">
      <Info className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
      {text}
    </p>
  );
}
