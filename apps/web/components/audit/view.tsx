"use client";

import { PageHeader } from "@/components/page-header";
import { PageFallback } from "@/components/fallback";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";
import { categoryLabel, dateTimeLabel, effortLabel, providerLabel, weekLabel } from "@/lib/format";
import type { Audit, AuditResponse, DiscoveredCompetitor, Provider, Recommendation } from "@/lib/types";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

const BARS = [
  { key: "headingScore", label: "Titres" },
  { key: "schemaScore", label: "JSON-LD" },
  { key: "factualScore", label: "Faits" },
  { key: "crawlerScore", label: "Robots" },
] as const;

export function AuditView() {
  const [ready, setReady] = useState(false);
  useEffect(() => setReady(true), []);
  if (!ready) return <PageFallback />;
  return <AuditData />;
}

function AuditData() {
  const queryClient = useQueryClient();
  const audit = useQuery({ queryKey: ["audit"], queryFn: () => api<AuditResponse>("/audit") });
  const run = useMutation({
    mutationFn: () => api<AuditResponse>("/audit/run", { method: "POST", body: JSON.stringify({}) }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["audit"] });
      await queryClient.invalidateQueries({ queryKey: ["overview"] });
    },
  });

  if (audit.isPending) return <PageFallback />;
  if (audit.error) {
    return (
      <div className="mx-auto max-w-6xl px-5 py-10">
        <p className="text-sm font-semibold text-destructive">{audit.error.message}</p>
        <Button className="mt-4" variant="outline" onClick={() => audit.refetch()}>
          Réessayer
        </Button>
      </div>
    );
  }

  const report = audit.data.audit;
  return (
    <div className="mx-auto max-w-6xl px-5 py-8">
      <PageHeader
        title="Préparation GEO du site"
        description="Ce que les moteurs peuvent lire sur votre site, et la liste exacte de ce qu'il faut changer pour être cité."
        action={
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" onClick={() => window.print()} disabled={!report}>
              Exporter en PDF
            </Button>
            <Button variant="outline" onClick={() => report && downloadChecklist(report, audit.data.discoveredCompetitors)} disabled={!report}>
              Télécharger la checklist
            </Button>
            <Button onClick={() => run.mutate()} disabled={run.isPending}>
              {run.isPending ? "Crawl en cours…" : "Relancer l'audit"}
            </Button>
          </div>
        }
      />
      {run.error ? <p className="mb-4 text-sm font-semibold text-destructive">{run.error.message}</p> : null}
      <DiscoveredCard items={audit.data.discoveredCompetitors} />
      {!report ? (
        <Card>
          <CardContent className="py-8 text-sm text-muted-foreground">
            Aucun audit pour l'instant. Renseignez un domaine, puis relancez le crawl.
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 lg:grid-cols-[280px_1fr]">
          <Card>
            <CardContent className="flex flex-col items-center pt-6">
              <ScoreRing score={report.score} />
              <p className="mt-2 text-sm text-muted-foreground">{report.url}</p>
              <p className="mt-1 text-xs text-muted-foreground">{dateTimeLabel(report.createdAt)}</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Sous-scores</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {BARS.map((bar) => (
                <div key={bar.key}>
                  <div className="mb-1 flex justify-between text-sm">
                    <span>{bar.label}</span>
                    <span className="tabular-nums text-muted-foreground">{report[bar.key]}</span>
                  </div>
                  <div className="h-2 overflow-hidden rounded-full bg-muted">
                    <div className="h-full rounded-full bg-primary" style={{ width: `${report[bar.key]}%` }} />
                  </div>
                </div>
              ))}
              {audit.data.history.length > 1 ? (
                <p className="text-xs text-muted-foreground">
                  Historique : {audit.data.history.map((point) => `${weekLabel(point.week)} ${point.score}`).join(" · ")}
                </p>
              ) : null}
            </CardContent>
          </Card>
          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle>Checklist</CardTitle>
            </CardHeader>
            <CardContent className="divide-y divide-border">
              {report.checks.map((check) => (
                <div key={check.id} className="flex flex-wrap items-start justify-between gap-3 py-3 first:pt-0 last:pb-0">
                  <div>
                    <p className="text-sm font-medium">{check.label}</p>
                    <p className="mt-1 text-sm text-muted-foreground">{check.detail}</p>
                  </div>
                  <Badge tone={check.status === "pass" ? "good" : check.status === "warn" ? "warn" : "bad"}>
                    {check.status === "pass" ? "OK" : check.status === "warn" ? "À améliorer" : "Manquant"}
                  </Badge>
                </div>
              ))}
            </CardContent>
          </Card>
          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle>Actions recommandées</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {report.recommendations.length === 0 ? (
                <p className="text-sm text-muted-foreground">Aucun point bloquant sur ce crawl.</p>
              ) : null}
              {report.recommendations.map((item) => (
                <RecommendationRow key={item.id} item={item} />
              ))}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}

function DiscoveredCard({ items }: { items: DiscoveredCompetitor[] }) {
  if (items.length === 0) return null;
  return (
    <Card className="mb-4">
      <CardHeader>
        <CardTitle>Concurrents repérés dans les réponses</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-sm leading-6 text-muted-foreground">
          Les marques que les moteurs nomment le plus sur vos questions. Les cinq premières servent de référence pour la part
          de voix et le comparatif.
        </p>
        {items.map((item) => (
          <div key={item.name} className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border px-4 py-3">
            <div>
              <p className="text-sm font-medium">{item.name}</p>
              <p className="mt-1 text-sm text-muted-foreground">
                {[
                  item.domain,
                  `citée dans ${item.mentions} réponse${item.mentions > 1 ? "s" : ""}`,
                  item.providers.map((provider) => providerLabel(provider as Provider)).join(", "),
                ]
                  .filter(Boolean)
                  .join(" · ")}
              </p>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

function RecommendationRow({ item }: { item: Recommendation }) {
  return (
    <article className="rounded-lg border border-border px-4 py-3">
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone={item.priority === "P1" ? "bad" : item.priority === "P2" ? "warn" : "brand"}>{item.priority}</Badge>
        <Badge>{categoryLabel(item.category)}</Badge>
        <span className="text-xs text-muted-foreground">{effortLabel(item.effort)}</span>
      </div>
      <h3 className="mt-2 text-sm font-medium">{item.title}</h3>
      <p className="mt-1 text-sm leading-6 text-muted-foreground">{item.detail}</p>
      {item.steps.length > 0 ? (
        <ol className="mt-3 list-decimal space-y-1 pl-5 text-sm leading-6">
          {item.steps.map((step) => (
            <li key={step}>{step}</li>
          ))}
        </ol>
      ) : null}
    </article>
  );
}

function ScoreRing({ score }: { score: number }) {
  const radius = 52;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - score / 100);
  return (
    <svg viewBox="0 0 140 140" className="size-40">
      <circle cx="70" cy="70" r={radius} fill="none" stroke="var(--muted)" strokeWidth="8" />
      {/* Le score du site du client : une donnée de la marque, donc en orange. */}
      <circle
        cx="70"
        cy="70"
        r={radius}
        fill="none"
        stroke="var(--primary)"
        strokeWidth="8"
        strokeLinecap="round"
        strokeDasharray={circumference}
        strokeDashoffset={offset}
        transform="rotate(-90 70 70)"
      />
      <text
        x="70"
        y="70"
        textAnchor="middle"
        fill="currentColor"
        fontSize="34"
        fontWeight="600"
        letterSpacing="-1"
        style={{ fontVariantNumeric: "tabular-nums" }}
      >
        {score}
      </text>
      <text x="70" y="88" textAnchor="middle" fill="var(--muted-foreground)" fontSize="12" fontWeight="500">
        / 100
      </text>
    </svg>
  );
}

function downloadChecklist(report: Audit, discovered: DiscoveredCompetitor[]) {
  const lines = [
    `# Audit GEO — ${report.url}`,
    ``,
    `Score : ${report.score}/100`,
    `Titres ${report.headingScore} · JSON-LD ${report.schemaScore} · Faits ${report.factualScore} · Robots ${report.crawlerScore}`,
    ``,
    `## Concurrents repérés dans les réponses`,
    ...(discovered.length
      ? discovered.map((item) => `- ${item.name}${item.domain ? ` (${item.domain})` : ""} — ${item.mentions} réponses`)
      : ["- Aucune"]),
    ``,
    `## Checklist`,
    ...report.checks.map((check) => `- [${check.status === "pass" ? "x" : " "}] ${check.label} — ${check.detail}`),
    ``,
    `## À faire`,
    ...report.recommendations.flatMap((item) => [
      `### ${item.priority} — ${item.title}`,
      item.detail,
      ...item.steps.map((step, index) => `${index + 1}. ${step}`),
      ``,
    ]),
  ];
  const blob = new Blob([lines.join("\n")], { type: "text/markdown;charset=utf-8" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = "audit-geo.md";
  link.click();
  URL.revokeObjectURL(link.href);
}
