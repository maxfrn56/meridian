"use client";

import { PageHeader } from "@/components/page-header";
import { PageFallback } from "@/components/fallback";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api, saveSettings } from "@/lib/api";
import { categoryLabel, dateTimeLabel, effortLabel, providerLabel, weekLabel } from "@/lib/format";
import type { Audit, AuditResponse, DiscoveredCompetitor, Provider, Recommendation, Settings } from "@/lib/types";
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
        <p className="text-sm text-destructive">{audit.error.message}</p>
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
        eyebrow="Audit"
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
      {run.error ? <p className="mb-4 text-sm text-destructive">{run.error.message}</p> : null}
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
                    <span className="font-mono text-muted-foreground">{report[bar.key]}</span>
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
  const queryClient = useQueryClient();
  const settings = useQuery({ queryKey: ["settings"], queryFn: () => api<Settings>("/settings") });
  const [notice, setNotice] = useState<string | null>(null);
  const add = useMutation({
    mutationFn: async (item: DiscoveredCompetitor) => {
      if (!settings.data) throw new Error("Les réglages ne sont pas encore chargés.");
      const current = settings.data;
      if (current.competitors.some((competitor) => competitor.domain === item.domain)) return current;
      if (current.competitors.length >= 5) throw new Error("La liste est pleine : 5 concurrents maximum. Retirez-en un dans Réglages.");
      return saveSettings({
        workspaceName: current.workspaceName,
        brandName: current.brandName,
        domain: current.domain,
        sector: current.sector,
        competitors: [...current.competitors.map(({ name, domain }) => ({ name, domain })), { name: item.name, domain: item.domain }],
        queries: current.queries.map(({ prompt, active }) => ({ prompt, active })),
      });
    },
    onSuccess: async (_data, item) => {
      setNotice(`${item.name} est ajouté à vos concurrents. Le prochain suivi le comptera dans votre part de voix.`);
      await queryClient.invalidateQueries({ queryKey: ["settings"] });
      await queryClient.invalidateQueries({ queryKey: ["audit"] });
      await queryClient.invalidateQueries({ queryKey: ["overview"] });
    },
  });

  if (items.length === 0) return null;
  const known = new Set(settings.data?.competitors.map((competitor) => competitor.domain) ?? []);
  const full = (settings.data?.competitors.length ?? 0) >= 5;

  return (
    <Card className="mb-4">
      <CardHeader>
        <CardTitle>Marques citées auxquelles vous n'aviez pas pensé</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-sm leading-6 text-muted-foreground">
          Vous avez indiqué vos concurrents connus. Les réponses des moteurs en citent d'autres, sur les mêmes questions.
          Ajoutez-les pour mesurer votre place face à eux.
        </p>
        {items.map((item) => {
          const tracked = known.has(item.domain);
          return (
            <div key={item.domain} className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border px-4 py-3">
              <div>
                <p className="text-sm font-medium">{item.name}</p>
                <p className="mt-1 text-sm text-muted-foreground">
                  {item.domain} · cité dans {item.mentions} réponses · {item.providers.map((provider) => providerLabel(provider as Provider)).join(", ")}
                </p>
              </div>
              {tracked ? (
                <Badge tone="good">Déjà suivi</Badge>
              ) : (
                <Button variant="outline" disabled={add.isPending || full || !settings.data} onClick={() => add.mutate(item)}>
                  Ajouter aux concurrents
                </Button>
              )}
            </div>
          );
        })}
        {full ? <p className="text-sm text-muted-foreground">Cinq concurrents sont déjà suivis. Retirez-en un dans Réglages pour en ajouter un nouveau.</p> : null}
        {notice ? <p className="text-sm text-success">{notice}</p> : null}
        {add.error ? <p className="text-sm text-destructive">{add.error.message}</p> : null}
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
      <circle cx="70" cy="70" r={radius} fill="none" stroke="rgba(232,239,235,0.1)" strokeWidth="10" />
      <circle
        cx="70"
        cy="70"
        r={radius}
        fill="none"
        stroke="#3dbea5"
        strokeWidth="10"
        strokeLinecap="round"
        strokeDasharray={circumference}
        strokeDashoffset={offset}
        transform="rotate(-90 70 70)"
      />
      <text x="70" y="66" textAnchor="middle" fill="currentColor" fontSize="32" fontFamily="var(--font-geist-mono), monospace">
        {score}
      </text>
      <text x="70" y="86" textAnchor="middle" fill="#93a29b" fontSize="11">
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
    `## Marques citées non déclarées`,
    ...(discovered.length
      ? discovered.map((item) => `- ${item.name} (${item.domain}) — ${item.mentions} réponses`)
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
