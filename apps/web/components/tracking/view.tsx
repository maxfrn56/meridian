"use client";

import { ModeBanner } from "@/components/mode-banner";
import { PageHeader } from "@/components/page-header";
import { PageFallback } from "@/components/fallback";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { api } from "@/lib/api";
import { PROVIDERS, dateTimeLabel, providerLabel, sentimentMeta } from "@/lib/format";
import type { Provider, Tracking, TrackingRun } from "@/lib/types";
import { cn } from "@/lib/utils";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

export function TrackingView() {
  const [ready, setReady] = useState(false);
  useEffect(() => setReady(true), []);
  if (!ready) return <PageFallback />;
  return <TrackingData />;
}

function TrackingData() {
  const queryClient = useQueryClient();
  const [provider, setProvider] = useState<Provider | "all">("all");
  const [openId, setOpenId] = useState<string | null>(null);
  const tracking = useQuery({ queryKey: ["tracking"], queryFn: () => api<Tracking>("/tracking") });
  const run = useMutation({
    mutationFn: () =>
      api("/tracking/run", {
        method: "POST",
        body: JSON.stringify(provider === "all" ? {} : { providers: [provider] }),
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["tracking"] });
      await queryClient.invalidateQueries({ queryKey: ["overview"] });
    },
  });

  if (tracking.isPending) return <PageFallback />;
  if (tracking.error) {
    return (
      <div className="mx-auto max-w-6xl px-5 py-10">
        <p className="text-sm font-semibold text-destructive">{tracking.error.message}</p>
        <Button className="mt-4" variant="outline" onClick={() => tracking.refetch()}>
          Réessayer
        </Button>
      </div>
    );
  }

  const engines = PROVIDERS.filter((item) => tracking.data.providers.includes(item.id));
  /* « Tous les moteurs » : une ligne par moteur qui a répondu, la question n'est écrite qu'une fois. */
  const rows = tracking.data.queries.flatMap((query) => {
    if (provider !== "all") return [{ query, selected: query.runs[provider], first: true, key: `${query.id}-${provider}` }];
    const answered = engines.map((item) => query.runs[item.id]).filter((item): item is TrackingRun => Boolean(item));
    if (answered.length === 0) return [{ query, selected: null, first: true, key: `${query.id}-none` }];
    return answered.map((selected, index) => ({ query, selected, first: index === 0, key: `${query.id}-${selected.provider}` }));
  });

  return (
    <div className="mx-auto max-w-6xl px-5 py-8">
      <PageHeader
        title="Marque contre concurrents"
        description="Chaque requête est envoyée telle quelle. Une réponse est citée si la marque est nommée ou si son domaine apparaît dans les sources."
        action={
          <Button onClick={() => run.mutate()} disabled={run.isPending || tracking.data.queries.length === 0}>
            {run.isPending ? "Interrogation…" : "Relancer les requêtes"}
          </Button>
        }
      />
      <ModeBanner mode={tracking.data.llmMode} />
      {run.error ? <p className="mb-4 text-sm font-semibold text-destructive">{run.error.message}</p> : null}
      <Tabs value={provider} onValueChange={(value) => setProvider(value as Provider | "all")}>
        <TabsList>
          <TabsTrigger value="all">Tous les moteurs</TabsTrigger>
          {engines.map((item) => (
            <TabsTrigger key={item.id} value={item.id}>
              {item.label}
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>
      <Card className="mt-4 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[760px] text-left text-sm">
            <thead className="border-b border-border text-xs font-medium text-muted-foreground">
              <tr>
                <th className="px-4 py-3 font-medium">Requête</th>
                <th className="px-4 py-3 font-medium">Statut</th>
                <th className="px-4 py-3 font-medium">Moteur</th>
                <th className="px-4 py-3 font-medium">Position</th>
                <th className="px-4 py-3 font-medium">Sentiment</th>
                <th className="px-4 py-3 font-medium">Sources</th>
              </tr>
            </thead>
            <tbody>
              {rows.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-muted-foreground">
                    Ajoutez des requêtes dans les réglages pour lancer le suivi.
                  </td>
                </tr>
              ) : null}
              {rows.map(({ query, selected, first, key }) => {
                const sentiment = sentimentMeta(selected?.sentiment ?? null);
                const open = openId === key;
                return (
                  <FragmentRow
                    key={key}
                    open={open}
                    onToggle={() => setOpenId(open ? null : key)}
                    prompt={query.prompt}
                    showPrompt={first}
                    active={query.active}
                    run={selected}
                    sentimentClass={sentiment.className}
                    sentimentLabel={sentiment.label}
                  />
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}

function FragmentRow({
  prompt,
  showPrompt,
  active,
  run,
  open,
  onToggle,
  sentimentClass,
  sentimentLabel,
}: {
  prompt: string;
  showPrompt: boolean;
  active: boolean;
  run: TrackingRun | null;
  open: boolean;
  onToggle: () => void;
  sentimentClass: string;
  sentimentLabel: string;
}) {
  return (
    <>
      <tr className={cn("border-b border-border", !active && "opacity-50")}>
        <td className="max-w-sm px-4 py-3">
          <button
            type="button"
            onClick={onToggle}
            aria-label={showPrompt ? undefined : `${prompt} — ${run ? providerLabel(run.provider) : ""}`}
            className={cn("text-left underline-offset-4 hover:underline", !showPrompt && "text-muted-foreground")}
          >
            {showPrompt ? prompt : "Voir la réponse"}
          </button>
        </td>
        <td className="px-4 py-3">
          {run?.status === "failed" ? (
            <div className="max-w-56">
              <Badge tone="bad" title={run.error ?? undefined}>
                Échec
              </Badge>
              {run.error ? <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">{run.error}</p> : null}
            </div>
          ) : run?.status === "no_answer" ? (
            <Badge title="Le moteur n'affiche aucune réponse IA pour cette question.">Pas de réponse IA</Badge>
          ) : run?.cited ? (
            <Badge tone="good">Cité</Badge>
          ) : (
            <Badge tone="bad">Non cité</Badge>
          )}
        </td>
        <td className="px-4 py-3 text-muted-foreground">{run ? providerLabel(run.provider) : "—"}</td>
        <td className="px-4 py-3 tabular-nums">{run?.position ?? "—"}</td>
        <td className={cn("px-4 py-3", sentimentClass)}>{sentimentLabel}</td>
        <td className="px-4 py-3 text-muted-foreground">{run ? sourceDomains(run).slice(0, 3).join(", ") || "—" : "—"}</td>
      </tr>
      {open && run ? (
        <tr className="border-b border-border bg-muted/40">
          <td colSpan={6} className="px-4 py-4">
            <p className="text-xs text-muted-foreground">
              {run.model} · {run.source === "mock" ? "simulation" : "moteur"} · {dateTimeLabel(run.createdAt)}
            </p>
            {run.error ? <p className="mt-2 text-sm font-semibold text-destructive">{run.error}</p> : null}
            <p className="mt-3 whitespace-pre-wrap text-sm leading-6">{run.responseText || "Pas de texte."}</p>
            {run.mentions.length ? (
              <ul className="mt-3 space-y-1 text-sm text-muted-foreground">
                {run.mentions.map((mention) => (
                  <li key={`${mention.entityName}-${mention.position}`}>
                    {mention.position}. {mention.entityName} · sentiment {mention.sentiment.toFixed(2)}
                    {mention.stance ? ` · ${STANCE_LABELS[mention.stance]}` : ""}
                  </li>
                ))}
              </ul>
            ) : null}
            {run.citations.length ? (
              <ul className="mt-3 space-y-1 text-sm">
                {run.citations.map((citation) => (
                  <li key={citation.url}>
                    <a href={citation.url} target="_blank" rel="noreferrer" className="text-foreground underline decoration-border underline-offset-4 transition-colors hover:decoration-foreground">
                      {citation.title || citation.domain}
                    </a>
                  </li>
                ))}
              </ul>
            ) : null}
          </td>
        </tr>
      ) : null}
    </>
  );
}

const STANCE_LABELS = {
  recommended: "recommandée",
  compared: "comparée",
  mentioned: "citée en passant",
  discouraged: "déconseillée",
} as const;

/* Un domaine cité par plusieurs pages ne compte qu'une fois dans la colonne Sources. */
function sourceDomains(run: TrackingRun) {
  return [...new Set(run.citations.map((item) => item.domain))];
}
