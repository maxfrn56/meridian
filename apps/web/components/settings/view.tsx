"use client";

import { PageHeader } from "@/components/page-header";
import { PageFallback } from "@/components/fallback";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { ApiError, api, saveSettings } from "@/lib/api";
import type { Settings, SettingsInput } from "@/lib/types";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

const EMPTY: SettingsInput = {
  workspaceName: "",
  brandName: "",
  domain: "",
  sector: "",
  competitors: [],
  queries: [],
};

export function SettingsView() {
  const [ready, setReady] = useState(false);
  useEffect(() => setReady(true), []);
  if (!ready) return <PageFallback />;
  return <SettingsData />;
}

function toInput(settings: Settings): SettingsInput {
  return {
    workspaceName: settings.workspaceName,
    brandName: settings.brandName,
    domain: settings.domain,
    sector: settings.sector,
    competitors: settings.competitors.map(({ name, domain }) => ({ name, domain })),
    queries: settings.queries.map(({ prompt, active }) => ({ prompt, active })),
  };
}

function SettingsData() {
  const queryClient = useQueryClient();
  const settings = useQuery({ queryKey: ["settings"], queryFn: () => api<Settings>("/settings") });
  const [form, setForm] = useState<SettingsInput>(EMPTY);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    if (settings.data) setForm(toInput(settings.data));
  }, [settings.data]);

  const save = useMutation({
    mutationFn: () => saveSettings(form),
    onSuccess: async (data) => {
      setForm(toInput(data));
      setMessage("Réglages enregistrés.");
      await queryClient.invalidateQueries({ queryKey: ["settings"] });
      await queryClient.invalidateQueries({ queryKey: ["overview"] });
      await queryClient.invalidateQueries({ queryKey: ["tracking"] });
      await queryClient.invalidateQueries({ queryKey: ["me"] });
    },
    onError: (error) => setMessage(error instanceof ApiError ? error.message : "Enregistrement impossible."),
  });

  if (settings.isPending) return <PageFallback />;
  if (settings.error) {
    return (
      <div className="mx-auto max-w-6xl px-5 py-10">
        <p className="text-sm text-destructive">{settings.error.message}</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl px-5 py-8">
      <PageHeader
        eyebrow="Réglages"
        title="Marque, concurrents, requêtes"
        description="Cinq concurrents et soixante questions au maximum. Le forfait décide combien peuvent être envoyées chaque mois."
        action={
          <Button onClick={() => save.mutate()} disabled={save.isPending}>
            {save.isPending ? "Enregistrement…" : "Enregistrer"}
          </Button>
        }
      />
      {message ? <p className="mb-4 text-sm text-muted-foreground">{message}</p> : null}
      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Marque</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-3">
            <Field label="Espace" value={form.workspaceName} onChange={(workspaceName) => setForm({ ...form, workspaceName })} />
            <Field label="Nom de marque" value={form.brandName} onChange={(brandName) => setForm({ ...form, brandName })} />
            <Field label="Domaine" value={form.domain} onChange={(domain) => setForm({ ...form, domain })} placeholder="northwind.io" />
            <Field label="Secteur" value={form.sector} onChange={(sector) => setForm({ ...form, sector })} />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Concurrents ({form.competitors.length}/5)</CardTitle>
            <Button
              variant="outline"
              size="sm"
              disabled={form.competitors.length >= 5}
              onClick={() => setForm({ ...form, competitors: [...form.competitors, { name: "", domain: "" }] })}
            >
              Ajouter
            </Button>
          </CardHeader>
          <CardContent className="space-y-3">
            {form.competitors.map((competitor, index) => (
              <div key={index} className="grid grid-cols-[1fr_1fr_auto] gap-2">
                <Input
                  aria-label="Nom du concurrent"
                  value={competitor.name}
                  placeholder="Nom"
                  onChange={(event) => updateCompetitor(index, { name: event.target.value })}
                />
                <Input
                  aria-label="Domaine du concurrent"
                  value={competitor.domain}
                  placeholder="domaine.com"
                  onChange={(event) => updateCompetitor(index, { domain: event.target.value })}
                />
                <Button variant="ghost" onClick={() => removeCompetitor(index)}>
                  Retirer
                </Button>
              </div>
            ))}
            {form.competitors.length === 0 ? <p className="text-sm text-muted-foreground">Aucun concurrent.</p> : null}
          </CardContent>
        </Card>
      </div>
      <Card className="mt-4">
        <CardHeader>
          <CardTitle>Questions ({form.queries.length}/60)</CardTitle>
          <Button
            variant="outline"
            size="sm"
            disabled={form.queries.length >= 60}
            onClick={() => setForm({ ...form, queries: [...form.queries, { prompt: "", active: true }] })}
          >
            Ajouter
          </Button>
        </CardHeader>
        <CardContent className="space-y-3">
          {form.queries.map((query, index) => (
            <div key={index} className="grid gap-2 md:grid-cols-[1fr_auto_auto] md:items-start">
              <Textarea
                aria-label="Requête cible"
                value={query.prompt}
                onChange={(event) => updateQuery(index, { prompt: event.target.value })}
              />
              <label className="flex items-center gap-2 text-sm text-muted-foreground">
                <input
                  type="checkbox"
                  checked={query.active}
                  onChange={(event) => updateQuery(index, { active: event.target.checked })}
                />
                Active
              </label>
              <Button variant="ghost" onClick={() => removeQuery(index)}>
                Retirer
              </Button>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );

  function updateCompetitor(index: number, patch: Partial<SettingsInput["competitors"][number]>) {
    setForm({
      ...form,
      competitors: form.competitors.map((item, itemIndex) => (itemIndex === index ? { ...item, ...patch } : item)),
    });
  }

  function removeCompetitor(index: number) {
    setForm({ ...form, competitors: form.competitors.filter((_, itemIndex) => itemIndex !== index) });
  }

  function updateQuery(index: number, patch: Partial<SettingsInput["queries"][number]>) {
    setForm({
      ...form,
      queries: form.queries.map((item, itemIndex) => (itemIndex === index ? { ...item, ...patch } : item)),
    });
  }

  function removeQuery(index: number) {
    setForm({ ...form, queries: form.queries.filter((_, itemIndex) => itemIndex !== index) });
  }
}

function Field({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}) {
  const id = label.toLowerCase().replace(/\s+/g, "-");
  return (
    <div className="grid gap-1.5">
      <Label htmlFor={id}>{label}</Label>
      <Input id={id} value={value} placeholder={placeholder} onChange={(event) => onChange(event.target.value)} />
    </div>
  );
}
