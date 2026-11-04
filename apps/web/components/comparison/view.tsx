"use client";

import { PageHeader } from "@/components/page-header";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PageFallback } from "@/components/fallback";
import { api } from "@/lib/api";
import { percent, providerLabel, sentimentMeta, weekLabel } from "@/lib/format";
import type { Comparison, CompareEntity, Provider } from "@/lib/types";
import { cn } from "@/lib/utils";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";

export function ComparisonView() {
  const [ready, setReady] = useState(false);
  const [provider, setProvider] = useState<Provider | "all">("all");
  useEffect(() => setReady(true), []);
  const comparison = useQuery({
    queryKey: ["comparison"],
    queryFn: () => api<Comparison>("/comparison"),
    enabled: ready,
  });
  if (!ready || comparison.isPending) return <PageFallback />;
  if (comparison.error || !comparison.data) {
    return (
      <div className="mx-auto max-w-6xl px-5 py-10">
        <p className="text-sm font-semibold text-destructive">{comparison.error?.message ?? "Comparaison indisponible."}</p>
      </div>
    );
  }
  const data = comparison.data;
  const brand = data.entities.find((item) => item.kind === "brand");
  return (
    <div className="mx-auto max-w-6xl px-5 py-8">
      <PageHeader
        meta={data.week ? `Semaine du ${weekLabel(data.week)}` : undefined}
        title="Marque contre concurrents"
        description={`${data.runs} réponses de la dernière semaine. Quatre lectures : présence, rang, ton et sources. Aucun nouvel appel n’est lancé.`}
      />
      <div className="mb-4 flex flex-wrap gap-2">
        <Filter active={provider === "all"} onClick={() => setProvider("all")}>
          Tous les moteurs
        </Filter>
        {data.providers.map((item) => (
          <Filter key={item} active={provider === item} onClick={() => setProvider(item)}>
            {providerLabel(item)}
          </Filter>
        ))}
      </div>
      <div className="grid gap-3 sm:grid-cols-4">
        <Metric label="Visibilité" value={percent(reading(brand, provider).visibility)} hint="Réponses où le nom apparaît" />
        <Metric label="Position moyenne" value={positionLabel(reading(brand, provider).averagePosition)} hint="1 = cité en premier" />
        <Metric label="Ton" value={sentimentMeta(reading(brand, provider).sentiment).label} hint="Jugement dans la phrase" />
        <Metric label="Sources propres" value={percent(reading(brand, provider).ownSourceRate)} hint="Le domaine de la marque est cité" />
      </div>

      <Card className="mt-4">
        <CardHeader>
          <CardTitle>Écarts à combler</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-2">
          {data.gaps.map((gap) => (
            <div key={gap.title} className="rounded-lg border border-border p-4">
              <p className="font-medium">{gap.title}</p>
              <p className="mt-1 text-sm leading-6 text-muted-foreground">{gap.detail}</p>
            </div>
          ))}
        </CardContent>
      </Card>

      <Card id="position" className="mt-4">
        <CardHeader>
          <CardTitle>Tableau comparatif</CardTitle>
        </CardHeader>
        <CardContent className="overflow-x-auto px-0">
          <table className="w-full min-w-[760px] text-left text-sm">
            <thead className="text-xs font-medium text-muted-foreground">
              <tr>
                <th className="px-4 py-3 font-medium">Marque</th>
                <th className="px-4 py-3 font-medium">Visibilité</th>
                <th className="px-4 py-3 font-medium">Position</th>
                <th className="px-4 py-3 font-medium">Ton</th>
                <th className="px-4 py-3 font-medium">Sources propres</th>
                <th className="px-4 py-3 font-medium">Réponses sourcées</th>
              </tr>
            </thead>
            <tbody>
              {data.entities.map((entity) => {
                const row = reading(entity, provider);
                const tone = sentimentMeta(row.sentiment);
                return (
                  <tr key={entity.name} className="border-t border-border">
                    <td className="px-4 py-3">
                      <p className="font-medium">{entity.name}</p>
                      <p className="text-xs text-muted-foreground">{entity.domain}</p>
                    </td>
                    <td className="px-4 py-3 tabular-nums">{percent(row.visibility)}</td>
                    <td className="px-4 py-3 tabular-nums">{positionLabel(row.averagePosition)}</td>
                    <td className={cn("px-4 py-3", tone.className)}>
                      {tone.label}
                      {provider === "all" ? (
                        <span className="mt-0.5 block text-xs text-muted-foreground">
                          {entity.positive} positif · {entity.neutral} neutre · {entity.negative} négatif
                        </span>
                      ) : null}
                    </td>
                    <td className="px-4 py-3 tabular-nums">{percent(row.ownSourceRate)}</td>
                    <td className="px-4 py-3 tabular-nums">{percent(row.sourcedRate)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </CardContent>
      </Card>

      <Card className="mt-4">
        <CardHeader>
          <CardTitle>Question par question</CardTitle>
        </CardHeader>
        <CardContent className="overflow-x-auto px-0">
          <table className="w-full min-w-[720px] text-left text-sm">
            <thead className="text-xs font-medium text-muted-foreground">
              <tr>
                <th className="px-4 py-3 font-medium">Question</th>
                {data.entities.map((entity) => (
                  <th key={entity.name} className="px-4 py-3 font-medium">
                    {entity.name}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.prompts.map((prompt) => (
                <tr key={prompt.queryId} className="border-t border-border align-top">
                  <td className="max-w-xs px-4 py-3">
                    <p>{prompt.prompt}</p>
                    {prompt.brandMentioned ? null : (
                      <Badge className="mt-2" tone="warn">
                        Marque absente
                      </Badge>
                    )}
                  </td>
                  {prompt.cells.map((cell) => {
                    const hits = provider === "all" ? cell.hits : cell.hits.filter((hit) => hit.provider === provider);
                    const best = hits.reduce<(typeof hits)[number] | null>((chosen, hit) => {
                      if (!chosen || hit.position < chosen.position) return hit;
                      return chosen;
                    }, null);
                    return (
                      <td key={cell.name} className="px-4 py-3 tabular-nums text-xs">
                        {best ? positionLabel(best.position) : "—"}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>

      <Card id="sources" className="mt-4">
        <CardHeader>
          <CardTitle>Sources qui nourrissent les réponses</CardTitle>
        </CardHeader>
        <CardContent className="overflow-x-auto px-0">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead className="text-xs font-medium text-muted-foreground">
              <tr>
                <th className="px-4 py-3 font-medium">Domaine</th>
                <th className="px-4 py-3 font-medium">Citations</th>
                <th className="px-4 py-3 font-medium">Avec la marque</th>
                <th className="px-4 py-3 font-medium">Sans la marque</th>
                <th className="px-4 py-3 font-medium">Marques présentes</th>
              </tr>
            </thead>
            <tbody>
              {data.sources.map((source) => (
                <tr key={source.domain} className="border-t border-border">
                  <td className="px-4 py-3">
                    <p className="font-medium">{source.domain}</p>
                    {source.ownedBy ? <p className="text-xs text-muted-foreground">Domaine de {source.ownedBy}</p> : null}
                  </td>
                  <td className="px-4 py-3 tabular-nums">{source.citations}</td>
                  <td className="px-4 py-3 tabular-nums">{source.runsWithBrand}</td>
                  <td className={cn("px-4 py-3 tabular-nums", source.runsWithoutBrand > 0 && "font-semibold text-foreground")}>{source.runsWithoutBrand}</td>
                  <td className="px-4 py-3 text-muted-foreground">{source.entities.join(", ") || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>
      <p className="mt-4 text-xs leading-5 text-muted-foreground">{data.methodology}</p>
    </div>
  );
}

function reading(entity: CompareEntity | undefined, provider: Provider | "all") {
  const empty = { visibility: null as number | null, averagePosition: null as number | null, sentiment: null as number | null, ownSourceRate: null as number | null, sourcedRate: null as number | null };
  if (!entity) return empty;
  if (provider === "all") return entity;
  return entity.byProvider.find((item) => item.provider === provider) ?? empty;
}

function positionLabel(value: number | null | undefined) {
  if (value == null) return "—";
  return value.toLocaleString("fr-FR", { maximumFractionDigits: 1 });
}

function Metric({ label, value, hint }: { label: string; value: string; hint: string }) {
  return (
    <Card>
      <CardContent className="pt-5">
        <p className="text-sm text-muted-foreground">{label}</p>
        <p className="mt-2 tabular-nums text-3xl font-semibold tracking-[-0.03em]">{value}</p>
        <p className="mt-2 text-sm text-muted-foreground">{hint}</p>
      </CardContent>
    </Card>
  );
}

function Filter({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "rounded-full border border-border px-3 py-1 text-xs",
        active ? "bg-foreground text-background" : "text-muted-foreground",
      )}
    >
      {children}
    </button>
  );
}
