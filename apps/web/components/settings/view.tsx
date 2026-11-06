"use client";

import { PageHeader } from "@/components/page-header";
import { PageFallback } from "@/components/fallback";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { ApiError, api, generateQuestions, saveSettings } from "@/lib/api";
import { PROVIDERS } from "@/lib/format";
import type { Provider, Settings, SettingsInput, Subscription } from "@/lib/types";
import { cn } from "@/lib/utils";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { parseQuestionFile } from "@/lib/questions";

const DEFAULT_ENGINES: Provider[] = ["openai", "perplexity", "gemini"];

const EMPTY: SettingsInput = {
  workspaceName: "",
  brandName: "",
  domain: "",
  sector: "",
  queries: [],
  providers: DEFAULT_ENGINES,
};

const MAX_QUERIES = 200;
const TRIAL_PER_DAY = 10;

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
    queries: settings.queries.map(({ prompt, active, tag }) => ({ prompt, active, tag: tag ?? "" })),
    providers: settings.providers?.length === 3 ? settings.providers : DEFAULT_ENGINES,
  };
}

function SettingsData() {
  const queryClient = useQueryClient();
  const settings = useQuery({ queryKey: ["settings"], queryFn: () => api<Settings>("/settings") });
  const [form, setForm] = useState<SettingsInput>(EMPTY);
  const billing = useQuery({ queryKey: ["billing"], queryFn: () => api<Subscription>("/billing") });
  const [message, setMessage] = useState<string | null>(null);
  /* Questions proposées par l'IA et pas encore enregistrées. */
  const [proposed, setProposed] = useState<Set<string>>(new Set());
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (settings.data) setForm(toInput(settings.data));
  }, [settings.data]);

  const save = useMutation({
    mutationFn: () => {
      if (form.providers.length !== 3) {
        throw new ApiError("Choisissez exactement trois modèles.", 422);
      }
      return saveSettings(form);
    },
    onSuccess: async (data) => {
      setForm(toInput(data));
      setProposed(new Set());
      setMessage("Réglages enregistrés.");
      await queryClient.invalidateQueries({ queryKey: ["settings"] });
      await queryClient.invalidateQueries({ queryKey: ["overview"] });
      await queryClient.invalidateQueries({ queryKey: ["tracking"] });
      await queryClient.invalidateQueries({ queryKey: ["comparison"] });
      await queryClient.invalidateQueries({ queryKey: ["audit"] });
      await queryClient.invalidateQueries({ queryKey: ["me"] });
    },
    onError: (error) => setMessage(error instanceof ApiError ? error.message : "Enregistrement impossible."),
  });

  const filled = form.queries.filter((query) => query.prompt.trim());
  const allowance = Math.min(billing.data?.plan?.questionsPerDay ?? (billing.data?.trialActive ? TRIAL_PER_DAY : 0), MAX_QUERIES);
  const toGenerate = Math.max(0, allowance - filled.length);

  const generate = useMutation({
    mutationFn: () =>
      generateQuestions({
        brandName: form.brandName,
        domain: form.domain,
        sector: form.sector,
        existing: filled.map((query) => query.prompt),
      }),
    onSuccess: ({ questions }) => {
      setForm({ ...form, queries: [...filled, ...questions.map((prompt) => ({ prompt, active: true, tag: "" }))] });
      setProposed(new Set([...proposed, ...questions]));
      setMessage(
        `${questions.length} questions proposées. Relisez-les, retirez celles qui ne correspondent pas à vos clients, puis enregistrez.`,
      );
    },
    onError: (error) => setMessage(error instanceof ApiError ? error.message : "Génération impossible."),
  });

  if (settings.isPending) return <PageFallback />;
  if (settings.error) {
    return (
      <div className="mx-auto max-w-6xl px-5 py-10">
        <p className="text-sm font-semibold text-destructive">{settings.error.message}</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl px-5 py-8">
      <PageHeader
        title="Marque et questions"
        description="Les questions sont posées telles quelles aux moteurs. Vos concurrents ne se déclarent pas : ce sont les marques que les moteurs citent dans leurs réponses."
        action={
          <Button onClick={() => save.mutate()} disabled={save.isPending}>
            {save.isPending ? "Enregistrement…" : "Enregistrer"}
          </Button>
        }
      />
      {message ? <p className="mb-4 text-sm text-muted-foreground">{message}</p> : null}
      <Card>
        <CardHeader>
          <CardTitle>Marque</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-2">
          <Field label="Espace" value={form.workspaceName} onChange={(workspaceName) => setForm({ ...form, workspaceName })} />
          <Field label="Nom de marque" value={form.brandName} onChange={(brandName) => setForm({ ...form, brandName })} />
          <Field label="Domaine" value={form.domain} onChange={(domain) => setForm({ ...form, domain })} placeholder="northwind.io" />
          <Field label="Secteur" value={form.sector} onChange={(sector) => setForm({ ...form, sector })} />
        </CardContent>
      </Card>
      <Card className="mt-4">
        <CardHeader>
          <CardTitle>Modèles</CardTitle>
          <p className="mt-1 text-sm text-muted-foreground">Trois modèles reçoivent chaque question. {form.providers.length} sur 3.</p>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          {PROVIDERS.map((item) => {
            const selected = form.providers.includes(item.id);
            return (
              <button
                key={item.id}
                type="button"
                aria-pressed={selected}
                onClick={() => {
                  const chosen = form.providers;
                  if (chosen.includes(item.id)) {
                    setMessage(null);
                    setForm({ ...form, providers: chosen.filter((engine) => engine !== item.id) });
                    return;
                  }
                  if (chosen.length >= 3) {
                    setMessage("Trois modèles maximum. Retirez-en un pour en changer.");
                    return;
                  }
                  setMessage(null);
                  setForm({ ...form, providers: [...chosen, item.id] });
                }}
                className={cn(
                  "rounded-full border px-3 py-2 text-sm font-semibold",
                  selected ? "border-foreground bg-foreground text-background" : "border-border bg-background",
                )}
              >
                {item.label}
              </button>
            );
          })}
        </CardContent>
      </Card>
      <Card className="mt-4">
        <CardHeader>
          <div>
            <CardTitle>
              Questions ({form.queries.length}/{MAX_QUERIES})
            </CardTitle>
            <p className="mt-1 text-sm text-muted-foreground">
              {billing.data?.plan
                ? `Chaque jour, jusqu'à ${allowance} questions partent en un seul envoi, en commençant par le haut. La génération complète la liste jusque-là, à partir du site et des questions déjà écrites.`
                : billing.data?.trialActive
                  ? `Chaque jour, l'essai envoie ${allowance} questions en un seul envoi, en commençant par le haut. La génération complète la liste jusque-là.`
                  : "L'essai est terminé. Choisissez un forfait pour continuer."}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={generate.isPending || toGenerate === 0 || !form.brandName.trim() || !form.domain.trim()}
              title={toGenerate === 0 ? "Votre liste couvre déjà votre forfait." : undefined}
              onClick={() => generate.mutate()}
            >
              {generate.isPending ? "Génération…" : `Générer ${toGenerate} questions`}
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={form.queries.length >= MAX_QUERIES}
              onClick={() => fileRef.current?.click()}
            >
              Importer
            </Button>
            <input
              ref={fileRef}
              type="file"
              accept=".csv,.txt,text/csv,text/plain"
              className="sr-only"
              aria-label="Fichier de questions"
              onChange={(event) => {
                const file = event.target.files?.[0];
                event.target.value = "";
                if (!file) return;
                void file.text().then((text) => {
                  const imported = parseQuestionFile(text);
                  let kept = 0;
                  setForm((current) => {
                    const known = new Set(current.queries.map((item) => item.prompt.trim()));
                    const next = [...current.queries];
                    for (const item of imported) {
                      if (known.has(item.prompt) || next.length >= MAX_QUERIES) continue;
                      known.add(item.prompt);
                      next.push({ prompt: item.prompt, active: true, tag: item.tag });
                      kept += 1;
                    }
                    return { ...current, queries: next };
                  });
                  setMessage(
                    kept
                      ? `${kept} question${kept > 1 ? "s" : ""} importée${kept > 1 ? "s" : ""}. Enregistrez pour les conserver.`
                      : "Aucune question nouvelle dans ce fichier.",
                  );
                });
              }}
            />
            <Button
              variant="outline"
              size="sm"
              disabled={form.queries.length >= MAX_QUERIES}
              onClick={() => setForm({ ...form, queries: [...form.queries, { prompt: "", active: true, tag: "" }] })}
            >
              Ajouter
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          <datalist id="question-tags">
            <option value="Persona" />
            <option value="Produit" />
            <option value="Zone" />
            <option value="Intention" />
          </datalist>
          {form.queries.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              Aucune question. Générez-en à partir de votre site, ou ajoutez les vôtres.
            </p>
          ) : null}
          {form.queries.map((query, index) => (
            <div key={index} className="grid gap-2 md:grid-cols-[1fr_auto_auto] md:items-start">
              <div className="grid gap-1.5">
                <Textarea
                  aria-label="Requête cible"
                  value={query.prompt}
                  onChange={(event) => updateQuery(index, { prompt: event.target.value })}
                />
                <Input
                  aria-label="Étiquette"
                  list="question-tags"
                  maxLength={40}
                  placeholder="Étiquette : persona, produit, zone, intention"
                  value={query.tag ?? ""}
                  onChange={(event) => updateQuery(index, { tag: event.target.value })}
                />
                {proposed.has(query.prompt) ? (
                  <Badge className="w-fit">Proposée par l&apos;IA, pas encore enregistrée</Badge>
                ) : null}
                {query.active && query.prompt.trim() && allowance > 0 && activeRank(index) > allowance ? (
                  <p className="text-xs text-muted-foreground">Au-delà des {allowance} questions du jour.</p>
                ) : null}
              </div>
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

  function activeRank(index: number) {
    return form.queries.slice(0, index + 1).filter((item) => item.active && item.prompt.trim()).length;
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
