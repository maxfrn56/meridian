"use client";

import { PageHeader } from "@/components/page-header";
import { PageFallback } from "@/components/fallback";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api";
import type { Prospect, ProspectChannel, ProspectInput, ProspectList, ProspectStatus } from "@/lib/types";
import { cn } from "@/lib/utils";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

const STATUSES: { id: ProspectStatus; label: string }[] = [
  { id: "a_contacter", label: "À contacter" },
  { id: "envoye", label: "Mail envoyé" },
  { id: "relance", label: "Relance prévue" },
  { id: "rdv", label: "Rendez-vous" },
  { id: "devis", label: "Devis envoyé" },
  { id: "gagne", label: "Signé" },
  { id: "perdu", label: "Sans suite" },
];

const CHANNELS: { id: ProspectChannel; label: string }[] = [
  { id: "email", label: "E-mail" },
  { id: "linkedin", label: "LinkedIn" },
  { id: "telephone", label: "Téléphone" },
];

const EMPTY: ProspectInput = {
  company: "",
  contactName: "",
  email: "",
  website: "",
  city: "",
  question: "",
  channel: "email",
  status: "a_contacter",
  sentOn: null,
  followUpOn: null,
  meetingOn: null,
  amountEur: 1500,
  nextStep: "",
  notes: "",
};

function statusLabel(status: ProspectStatus) {
  return STATUSES.find((item) => item.id === status)?.label ?? status;
}

function statusTone(status: ProspectStatus) {
  if (status === "gagne" || status === "rdv") return "good" as const;
  if (status === "perdu") return "bad" as const;
  if (status === "relance") return "warn" as const;
  if (status === "envoye" || status === "devis") return "brand" as const;
  return "neutral" as const;
}

function toInput(item: Prospect): ProspectInput {
  const { id: _id, createdAt: _created, updatedAt: _updated, ...input } = item;
  return input;
}

function due(item: Prospect) {
  if (!item.followUpOn || (item.status !== "envoye" && item.status !== "relance")) return false;
  return item.followUpOn <= new Date().toISOString().slice(0, 10);
}

export function ProspectsView() {
  const [ready, setReady] = useState(false);
  useEffect(() => setReady(true), []);
  if (!ready) return <PageFallback />;
  return <ProspectsData />;
}

