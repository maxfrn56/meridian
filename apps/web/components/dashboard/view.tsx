"use client";

import { DomainChart, SovChart, TrendChart, TrendLegend } from "@/components/charts";
import { ModeBanner } from "@/components/mode-banner";
import { PageHeader } from "@/components/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PageFallback } from "@/components/fallback";
import { api } from "@/lib/api";
import { percent, signedRate } from "@/lib/format";
import type { Overview, Subscription } from "@/lib/types";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useEffect, useState } from "react";

export function DashboardView() {
  const [ready, setReady] = useState(false);
  useEffect(() => setReady(true), []);
  if (!ready) return <PageFallback />;
  return <DashboardData />;
}

function DashboardData() {
  const queryClient = useQueryClient();
  const overview = useQuery({ queryKey: ["overview"], queryFn: () => api<Overview>("/overview") });
  const billing = useQuery({ queryKey: ["billing"], queryFn: () => api<Subscription>("/billing") });
  const run = useMutation({
    mutationFn: () => api("/tracking/run", { method: "POST", body: JSON.stringify({}) }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["overview"] });
      await queryClient.invalidateQueries({ queryKey: ["tracking"] });
    },
  });

  if (overview.isPending) return <PageFallback />;
  if (overview.error) {
    return (
      <div className="mx-auto max-w-6xl px-5 py-10">
        <p className="text-sm font-semibold text-destructive">{overview.error.message}</p>
        <Button className="mt-4" variant="outline" onClick={() => overview.refetch()}>
          Réessayer
        </Button>
      </div>
    );
  }

  const data = overview.data;
  const empty = data.kpis.queriesTracked === 0;
  return (
    <div className="mx-auto max-w-6xl px-5 py-8">
      <PageHeader
        meta={data.sector || undefined}
        title={data.brandName || data.workspaceName}
        description={data.domain ? `Domaine suivi : ${data.domain}` : "Configurez la marque pour commencer le suivi."}
        action={
          <Button
            onClick={() => run.mutate()}
            disabled={
              run.isPending ||
              data.kpis.queriesTracked === 0 ||
              !(billing.data?.plan || billing.data?.trialActive) ||
              billing.data.questionsRemaining === 0
            }
          >
            {run.isPending ? "Suivi en cours…" : "Lancer le suivi"}
          </Button>
        }
      />
      <ModeBanner mode={data.llmMode} />
      <AccountAccess billing={billing.data} />
      {run.error ? <p className="mb-4 text-sm font-semibold text-destructive">{run.error.message}</p> : null}
      {empty ? (
        <Card>
          <CardContent className="py-8">
            <h2 className="text-lg font-medium">L'espace est prêt, il n'y a pas encore de mesure.</h2>
            <p className="mt-2 max-w-xl text-sm text-muted-foreground">
              Ajoutez le domaine et les questions, ou générez-les à partir de votre site. Les concurrents seront repérés dans les réponses des moteurs.
            </p>
            <Button asChild className="mt-5">
              <Link href="/settings">Configurer l'espace</Link>
            </Button>
          </CardContent>
        </Card>
      ) : (
        <>
          <div className="grid gap-4 md:grid-cols-3">
            <Kpi label="Taux de citation" value={percent(data.kpis.citationRate)} delta={signedRate(data.kpis.citationRateDelta)} />
            <Kpi label="Part de voix" value={percent(data.kpis.shareOfVoice)} delta={signedRate(data.kpis.shareOfVoiceDelta)} />
            <Kpi label="Requêtes actives" value={String(data.kpis.queriesTracked)} delta={`${data.kpis.runsCompleted} réponses`} />
          </div>
          <div className="mt-4 grid gap-4 lg:grid-cols-[1.5fr_0.9fr]">
            <Card>
              <CardHeader>
                <CardTitle>Citation et part de voix</CardTitle>
                <TrendLegend />
              </CardHeader>
              <CardContent>
                <TrendChart trend={data.trend} />
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Part de voix, dernière semaine</CardTitle>
              </CardHeader>
              <CardContent>
                <SovChart slices={data.shareOfVoice} />
              </CardContent>
            </Card>
          </div>
          <Card className="mt-4">
            <CardHeader>
              <CardTitle>Domaines externes les plus cités</CardTitle>
              <Badge tone="warn">Là où la marque manque souvent</Badge>
            </CardHeader>
            <CardContent>
              <DomainChart domains={data.topDomains} />
            </CardContent>
          </Card>
          <p className="mt-4 text-xs leading-5 text-muted-foreground">{data.methodology}</p>
        </>
      )}
    </div>
  );
}

function AccountAccess({ billing }: { billing?: Subscription }) {
  const plan = billing?.plan;
  return (
    <div className="mb-4 grid gap-3 lg:grid-cols-[1.1fr_1.4fr]">
      <Card>
        <CardContent className="pt-5">
          <p className="text-sm text-muted-foreground">Forfait du mois</p>
          <p className="mt-2 text-lg font-medium">{plan ? plan.name : billing?.trialActive ? "Essai gratuit" : "Aucun forfait"}</p>
          <p className="mt-1 text-sm text-muted-foreground">
            {plan
              ? `${billing?.questionsUsed ?? 0} question${(billing?.questionsUsed ?? 0) > 1 ? "s" : ""} envoyée${(billing?.questionsUsed ?? 0) > 1 ? "s" : ""} aujourd'hui sur ${plan.questionsPerDay}. Il en reste ${billing?.questionsRemaining ?? 0}.`
              : billing?.trialActive
                ? `${billing.questionsUsed} question${billing.questionsUsed > 1 ? "s" : ""} envoyée${billing.questionsUsed > 1 ? "s" : ""} aujourd'hui sur 10. Il en reste ${billing.questionsRemaining}.`
                : "L'essai de 7 jours est terminé. Choisissez un forfait pour continuer."}
          </p>
          <Button asChild className="mt-4" variant="outline">
            <Link href="/billing">{plan ? "Changer de forfait" : billing?.trialActive ? "Voir les forfaits" : "Choisir un forfait"}</Link>
          </Button>
        </CardContent>
      </Card>
      <div className="grid gap-3 sm:grid-cols-2">
        <AccessLink href="/comparison" title="Position" text="Rang, visibilité et ton face aux concurrents." />
        <AccessLink href="/comparison#sources" title="Sources" text="Les domaines qui nourrissent les réponses." />
      </div>
    </div>
  );
}

function AccessLink({ href, title, text }: { href: string; title: string; text: string }) {
  return (
    <Link href={href} className="rounded-xl border border-border bg-card p-4 shadow-xs transition-shadow duration-300 ease-out hover:shadow-md">
      <p className="font-medium">{title}</p>
      <p className="mt-1 text-sm leading-5 text-muted-foreground">{text}</p>
    </Link>
  );
}

function Kpi({ label, value, delta }: { label: string; value: string; delta: string }) {
  return (
    <Card>
      <CardContent className="pt-5">
        <p className="text-sm text-muted-foreground">{label}</p>
        <p className="mt-2 tabular-nums text-3xl font-semibold tracking-[-0.03em]">{value}</p>
        <p className="mt-2 text-sm text-muted-foreground">{delta}</p>
      </CardContent>
    </Card>
  );
}
