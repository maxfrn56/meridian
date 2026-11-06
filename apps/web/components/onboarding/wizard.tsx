"use client";

import { RunProgressBar, runTracking } from "@/components/run-progress";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { ApiError, api, generateQuestions, saveSettings } from "@/lib/api";
import { forgetDomain, rememberedDomain } from "@/lib/domain";
import { providerLabel, PROVIDERS } from "@/lib/format";
import type { Provider, Settings, SettingsInput } from "@/lib/types";
import { cn } from "@/lib/utils";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, ArrowRight, Check } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

const ACTIVITIES = ["Commerce", "Service local", "Logiciel", "Industrie", "Conseil"] as const;
const MARKETS = ["France", "Belgique", "Suisse", "Canada"] as const;
const STEPS = 8;
const SEED_COUNT = 3;
const DEFAULT_ENGINES: Provider[] = ["openai", "perplexity", "gemini"];
const MAX_QUESTIONS = 200;

function suggestBrand(domain: string) {
  const host = domain.trim().replace(/^https?:\/\//i, "").split("/")[0]?.replace(/^www\./i, "") ?? "";
  return (host.split(".")[0] ?? "").replace(/[-_]+/g, " ").trim();
}

function sectorLine(offer: string, market: string, city: string, multi: boolean) {
  const place = [market, city.trim()].filter(Boolean).join(", ");
  const where = multi ? `${place}, plusieurs pays` : place;
  return `${offer.trim()} · ${where}`.slice(0, 80);
}

export function OnboardingWizard({ onDone }: { onDone: () => void }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const settings = useQuery({ queryKey: ["settings"], queryFn: () => api<Settings>("/settings") });
  const [step, setStep] = useState(0);
  const [domain, setDomain] = useState("");
  const [brand, setBrand] = useState("");
  const [offer, setOffer] = useState("");
  const [market, setMarket] = useState("France");
  const [city, setCity] = useState("");
  const [multi, setMulti] = useState(false);
  const [engines, setEngines] = useState<Provider[]>(DEFAULT_ENGINES);
  const [seeds, setSeeds] = useState<string[]>(["", "", ""]);
  const [questions, setQuestions] = useState<string[]>([""]);
  const [coach, setCoach] = useState(false);
  const [coachPage, setCoachPage] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [readyBrand, setReadyBrand] = useState(false);
  const request = useRef(0);
  const coachOnce = useRef(false);
  const generatedFrom = useRef("");

  useEffect(() => {
    const saved = rememberedDomain();
    if (saved) setDomain(saved);
  }, []);

  useEffect(() => {
    if (!settings.data || readyBrand) return;
    setBrand(settings.data.brandName);
    setReadyBrand(true);
  }, [readyBrand, settings.data]);

  function keptQuestions(list: string[]) {
    return list.map((item) => item.trim()).filter((item) => item.length >= 8);
  }

  function go(next: number) {
    setError(null);
    setStep(next);
    if (next === 6) {
      const key = keptQuestions(seeds).join("\n");
      if (key !== generatedFrom.current) void propose();
    }
  }

  async function propose() {
    const written = keptQuestions(seeds).slice(0, SEED_COUNT);
    const id = request.current + 1;
    request.current = id;
    setGenerating(true);
    setError(null);
    setQuestions(written);
    try {
      const result = await generateQuestions({
        brandName: brand.trim().slice(0, 80),
        domain: domain.trim(),
        sector: sectorLine(offer, market, city, multi),
        existing: written,
      });
      if (request.current !== id) return;
      const extra = result.questions.filter((item) => !written.some((seed) => seed.toLocaleLowerCase("fr-FR") === item.toLocaleLowerCase("fr-FR")));
      setQuestions([...written, ...extra].slice(0, MAX_QUESTIONS));
      generatedFrom.current = written.join("\n");
      if (!coachOnce.current) {
        coachOnce.current = true;
        setCoach(true);
        setCoachPage(0);
      }
    } catch (caught) {
      if (request.current !== id) return;
      setError(caught instanceof ApiError ? caught.message : "La génération n'a pas abouti.");
    } finally {
      if (request.current === id) setGenerating(false);
    }
  }

  function validate(index: number) {
    if (index === 0) {
      const host = domain.trim().replace(/^https?:\/\//i, "").split("/")[0] ?? "";
      if (!host.includes(".") || host.length < 3) return "Indiquez l'adresse du site, par exemple atelier-nord.fr.";
    }
    if (index === 1 && brand.trim().length < 1) return "Indiquez le nom de la marque.";
    if (index === 2 && offer.trim().length < 2) return "Décrivez en quelques mots ce que l'entreprise vend.";
    if (index === 3 && !market.trim()) return "Choisissez un pays.";
    if (index === 4 && engines.length !== 3) return "Choisissez trois modèles.";
    if (index === 5) {
      const written = seeds.map((item) => item.trim());
      if (written.length !== SEED_COUNT || written.some((item) => item.length < 8)) {
        return "Écrivez trois questions, telles qu'un client les poserait.";
      }
      const distinct = new Set(written.map((item) => item.toLocaleLowerCase("fr-FR")));
      if (distinct.size !== SEED_COUNT) return "Les trois questions doivent être différentes.";
    }
    if (index === 6 && !questions.some((item) => item.trim().length >= 8)) {
      return "Gardez au moins une question.";
    }
    return null;
  }

  function forward() {
    if (generating) return;
    const problem = validate(step);
    if (problem) {
      setError(problem);
      return;
    }
    if (step === 0 && brand.trim().length < 1) setBrand(suggestBrand(domain));
    if (step < STEPS - 1) go(step + 1);
    else void finish();
  }

  async function finish() {
    const problem = validate(6);
    if (problem) {
      setError(problem);
      setStep(6);
      return;
    }
    const payload: SettingsInput = {
      workspaceName: brand.trim().slice(0, 80),
      brandName: brand.trim().slice(0, 80),
      domain: domain.trim(),
      sector: sectorLine(offer, market, city, multi),
      providers: engines,
      queries: keptQuestions(questions)
        .slice(0, MAX_QUESTIONS)
        .map((prompt) => ({ prompt: prompt.slice(0, 400), active: true })),
    };
    setPending(true);
    setError(null);
    try {
      await saveSettings(payload);
      forgetDomain();
      try {
        await runTracking({});
      } catch (caught) {
        const message = caught instanceof ApiError ? caught.message : "Le suivi n'a pas pu démarrer.";
        await queryClient.invalidateQueries({ queryKey: ["settings"] });
        await queryClient.invalidateQueries({ queryKey: ["me"] });
        if (message.toLowerCase().includes("forfait")) {
          router.push("/billing");
          return;
        }
        setError(message);
        setPending(false);
        return;
      }
      await queryClient.invalidateQueries({ queryKey: ["settings"] });
      await queryClient.invalidateQueries({ queryKey: ["me"] });
      await queryClient.invalidateQueries({ queryKey: ["tracking"] });
      await queryClient.invalidateQueries({ queryKey: ["overview"] });
      onDone();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "L'enregistrement n'a pas abouti.");
      setPending(false);
    }
  }

  function addSuggestion(text: string) {
    setSeeds((current) => {
      const empty = current.findIndex((item) => item.trim().length === 0);
      if (empty < 0) return current;
      return current.map((item, index) => (index === empty ? text : item));
    });
  }

  const place = city.trim() || market;
  const offerText = offer.trim().toLocaleLowerCase("fr-FR");
  const suggestions = [
    `Quel est le meilleur ${offerText || "prestataire"} à ${place} ?`,
    `Qui contacter pour ${offerText || "ce métier"} à ${place} ?`,
    `Comment choisir un ${offerText || "prestataire"} à ${place} ?`,
  ];

  return (
    <div className="fixed inset-0 z-50 flex flex-col bg-background">
      <div className="mx-auto flex w-full max-w-lg flex-1 flex-col px-5 py-6">
        <div className="flex gap-1" aria-hidden="true">
          {Array.from({ length: STEPS }, (_, index) => (
            <span key={index} className={cn("h-1 flex-1 rounded-full", index <= step ? "bg-foreground" : "bg-border")} />
          ))}
        </div>
        <p className="sr-only">
          Étape {step + 1} sur {STEPS}
        </p>

        <div key={step} className="mt-8 min-h-0 flex-1 overflow-y-auto motion-safe:animate-none">
          {step === 0 ? (
            <>
              <h1 className="text-3xl font-semibold tracking-[-0.03em]">Quel site faut-il suivre ?</h1>
              <p className="mt-3 text-base leading-6 text-muted-foreground">
                On commence par là. Vous écrirez ensuite trois questions de clients, et le site servira à les compléter.
              </p>
              <Input
                className="mt-8 h-12 text-base"
                autoFocus
                inputMode="url"
                autoComplete="url"
                placeholder="atelier-nord.fr"
                aria-label="Adresse du site"
                value={domain}
                onChange={(event) => setDomain(event.target.value)}
              />
            </>
          ) : null}

          {step === 1 ? (
            <>
              <h1 className="text-3xl font-semibold tracking-[-0.03em]">Quel nom les IA doivent-elles reconnaître ?</h1>
              <p className="mt-3 text-base leading-6 text-muted-foreground">
                Le nom exact, tel qu'un client le dit. Pas le slogan.
              </p>
              <Input
                className="mt-8 h-12 text-base"
                autoFocus
                aria-label="Nom de la marque"
                value={brand}
                onChange={(event) => setBrand(event.target.value)}
              />
            </>
          ) : null}

          {step === 2 ? (
            <>
              <h1 className="text-3xl font-semibold tracking-[-0.03em]">Que vend cette entreprise ?</h1>
              <p className="mt-3 text-base leading-6 text-muted-foreground">
                Une phrase suffit. Elle sert à écrire des questions que vos clients posent vraiment.
              </p>
              <div className="mt-6 flex flex-wrap gap-2">
                {ACTIVITIES.map((item) => (
                  <button
                    key={item}
                    type="button"
                    aria-pressed={offer === item}
                    onClick={() => setOffer(item)}
                    className={cn(
                      "rounded-full border px-3 py-2 text-sm font-semibold",
                      offer === item ? "border-foreground bg-foreground text-background" : "border-border bg-background",
                    )}
                  >
                    {item}
                  </button>
                ))}
              </div>
              <Textarea
                className="mt-4"
                aria-label="Activité"
                placeholder="Boulangerie artisanale, pain au levain et snacking"
                value={offer}
                onChange={(event) => setOffer(event.target.value)}
              />
            </>
          ) : null}

          {step === 3 ? (
            <>
              <h1 className="text-3xl font-semibold tracking-[-0.03em]">Où sont vos clients ?</h1>
              <p className="mt-3 text-base leading-6 text-muted-foreground">
                Le pays d'abord. La ville, si l'on vous cherche autour de chez vous.
              </p>
              <div className="mt-6 flex flex-wrap gap-2">
                {MARKETS.map((item) => (
                  <button
                    key={item}
                    type="button"
                    aria-pressed={market === item}
                    onClick={() => setMarket(item)}
                    className={cn(
                      "rounded-full border px-3 py-2 text-sm font-semibold",
                      market === item ? "border-foreground bg-foreground text-background" : "border-border bg-background",
                    )}
                  >
                    {item}
                  </button>
                ))}
              </div>
              <Input
                className="mt-4"
                aria-label="Ville ou zone"
                placeholder="Lyon, ou laissez vide"
                value={city}
                onChange={(event) => setCity(event.target.value)}
              />
              <button
                type="button"
                aria-pressed={multi}
                onClick={() => setMulti((value) => !value)}
                className="mt-4 flex w-full items-center justify-between gap-4 rounded-xl border border-border px-4 py-4 text-left"
              >
                <span>
                  <span className="block text-sm font-semibold">Plusieurs pays</span>
                  <span className="mt-1 block text-sm text-muted-foreground">
                    On gardera le pays principal, et on notera que vous vendez ailleurs.
                  </span>
                </span>
                <span
                  className={cn(
                    "flex size-6 shrink-0 items-center justify-center rounded-full border",
                    multi ? "border-foreground bg-foreground text-background" : "border-input",
                  )}
                >
                  {multi ? <Check className="size-3.5" aria-hidden="true" /> : null}
                </span>
              </button>
            </>
          ) : null}

          {step === 4 ? (
            <>
              <h1 className="text-3xl font-semibold tracking-[-0.03em]">Quels trois modèles interroger ?</h1>
              <p className="mt-3 text-base leading-6 text-muted-foreground">
                Chaque question part vers ces trois modèles. Choisissez-en trois, pas plus.
              </p>
              <div className="mt-6 flex flex-wrap gap-2">
                {PROVIDERS.map((item) => {
                  const selected = engines.includes(item.id);
                  return (
                    <button
                      key={item.id}
                      type="button"
                      aria-pressed={selected}
                      onClick={() => {
                        if (engines.includes(item.id)) {
                          setError(null);
                          setEngines(engines.filter((engine) => engine !== item.id));
                          return;
                        }
                        if (engines.length >= 3) {
                          setError("Trois modèles maximum. Retirez-en un pour en changer.");
                          return;
                        }
                        setError(null);
                        setEngines([...engines, item.id]);
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
              </div>
              <p className="mt-4 text-sm text-muted-foreground">{engines.length} sur 3</p>
            </>
          ) : null}

          {step === 5 ? (
            <>
              <h1 className="text-3xl font-semibold tracking-[-0.03em]">Écrivez trois questions de vos clients.</h1>
              <p className="mt-3 text-base leading-6 text-muted-foreground">
                Claude s'en inspire, avec votre site, pour compléter la liste. L'essai va jusqu'à 10 questions au total. Un forfait va jusqu'au nombre envoyé chaque jour.
              </p>
              <div className="mt-6 flex flex-col gap-2">
                {suggestions.map((item) => (
                  <button
                    key={item}
                    type="button"
                    onClick={() => addSuggestion(item)}
                    className="rounded-xl border border-border px-4 py-3 text-left text-sm hover:bg-muted"
                  >
                    {item}
                  </button>
                ))}
              </div>
              <div className="mt-4 space-y-3">
                {seeds.map((question, index) => (
                  <Textarea
                    key={index}
                    aria-label={`Question ${index + 1}`}
                    placeholder={`Question ${index + 1}`}
                    value={question}
                    onChange={(event) =>
                      setSeeds((current) => current.map((item, itemIndex) => (itemIndex === index ? event.target.value : item)))
                    }
                  />
                ))}
              </div>
            </>
          ) : null}

          {step === 6 ? (
            <>
              <h1 className="text-3xl font-semibold tracking-[-0.03em]">Que demandent vos clients aux IA ?</h1>
              <p className="mt-3 text-base leading-6 text-muted-foreground">
                Vos trois questions sont en tête. Les suivantes viennent du site et de ces exemples. Relisez-les avant de continuer.
              </p>
              {generating ? (
                <p className="mt-8 text-sm font-semibold" role="status">
                  Lecture du site et rédaction des questions…
                </p>
              ) : (
                <>
                  <div className="mt-4 space-y-3">
                    {questions.map((question, index) => (
                      <div key={index} className="grid grid-cols-[1fr_auto] items-start gap-2">
                        <Textarea
                          aria-label={`Question ${index + 1}`}
                          value={question}
                          onChange={(event) =>
                            setQuestions((current) => current.map((item, itemIndex) => (itemIndex === index ? event.target.value : item)))
                          }
                        />
                        <Button
                          type="button"
                          variant="ghost"
                          onClick={() =>
                            setQuestions((current) => {
                              const next = current.filter((_, itemIndex) => itemIndex !== index);
                              return next.length > 0 ? next : [""];
                            })
                          }
                        >
                          Retirer
                        </Button>
                      </div>
                    ))}
                  </div>
                  <div className="mt-4 flex flex-wrap gap-2">
                    <Button type="button" variant="outline" onClick={() => void propose()}>
                      Générer à nouveau
                    </Button>
                    {questions.length < MAX_QUESTIONS ? (
                      <Button type="button" variant="outline" onClick={() => setQuestions((current) => [...current, ""])}>
                        Ajouter une question
                      </Button>
                    ) : null}
                  </div>
                </>
              )}
            </>
          ) : null}

          {step === 7 ? (
            <>
              <h1 className="text-3xl font-semibold tracking-[-0.03em]">Voici ce qu'on va mesurer.</h1>
              <p className="mt-3 text-base leading-6 text-muted-foreground">
                Ces questions sont envoyées aux trois modèles choisis. Le suivi mesure s'ils vous citent.
              </p>
              <dl className="mt-6 divide-y divide-border rounded-xl border border-border">
                <Summary label="Site" value={domain.trim()} />
                <Summary label="Marque" value={brand.trim()} />
                <Summary label="Activité" value={sectorLine(offer, market, city, multi)} />
                <Summary label="Modèles" value={engines.map((item) => providerLabel(item)).join(", ")} />
                <Summary
                  label="Questions"
                  value={questions.map((item) => item.trim()).filter((item) => item.length >= 8).join(" · ") || "Aucune"}
                />
              </dl>
            </>
          ) : null}
        </div>

        {pending ? <div className="mt-4"><RunProgressBar active /></div> : null}
        {error ? <p className="mt-4 text-sm font-semibold">{error}</p> : null}

        <div className="mt-auto flex items-center justify-end gap-3 pt-8">
          <div className="flex gap-2">
            {step > 0 ? (
              <Button type="button" variant="outline" onClick={() => go(step - 1)} disabled={pending || generating}>
                <ArrowLeft />
                Précédent
              </Button>
            ) : null}
            <Button type="button" onClick={forward} disabled={pending || generating}>
              {pending ? "Envoi des questions…" : step === STEPS - 1 ? "Lancer le suivi" : "Continuer"}
              {pending || step === STEPS - 1 ? null : <ArrowRight />}
            </Button>
          </div>
        </div>
      </div>

      {coach && step === 6 ? (
        <div className="fixed inset-0 z-[60] flex items-end justify-center bg-foreground/40 p-4 sm:items-center">
          <div className="w-full max-w-md rounded-2xl bg-background p-6 shadow-float" role="dialog" aria-modal="true" aria-labelledby="coach-title">
            <p className="text-sm text-muted-foreground">
              {coachPage + 1} sur 2
            </p>
            {coachPage === 0 ? (
              <>
                <h2 id="coach-title" className="mt-2 text-2xl font-semibold tracking-[-0.02em]">
                  Une question sert à mesurer, pas à vous présenter.
                </h2>
                <ul className="mt-4 space-y-3 text-sm leading-6">
                  <li>Comparaison : « meilleur {offer.trim().toLocaleLowerCase("fr-FR") || "produit"} » contre un concurrent.</li>
                  <li>Proximité : « autour de {city.trim() || market} », horaires, déplacement.</li>
                  <li>Expertise : « comment choisir » dans votre métier.</li>
                </ul>
              </>
            ) : (
              <>
                <h2 id="coach-title" className="mt-2 text-2xl font-semibold tracking-[-0.02em]">
                  Évitez de guider la réponse.
                </h2>
                <p className="mt-4 text-sm font-semibold">À éviter</p>
                <p className="mt-1 text-sm text-muted-foreground">{brand.trim() || "Ma marque"} est-il connu ?</p>
                <p className="mt-4 text-sm font-semibold">À privilégier</p>
                <p className="mt-1 text-sm text-muted-foreground">
                  Quel {offer.trim().toLocaleLowerCase("fr-FR") || "prestataire"} choisir à {place}, face à un concurrent ?
                </p>
              </>
            )}
            <div className="mt-6 flex items-center justify-between gap-3">
              <button type="button" className="text-sm font-semibold text-muted-foreground" onClick={() => setCoach(false)}>
                Passer l'explication
              </button>
              <Button type="button" onClick={() => (coachPage === 0 ? setCoachPage(1) : setCoach(false))}>
                {coachPage === 0 ? "Suivant" : "Relire les questions"}
              </Button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}

function Summary({ label, value }: { label: string; value: string }) {
  return (
    <div className="px-4 py-3">
      <dt className="text-sm text-muted-foreground">{label}</dt>
      <dd className="mt-1 text-sm font-semibold">{value}</dd>
    </div>
  );
}