function ProspectsData() {
  const queryClient = useQueryClient();
  const prospects = useQuery({ queryKey: ["prospects"], queryFn: () => api<ProspectList>("/prospects") });
  const [selectedId, setSelectedId] = useState<string | "new" | null>(null);
  const [form, setForm] = useState<ProspectInput>(EMPTY);
  const [message, setMessage] = useState<string | null>(null);
  const [filter, setFilter] = useState<"all" | "due" | ProspectStatus>("all");

  useEffect(() => {
    if (selectedId === "new") {
      setForm(EMPTY);
      return;
    }
    const current = prospects.data?.items.find((item) => item.id === selectedId);
    if (current) setForm(toInput(current));
  }, [prospects.data, selectedId]);

  const save = useMutation({
    mutationFn: () => {
      const body = JSON.stringify(form);
      if (selectedId && selectedId !== "new") {
        return api<Prospect>(`/prospects/${selectedId}`, { method: "PUT", body });
      }
      return api<Prospect>("/prospects", { method: "POST", body });
    },
    onSuccess: async (saved) => {
      setMessage("Fiche enregistrée.");
      setSelectedId(saved.id);
      await queryClient.invalidateQueries({ queryKey: ["prospects"] });
    },
    onError: (error) => setMessage(error.message),
  });

  const remove = useMutation({
    mutationFn: (id: string) => api<void>(`/prospects/${id}`, { method: "DELETE" }),
    onSuccess: async () => {
      setSelectedId(null);
      setMessage("Fiche retirée.");
      await queryClient.invalidateQueries({ queryKey: ["prospects"] });
    },
    onError: (error) => setMessage(error.message),
  });

  if (prospects.isPending) return <PageFallback />;
  if (prospects.error) {
    return (
      <div className="mx-auto max-w-6xl px-5 py-10">
        <p className="text-sm font-semibold text-destructive">{prospects.error.message}</p>
      </div>
    );
  }

  const items = prospects.data.items.filter((item) => {
    if (filter === "all") return true;
    if (filter === "due") return due(item);
    return item.status === filter;
  });

  return (
    <div className="mx-auto max-w-7xl px-5 py-8">
      <PageHeader
        title="Suivi des entreprises"
        description="Fiches partagées de l'équipe commerciale : contact, question posée, date d'envoi et relance."
        action={
          <Button
            onClick={() => {
              setSelectedId("new");
              setMessage(null);
            }}
          >
            Nouvelle entreprise
          </Button>
        }
      />
      <div className="mb-4 grid gap-3 sm:grid-cols-4">
        <Metric label="À contacter" value={prospects.data.summary.toContact} />
        <Metric label="En attente" value={prospects.data.summary.waiting} />
        <Metric label="Relances dues" value={prospects.data.summary.followUpsDue} />
        <Metric label="Rendez-vous" value={prospects.data.summary.meetings} />
      </div>
      <div className="mb-4 flex flex-wrap gap-2">
        <FilterButton active={filter === "all"} onClick={() => setFilter("all")}>
          Toutes
        </FilterButton>
        <FilterButton active={filter === "due"} onClick={() => setFilter("due")}>
          À relancer
        </FilterButton>
        {STATUSES.map((status) => (
          <FilterButton key={status.id} active={filter === status.id} onClick={() => setFilter(status.id)}>
            {status.label}
          </FilterButton>
        ))}
      </div>
      <Card>
        <CardContent className="overflow-x-auto px-0">
          <table className="w-full min-w-[760px] text-left text-sm">
            <thead className="text-xs font-medium text-muted-foreground">
              <tr>
                <th className="px-4 py-3 font-medium">Entreprise</th>
                <th className="px-4 py-3 font-medium">Contact</th>
                <th className="px-4 py-3 font-medium">Statut</th>
                <th className="px-4 py-3 font-medium">Envoyé</th>
                <th className="px-4 py-3 font-medium">Relance</th>
                <th className="px-4 py-3 font-medium">Prochaine action</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr
                  key={item.id}
                  onClick={() => {
                    setSelectedId(item.id);
                    setMessage(null);
                  }}
                  className={cn("cursor-pointer border-t border-border hover:bg-muted/60", selectedId === item.id && "bg-muted")}
                >
                  <td className="px-4 py-3">
                    <p className="font-medium">{item.company}</p>
                    <p className="text-xs text-muted-foreground">{item.city || item.website}</p>
                  </td>
                  <td className="px-4 py-3">
                    <p>{item.contactName || "—"}</p>
                    <p className="text-xs text-muted-foreground">{item.email}</p>
                  </td>
                  <td className="px-4 py-3">
                    <Badge tone={statusTone(item.status)}>{statusLabel(item.status)}</Badge>
                  </td>
                  <td className="px-4 py-3 tabular-nums text-xs">{item.sentOn || "—"}</td>
                  <td className="px-4 py-3">
                    <span className={cn("tabular-nums text-xs", due(item) && "font-semibold text-foreground")}>{item.followUpOn || "—"}</span>
                    {due(item) ? <p className="text-xs font-semibold text-foreground">À faire</p> : null}
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">{item.nextStep || "—"}</td>
                </tr>
              ))}
              {items.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-muted-foreground">
                    Aucune entreprise dans ce filtre.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </CardContent>
      </Card>
      {selectedId ? (
        <Card className="mt-4">
          <CardContent className="grid gap-4 pt-6 md:grid-cols-2">
            <Field label="Entreprise">
              <Input value={form.company} onChange={(event) => setForm({ ...form, company: event.target.value })} />
            </Field>
            <Field label="Contact">
              <Input value={form.contactName} onChange={(event) => setForm({ ...form, contactName: event.target.value })} />
            </Field>
            <Field label="E-mail">
              <Input value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} />
            </Field>
            <Field label="Site">
              <Input value={form.website} onChange={(event) => setForm({ ...form, website: event.target.value })} />
            </Field>
            <Field label="Ville">
              <Input value={form.city} onChange={(event) => setForm({ ...form, city: event.target.value })} />
            </Field>
            <Field label="Canal">
              <Select value={form.channel} onChange={(value) => setForm({ ...form, channel: value as ProspectChannel })} options={CHANNELS} />
            </Field>
            <Field label="Statut">
              <Select value={form.status} onChange={(value) => setForm({ ...form, status: value as ProspectStatus })} options={STATUSES} />
            </Field>
            <Field label="Montant (€)">
              <Input
                type="number"
                value={form.amountEur ?? ""}
                onChange={(event) => setForm({ ...form, amountEur: event.target.value === "" ? null : Number(event.target.value) })}
              />
            </Field>
            <Field label="Date d’envoi">
              <Input type="date" value={form.sentOn ?? ""} onChange={(event) => setForm({ ...form, sentOn: event.target.value || null })} />
            </Field>
            <Field label="Relance prévue">
              <Input type="date" value={form.followUpOn ?? ""} onChange={(event) => setForm({ ...form, followUpOn: event.target.value || null })} />
            </Field>
            <Field label="Rendez-vous">
              <Input type="date" value={form.meetingOn ?? ""} onChange={(event) => setForm({ ...form, meetingOn: event.target.value || null })} />
            </Field>
            <Field label="Prochaine action">
              <Input value={form.nextStep} onChange={(event) => setForm({ ...form, nextStep: event.target.value })} />
            </Field>
            <div className="md:col-span-2">
              <Field label="Question posée">
                <Textarea value={form.question} onChange={(event) => setForm({ ...form, question: event.target.value })} />
              </Field>
            </div>
            <div className="md:col-span-2">
              <Field label="Notes">
                <Textarea value={form.notes} onChange={(event) => setForm({ ...form, notes: event.target.value })} />
              </Field>
            </div>
            <div className="flex flex-wrap items-center gap-2 md:col-span-2">
              <Button onClick={() => save.mutate()} disabled={save.isPending || form.company.trim().length < 2}>
                {save.isPending ? "Enregistrement…" : "Enregistrer"}
              </Button>
              {selectedId !== "new" ? (
                <Button variant="outline" onClick={() => remove.mutate(selectedId)} disabled={remove.isPending}>
                  Retirer
                </Button>
              ) : null}
              {message ? <p className="text-sm text-muted-foreground">{message}</p> : null}
            </div>
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <Card>
      <CardContent className="py-4">
        <p className="text-xs font-medium text-muted-foreground">{label}</p>
        <p className="mt-1 tabular-nums text-2xl font-semibold tracking-[-0.02em]">{value}</p>
      </CardContent>
    </Card>
  );
}

function FilterButton({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn("rounded-full border border-border px-3 py-1 text-xs", active ? "bg-foreground text-background" : "text-muted-foreground")}
    >
      {children}
    </button>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <Label className="grid gap-1.5">
      <span>{label}</span>
      {children}
    </Label>
  );
}

function Select({
  value,
  onChange,
  options,
}: {
  value: string;
  onChange: (value: string) => void;
  options: { id: string; label: string }[];
}) {
  return (
    <select
      value={value}
      onChange={(event) => onChange(event.target.value)}
      className="h-10 rounded-lg border border-input bg-background px-3 text-sm font-medium shadow-xs outline-none transition-[border-color,box-shadow] duration-300 ease-out focus-visible:border-foreground focus-visible:ring-4 focus-visible:ring-foreground/10"
    >
      {options.map((option) => (
        <option key={option.id} value={option.id}>
          {option.label}
        </option>
      ))}
    </select>
  );
}
