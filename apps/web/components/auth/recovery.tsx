"use client";

import { AuthFrame } from "@/components/auth/screen";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError, requestPasswordReset, resetPassword, verifyEmail } from "@/lib/api";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

export function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setPending(true);
    setError(null);
    try {
      const result = await requestPasswordReset(email);
      setNotice(result.message);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Envoi impossible.");
    } finally {
      setPending(false);
    }
  }

  return (
    <AuthFrame title="Mot de passe oublié" subtitle="Un lien valable une heure est envoyé si un compte existe.">
      {notice ? (
        <p className="mt-8 text-sm leading-6">{notice}</p>
      ) : (
        <form onSubmit={submit}>
          <div className="mt-8 grid gap-1.5">
            <Label htmlFor="email">E-mail</Label>
            <Input id="email" type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
          </div>
          {error ? <p className="mt-4 text-sm text-destructive">{error}</p> : null}
          <Button type="submit" className="mt-6 w-full" disabled={pending}>
            {pending ? "Patientez…" : "Envoyer le lien"}
          </Button>
        </form>
      )}
      <p className="mt-6 text-sm text-muted-foreground">
        <Link href="/login" className="text-foreground underline-offset-4 hover:underline">
          Retour à la connexion
        </Link>
      </p>
    </AuthFrame>
  );
}

export function ResetPassword() {
  const params = useSearchParams();
  const token = params.get("token") ?? "";
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    if (password !== confirmation) {
      setError("Les deux mots de passe ne correspondent pas.");
      return;
    }
    setPending(true);
    try {
      const result = await resetPassword(token, password);
      setNotice(result.message);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Réinitialisation impossible.");
    } finally {
      setPending(false);
    }
  }

  return (
    <AuthFrame title="Nouveau mot de passe" subtitle="8 caractères minimum, avec une lettre et un chiffre.">
      {!token ? <p className="mt-8 text-sm text-destructive">Ce lien est incomplet. Demandez-en un nouveau.</p> : null}
      {notice ? (
        <p className="mt-8 text-sm leading-6">{notice}</p>
      ) : (
        <form onSubmit={submit}>
          <div className="mt-8 grid gap-4">
            <div className="grid gap-1.5">
              <Label htmlFor="password">Nouveau mot de passe</Label>
              <Input id="password" type="password" autoComplete="new-password" value={password} onChange={(event) => setPassword(event.target.value)} required minLength={8} />
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="confirmation">Confirmer</Label>
              <Input id="confirmation" type="password" autoComplete="new-password" value={confirmation} onChange={(event) => setConfirmation(event.target.value)} required minLength={8} />
            </div>
          </div>
          {error ? <p className="mt-4 text-sm text-destructive">{error}</p> : null}
          <Button type="submit" className="mt-6 w-full" disabled={pending || !token}>
            {pending ? "Patientez…" : "Enregistrer"}
          </Button>
        </form>
      )}
      <p className="mt-6 text-sm text-muted-foreground">
        <Link href="/login" className="text-foreground underline-offset-4 hover:underline">
          Aller à la connexion
        </Link>
      </p>
    </AuthFrame>
  );
}

export function VerifyEmail() {
  const params = useSearchParams();
  const token = params.get("token") ?? "";
  const [message, setMessage] = useState("Confirmation en cours…");
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (!token) {
      setFailed(true);
      setMessage("Ce lien est incomplet. Demandez un nouvel e-mail de confirmation.");
      return;
    }
    let active = true;
    verifyEmail(token)
      .then((result) => {
        if (active) setMessage(result.message);
      })
      .catch((caught: unknown) => {
        if (!active) return;
        setFailed(true);
        setMessage(caught instanceof ApiError ? caught.message : "Confirmation impossible.");
      });
    return () => {
      active = false;
    };
  }, [token]);

  return (
    <AuthFrame title="Confirmation d'inscription" subtitle="Le lien reçu par e-mail active le compte.">
      <p className={`mt-8 text-sm leading-6 ${failed ? "text-destructive" : ""}`}>{message}</p>
      <p className="mt-6 text-sm text-muted-foreground">
        <Link href="/login" className="text-foreground underline-offset-4 hover:underline">
          Aller à la connexion
        </Link>
      </p>
    </AuthFrame>
  );
}
