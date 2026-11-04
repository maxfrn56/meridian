"use client";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError, TOKEN_KEY, login, register } from "@/lib/api";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

export function AuthScreen({ mode }: { mode: "login" | "register" }) {
  const router = useRouter();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  useEffect(() => {
    if (localStorage.getItem(TOKEN_KEY)) router.replace("/dashboard");
  }, [router]);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setPending(true);
    setError(null);
    try {
      const result =
        mode === "login" ? await login(email, password) : await register(name, email, password);
      localStorage.setItem(TOKEN_KEY, result.token);
      router.push("/dashboard");
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Connexion impossible.");
      setPending(false);
    }
  }

  return (
    <div className="grid min-h-screen lg:grid-cols-[1.1fr_0.9fr]">
      <section className="hidden flex-col justify-between border-r border-border px-12 py-10 lg:flex">
        <p className="text-sm font-medium tracking-[0.18em] text-primary uppercase">Meridian</p>
        <div>
          <h1 className="max-w-md text-4xl font-semibold tracking-tight">
            Mesurez ce que les moteurs génératifs disent de votre marque.
          </h1>
          <p className="mt-4 max-w-md text-sm leading-6 text-muted-foreground">
            Taux de citation, part de voix face aux concurrents, audit du site et actions classées par priorité.
          </p>
        </div>
        <p className="text-xs text-muted-foreground">GEO · OpenAI · Perplexity · Gemini</p>
      </section>
      <section className="flex items-center justify-center px-6 py-16">
        <form onSubmit={submit} className="w-full max-w-sm">
          <h2 className="text-2xl font-semibold tracking-tight">
            {mode === "login" ? "Connexion" : "Créer un espace"}
          </h2>
          <p className="mt-2 text-sm text-muted-foreground">
            {mode === "login" ? "Revenez à votre espace de suivi." : "Un espace vide, à configurer ensuite."}
          </p>
          <div className="mt-8 grid gap-4">
            {mode === "register" ? (
              <div className="grid gap-1.5">
                <Label htmlFor="name">Nom</Label>
                <Input id="name" value={name} onChange={(event) => setName(event.target.value)} required minLength={2} />
              </div>
            ) : null}
            <div className="grid gap-1.5">
              <Label htmlFor="email">E-mail</Label>
              <Input
                id="email"
                type="email"
                autoComplete="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                required
              />
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="password">Mot de passe</Label>
              <Input
                id="password"
                type="password"
                autoComplete={mode === "login" ? "current-password" : "new-password"}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
                minLength={8}
              />
            </div>
          </div>
          {error ? <p className="mt-4 text-sm text-destructive">{error}</p> : null}
          <Button type="submit" className="mt-6 w-full" disabled={pending}>
            {pending ? "Patientez…" : mode === "login" ? "Entrer" : "Créer le compte"}
          </Button>
          {mode === "login" ? (
            <Button
              type="button"
              variant="outline"
              className="mt-3 w-full"
              onClick={() => {
                setEmail("demo@geo.dev");
                setPassword("meridian");
              }}
            >
              Préremplir le compte démo
            </Button>
          ) : null}
          <p className="mt-6 text-sm text-muted-foreground">
            {mode === "login" ? (
              <>
                Pas encore de compte ?{" "}
                <Link href="/register" className="text-foreground underline-offset-4 hover:underline">
                  Créer un espace
                </Link>
              </>
            ) : (
              <>
                Déjà inscrit ?{" "}
                <Link href="/login" className="text-foreground underline-offset-4 hover:underline">
                  Se connecter
                </Link>
              </>
            )}
          </p>
          {mode === "login" ? (
            <p className="mt-4 text-xs leading-5 text-muted-foreground">Compte démo : demo@geo.dev · meridian</p>
          ) : null}
        </form>
      </section>
    </div>
  );
}
