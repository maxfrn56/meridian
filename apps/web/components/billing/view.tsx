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
import { useEffect, useRef, useState } from "react";

export function BillingView() {
  const [ready, setReady] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const confirmedOnce = useRef(false);
  const queryClient = useQueryClient();
  useEffect(() => setReady(true), []);
  const billing = useQuery({
    queryKey: ["billing"],
    queryFn: () => api<Subscription>("/billing"),
    enabled: ready,
  });
  const choose = useMutation({
    mutationFn: (planId: string) => api<{ url: string }>("/billing/checkout", { method: "POST", body: JSON.stringify({ planId }) }),
    onSuccess: (next) => {
      window.location.assign(next.url);
    },
    onError: (error: Error) => setMessage(error.message),
  });
  useEffect(() => {
    if (!ready || !billing.data || confirmedOnce.current) return;
    const params = new URLSearchParams(window.location.search);
    if (params.get("checkout") === "cancel") {
      confirmedOnce.current = true;
      setMessage("Paiement annulé. Le forfait n'a pas changé.");
      return;
    }
    const returned = params.get("checkout") === "success" || Boolean(params.get("session_id"));
    if (!returned && billing.data.plan) return;
    confirmedOnce.current = true;
    const sessionId = params.get("session_id");
    const query = sessionId ? `?sessionId=${encodeURIComponent(sessionId)}` : "";
    api<Subscription>(`/billing/confirm${query}`, { method: "POST" })
      .then((next) => {
        queryClient.setQueryData(["billing"], next);
        setMessage(next.plan ? `Le forfait ${next.plan.name} est actif.` : "Paiement reçu.");
      })
      .catch((error: Error) => {
        if (returned) setMessage(error.message);
      });
  }, [billing.data, queryClient, ready]);
  if (!ready || billing.isPending) return <PageFallback />;
  if (billing.error || !billing.data) {
    return (
      <div className="mx-auto max-w-6xl px-5 py-10">
        <p className="text-sm font-semibold text-destructive">{billing.error?.message ?? "Forfaits indisponibles."}</p>
      </div>
    );
  }
  const data = billing.data;
  const allowance = data.plan?.questionsPerDay ?? (data.trialActive ? 10 : 0);
  const used = allowance ? Math.min(100, Math.round((data.questionsUsed / allowance) * 100)) : 0;
  const trialDate = data.trialEndsAt
    ? new Date(data.trialEndsAt).toLocaleDateString("fr-FR", { day: "numeric", month: "long" })
    : "";
  return (
    <div className="mx-auto max-w-6xl px-5 py-8">
      <PageHeader
        title="Choisissez le nombre de questions"
        description="Sept jours d'essai, dix questions par jour, sans carte. Ensuite, une question est envoyée aux trois modèles choisis et compte pour une dans la journée. Le compteur repart à zéro chaque jour."
      />
      {message ? (
        <p className="mb-4 rounded-xl border border-border bg-muted px-4 py-3 text-sm font-semibold" role="status">
          {message}
        </p>
      ) : null}
      {data.plan || data.trialActive ? (
        <Card className="mb-4">
          <CardContent className="pt-5">
            <div className="flex flex-wrap items-end justify-between gap-3">
              <div>
                <p className="text-sm text-muted-foreground">Aujourd'hui · {data.periodDay}</p>
                <p className="mt-2 text-lg font-medium">{data.plan ? data.plan.name : "Essai gratuit"}</p>
                <p className="text-sm text-muted-foreground">
                  {data.questionsUsed} sur {allowance} questions envoyées aujourd'hui. Il en reste {data.questionsRemaining}.
                  {data.trialActive && trialDate ? ` Essai jusqu'au ${trialDate}.` : ""}
                </p>
              </div>
              {data.plan ? (
                <p className="tabular-nums text-2xl font-semibold tracking-[-0.02em]">{euros(data.plan.priceEur)}<span className="text-sm text-muted-foreground"> / mois</span></p>
              ) : null}
            </div>
            <div className="mt-4 h-2 overflow-hidden rounded-full bg-muted">
              <div className="h-full bg-foreground" style={{ width: `${used}%` }} />
            </div>
          </CardContent>
        </Card>
      ) : (
        <p className="mb-4 rounded-xl border border-border bg-muted px-4 py-3 text-sm font-semibold">
          L'essai de 7 jours est terminé. Choisissez un forfait pour continuer à envoyer des questions.
        </p>
      )}
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
                <p className="mt-3 text-sm font-medium">{plan.questionsPerDay} questions par jour</p>
                <p className="mt-2 text-sm leading-6 text-muted-foreground">{plan.detail}</p>
                <Button className="mt-5 w-full" variant="outline" disabled={current || choose.isPending} onClick={() => choose.mutate(plan.id)}>
                  {current ? "Forfait en cours" : choose.isPending && choose.variables === plan.id ? "Ouverture de Stripe…" : "Payer ce forfait"}
                </Button>
              </CardContent>
            </Card>
          );
        })}
      </div>
      <p className="mt-4 text-xs leading-5 text-muted-foreground">
        Le paiement s'ouvre sur Stripe. Le forfait s'active une fois le paiement confirmé.
      </p>
    </div>
  );
}
