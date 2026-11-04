"use client";

import { PageHeader } from "@/components/page-header";
import { PageFallback } from "@/components/fallback";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";
import type { AdminOverview } from "@/lib/types";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";

function euros(value: number) {
  return `${value.toLocaleString("fr-FR")} €`;
}

function openedOn(iso: string) {
  return new Intl.DateTimeFormat("fr-FR", { day: "numeric", month: "short", year: "numeric" }).format(new Date(iso));
}

export function AdminView() {
  const [ready, setReady] = useState(false);
  useEffect(() => setReady(true), []);
  const office = useQuery({
    queryKey: ["admin"],
    queryFn: () => api<AdminOverview>("/admin/overview"),
    enabled: ready,
  });
  if (!ready || office.isPending) return <PageFallback />;
  if (office.error || !office.data) {
    return (
      <div className="mx-auto max-w-6xl px-5 py-10">
        <p className="text-sm font-semibold text-destructive">{office.error?.message ?? "Pilotage indisponible."}</p>
        <Button className="mt-4" variant="outline" onClick={() => office.refetch()}>
          Réessayer
        </Button>
      </div>
    );
  }
  const data = office.data;
  return (
    <div className="mx-auto max-w-6xl px-5 py-8">
      <PageHeader
        title="Activité de Meridian"
        description="Comptes clients, forfaits en cours et montant mensuel de ces forfaits. La prospection est dans l'écran suivant."
      />
      <div className="grid gap-4 md:grid-cols-4">
        <Metric label="Comptes" value={String(data.accounts)} detail={`${data.verifiedAccounts} e-mail confirmé${data.verifiedAccounts > 1 ? "s" : ""}`} />
        <Metric label="Abonnements" value={String(data.subscriptions)} detail={`sur ${data.accounts} compte${data.accounts > 1 ? "s" : ""}`} />
        <Metric label="Montant mensuel" value={euros(data.monthlyRevenueEur)} detail="somme des forfaits actifs" />
        <Metric label="Questions" value={String(data.questionsUsed)} detail="envoyées ce mois-ci" />
      </div>
      <p className="mt-3 text-xs leading-5 text-muted-foreground">
        Le montant mensuel additionne les forfaits choisis par les clients. Il correspond aux abonnements enregistrés dans Meridian.
      </p>
      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        {data.plans.map((plan) => (
          <Card key={plan.id}>
            <CardHeader>
              <CardTitle>{plan.name}</CardTitle>
              <Badge tone={plan.subscribers > 0 ? "brand" : "neutral"}>
                {plan.subscribers} abonné{plan.subscribers > 1 ? "s" : ""}
              </Badge>
            </CardHeader>
            <CardContent>
              <p className="tabular-nums text-2xl font-semibold tracking-[-0.02em]">{euros(plan.monthlyEur)}</p>
              <p className="mt-1 text-sm text-muted-foreground">
                {plan.priceEur} € / mois · {plan.subscribers} × {plan.priceEur} €
              </p>
            </CardContent>
          </Card>
        ))}
      </div>
      <Card className="mt-4">
        <CardHeader>
          <CardTitle>Comptes clients</CardTitle>
        </CardHeader>
        <CardContent className="overflow-x-auto px-0">
          <table className="w-full min-w-[760px] text-left text-sm">
            <thead className="text-xs font-medium text-muted-foreground">
              <tr>
                <th className="px-4 py-3 font-medium">Client</th>
                <th className="px-4 py-3 font-medium">Espace</th>
                <th className="px-4 py-3 font-medium">Forfait</th>
                <th className="px-4 py-3 font-medium">Montant</th>
                <th className="px-4 py-3 font-medium">Questions</th>
                <th className="px-4 py-3 font-medium">Ouvert le</th>
              </tr>
            </thead>
            <tbody>
              {data.clients.length === 0 ? (
                <tr>
                  <td className="px-4 py-6 text-muted-foreground" colSpan={6}>
                    Aucun compte client pour le moment.
                  </td>
                </tr>
              ) : (
                data.clients.map((client) => (
                  <tr key={client.id} className="border-t border-border">
                    <td className="px-4 py-3">
                      <p className="font-medium">{client.name}</p>
                      <p className="text-xs text-muted-foreground">{client.email}</p>
                      {client.emailVerified ? null : (
                        <Badge tone="warn" className="mt-1">
                          E-mail non confirmé
                        </Badge>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <p>{client.brandName || client.workspaceName || "—"}</p>
                      <p className="text-xs text-muted-foreground">{client.domain || "Domaine non renseigné"}</p>
                    </td>
                    <td className="px-4 py-3">{client.planName ?? "Aucun"}</td>
                    <td className="px-4 py-3 tabular-nums">{client.planName ? `${euros(client.priceEur)} / mois` : "—"}</td>
                    <td className="px-4 py-3 tabular-nums">
                      {client.planName ? `${client.questionsUsed} / ${client.questionsPerMonth}` : "—"}
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">{openedOn(client.createdAt)}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </div>
  );
}

function Metric({ label, value, detail }: { label: string; value: string; detail: string }) {
  return (
    <Card>
      <CardContent className="pt-5">
        <p className="text-sm text-muted-foreground">{label}</p>
        <p className="mt-2 tabular-nums text-3xl font-semibold tracking-[-0.03em]">{value}</p>
        <p className="mt-2 text-sm text-muted-foreground">{detail}</p>
      </CardContent>
    </Card>
  );
}
