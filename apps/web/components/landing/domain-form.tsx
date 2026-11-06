"use client";

import { rememberDomain, normalizeDomain } from "@/lib/domain";
import { ArrowRight } from "lucide-react";
import { useRouter } from "next/navigation";
import { useRef, useState, type FormEvent } from "react";

/** Champ « votre domaine » + bouton d'audit. Sans JavaScript, le formulaire envoie quand même vers /register. */
export function DomainForm({ id }: { id: string }) {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [error, setError] = useState<string | null>(null);
  const inputId = `${id}-domain`;
  const errorId = `${id}-error`;

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const domain = normalizeDomain(String(new FormData(event.currentTarget).get("domain") ?? ""));
    if (!domain) {
      setError("Saisissez un nom de domaine valide, par exemple votre-entreprise.fr.");
      inputRef.current?.focus();
      return;
    }
    setError(null);
    rememberDomain(domain);
    router.push(`/register?domain=${encodeURIComponent(domain)}`);
  }

  return (
    <form className="lp-domain" action="/register" method="get" noValidate onSubmit={submit}>
      <label className="visually-hidden" htmlFor={inputId}>
        Votre nom de domaine
      </label>
      <div className="lp-domain__row">
        <div className="lp-domain__field">
          <span className="lp-domain__prefix" aria-hidden="true">
            https://
          </span>
          <input
            ref={inputRef}
            id={inputId}
            name="domain"
            className="lp-domain__input"
            type="text"
            inputMode="url"
            autoComplete="url"
            autoCapitalize="none"
            spellCheck={false}
            placeholder="votre-entreprise.fr"
            aria-invalid={error ? true : undefined}
            aria-describedby={error ? errorId : undefined}
            onChange={() => error && setError(null)}
          />
        </div>
        <button type="submit" className="lp-btn lp-btn--accent lp-btn--lg">
          Lancer l&apos;audit gratuit
          <ArrowRight aria-hidden="true" className="lp-btn__icon" />
        </button>
      </div>
      <p id={errorId} className="lp-domain__error" aria-live="polite">
        {error}
      </p>
    </form>
  );
}
