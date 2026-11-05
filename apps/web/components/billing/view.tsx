"use client";

import { PageHeader } from "@/components/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PageFallback } from "@/components/fallback";
import { api } from "@/lib/api";
import { euros } from "@/lib/format";
import type { Subscription } from "@/lib/types";
import { cn } from "@/lib/utils";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

export function BillingView() {
  const [ready, setReady] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const queryClient = useQueryClient();
  useEffect(() => setReady(true), []);
  const billing = useQuery({
    queryKey: ["billing"],
    queryFn: () => api<Subscription>("/billing"),
    enabled: ready,
  });
  const choose = useMutation({
    mutationFn: (planId: string) => api<Subscription>("/billing", { method: "POST", body: JSON.stringify({ planId }) }),
    onSuccess: async (next) => {
      queryClient.setQueryData(["billing"], next);
      setMessage(`Le forfait ${next.plan?.name} est actif pour ce mois.`);
    },
    onError: (error: Error) => setMessage(error.message),
  });
  if (!ready || billing.isPending) return <PageFallback />;
  if (billing.error || !billing.data) {
    return (
      <div className="mx-auto max-w-6xl px-5 py-10">
        <p className="text-sm font-semibold text-destructive">{billing.error?.message ?? "Forfaits indisponibles."}</p>
      </div>
    );
  }
  const data = billing.data;
  const used = data.plan ? Math.min(100, Math.round((data.questionsUsed / data.plan.questionsPerMonth) * 100)) : 0;
  return (
    <div className="mx-auto max-w-6xl px-5 py-8">
      <PageHeader
        title="Choisissez le nombre de questions"
        description="Une question est envoyée aux trois moteurs et compte pour une dans le forfait. Le compte reste ouvert : position, sources et axes d'amélioration se consultent sans nouvelle question."
      />
      {data.plan ? (
        <Card className="mb-4">
          <CardContent className="pt-5">
            <div className="flex flex-wrap items-end justify-between gap-3">
              <div>
                <p className="text-sm text-muted-foreground">Mois en cours · {data.periodMonth}</p>
                <p className="mt-2 text-lg font-medium">{data.plan.name}</p>
                <p className="text-sm text-muted-foreground">
                  {data.questionsUsed} sur {data.plan.questionsPerMonth} questions envoyées. Il en reste {data.questionsRemaining}.
                </p>
              </div>
              <p className="tabular-nums text-2xl font-semibold tracking-[-0.02em]">{euros(data.plan.priceEur)}<span className="text-sm text-muted-foreground"> / mois</span></p>
            </div>
            <div className="mt-4 h-2 overflow-hidden rounded-full bg-muted">
              <div className="h-full bg-foreground" style={{ width: `${used}%` }} />
            </div>
          </CardContent>
        </Card>
      ) : null}
      <div className="grid gap-4 lg:grid-cols-3">
        {data.plans.map((plan) => {
          const current = data.plan?.id === plan.id;
          return (
            <Card key={plan.id} className={cn(current && "border-foreground/30 shadow-md")}>
              <CardHeader>
                <div className="flex items-center justify-between gap-2">
                  <CardTitle>{plan.name}</CardTitle>
                  {current ? <Badge tone="brand">Actif</Badge> : null}
                </div>
              </CardHeader>
              <CardContent>
                <p className="tabular-nums text-3xl font-semibold tracking-[-0.03em]">{euros(plan.priceEur)}<span className="text-sm text-muted-foreground"> / mois</span></p>
                <p className="mt-3 text-sm font-medium">{plan.questionsPerMonth} questions par mois</p>
                <p className="mt-2 text-sm leading-6 text-muted-foreground">{plan.detail}</p>
                <Button className="mt-5 w-full" variant="outline" disabled={current || choose.isPending} onClick={() => choose.mutate(plan.id)}>
                  {current ? "Forfait en cours" : "Activer ce forfait"}
                </Button>
              </CardContent>
            </Card>
          );
        })}
      </div>
      {message ? <p className="mt-4 text-sm text-muted-foreground">{message}</p> : null}
      <p className="mt-4 text-xs leading-5 text-muted-foreground">
        L'activation enregistre le forfait sur cet espace. Le paiement bancaire n'est pas encore branché : aucun prélèvement n'est fait.
      </p>
    </div>
  );
}
