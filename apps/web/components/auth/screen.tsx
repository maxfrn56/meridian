"use client";

import { Globe, LogoMark } from "@/components/landing/globe";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError, TOKEN_KEY, api, login, register, resendVerification } from "@/lib/api";
import type { User } from "@/lib/types";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

export function AuthFrame({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle: string;
  children: React.ReactNode;
}) {
  return (
    <div className="grid min-h-screen lg:grid-cols-[1.1fr_0.9fr]">
      <section className="relative isolate hidden flex-col justify-between overflow-hidden border-r border-border bg-muted px-12 py-10 lg:flex">
        <Globe
          id="auth"
          className="pointer-events-none absolute top-[58%] left-1/2 -z-10 w-[130%] -translate-x-1/2 text-[#dcdfe5]"
        />
        <Link href="/" className="logo-turn flex w-fit items-center gap-2 text-lg font-semibold tracking-[-0.02em]">
          <LogoMark className="size-[22px]" />
          Meridian
        </Link>
        <div>
          <h1 className="max-w-md text-4xl font-semibold leading-[1.1] tracking-[-0.03em] text-balance">
            Voyez ce que les IA disent de vous. <span className="text-muted-foreground">Puis changez la réponse.</span>
          </h1>
          <p className="mt-4 max-w-md text-base leading-7 text-muted-foreground">
            Taux de citation, part de voix face aux concurrents, audit du site et actions classées par priorité.
          </p>
        </div>
        <p className="text-sm text-muted-foreground">Analyse quotidienne sur ChatGPT, Perplexity et Gemini</p>
      </section>
      <section className="flex flex-col items-center justify-center px-6 py-16">
        <Link href="/" className="logo-turn mb-10 flex items-center gap-2 text-lg font-semibold tracking-[-0.02em] lg:hidden">
          <LogoMark className="size-[22px]" />
          Meridian
        </Link>
        <div className="w-full max-w-sm">
          <h2 className="text-3xl font-semibold tracking-[-0.03em]">{title}</h2>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">{subtitle}</p>
          {children}
        </div>
      </section>
    </div>
  );
}

export function AuthScreen({ mode }: { mode: "login" | "register" }) {
  const router = useRouter();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [needsVerification, setNeedsVerification] = useState(false);
  const [pending, setPending] = useState(false);

  useEffect(() => {
    if (!localStorage.getItem(TOKEN_KEY)) return;
    api<User>("/auth/me")
      .then((user) => router.replace(user.role === "admin" ? "/admin" : "/dashboard"))
      .catch(() => undefined);
  }, [router]);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setPending(true);
    setError(null);
    setNotice(null);
    setNeedsVerification(false);
    try {
      if (mode === "register" && password !== confirmation) {
        setError("Les deux mots de passe ne correspondent pas.");
        setPending(false);
        return;
      }
      if (mode === "login") {
        const result = await login(email, password);
        localStorage.setItem(TOKEN_KEY, result.token);
        router.push(result.user.role === "admin" ? "/admin" : "/dashboard");
        return;
      }
      const result = await register(name, email, password);
      setNotice(result.message);
      setPending(false);
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 403) setNeedsVerification(true);
      setError(caught instanceof ApiError ? caught.message : "Connexion impossible.");
      setPending(false);
    }
  }

  async function resend() {
    setPending(true);
    setError(null);
    try {
      const result = await resendVerification(email);
      setNotice(result.message);
      setNeedsVerification(false);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Envoi impossible.");
    } finally {
      setPending(false);
    }
  }

  return (
    <AuthFrame
      title={mode === "login" ? "Connexion" : "Créer un espace"}
      subtitle={mode === "login" ? "Revenez à votre espace de suivi." : "Un e-mail de confirmation est envoyé avant l'ouverture du compte."}
    >
      {notice && mode === "register" ? (
        <div className="mt-8">
          <p className="text-sm leading-6">{notice}</p>
          <p className="mt-6 text-sm text-muted-foreground">
            <Link href="/login" className="text-foreground underline-offset-4 hover:underline">
              Aller à la connexion
            </Link>
          </p>
        </div>
      ) : (
        <form onSubmit={submit}>
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
              <div className="flex items-center justify-between gap-3">
                <Label htmlFor="password">Mot de passe</Label>
                {mode === "login" ? (
                  <Link href="/forgot-password" className="text-xs text-muted-foreground underline-offset-4 hover:underline">
                    Mot de passe oublié
                  </Link>
                ) : null}
              </div>
              <Input
                id="password"
                type="password"
                autoComplete={mode === "login" ? "current-password" : "new-password"}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
                minLength={8}
              />
              {mode === "register" ? (
                <p className="text-xs text-muted-foreground">8 caractères minimum, avec une lettre et un chiffre.</p>
              ) : null}
            </div>
            {mode === "register" ? (
              <div className="grid gap-1.5">
                <Label htmlFor="confirmation">Confirmer le mot de passe</Label>
                <Input
                  id="confirmation"
                  type="password"
                  autoComplete="new-password"
                  value={confirmation}
                  onChange={(event) => setConfirmation(event.target.value)}
                  required
                  minLength={8}
                />
              </div>
            ) : null}
          </div>
          {error ? <p className="mt-4 text-sm font-semibold text-destructive">{error}</p> : null}
          {notice ? <p className="mt-4 text-sm text-muted-foreground">{notice}</p> : null}
          {needsVerification ? (
            <Button type="button" variant="outline" className="mt-4 w-full" disabled={pending || !email} onClick={resend}>
              Renvoyer l'e-mail de confirmation
            </Button>
          ) : null}
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
      )}
    </AuthFrame>
  );
}
