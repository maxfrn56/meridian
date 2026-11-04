"use client";

import { ArrowRight } from "lucide-react";
import { useRouter } from "next/navigation";
import { useRef, useState, type FormEvent } from "react";

const DOMAIN_PATTERN = /^(?=.{4,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$/;

/** Accepte « https://www.exemple.fr/page » comme « exemple.fr ». */
export function normalizeDomain(raw: string): string | null {
  const domain = raw
    .trim()
    .toLowerCase()
    .replace(/^[a-z]+:\/\//, "")
    .replace(/^www\./, "")
    .split(/[/?#]/)[0]
    .replace(/:\d+$/, "")
    .replace(/\.$/, "");
  return DOMAIN_PATTERN.test(domain) ? domain : null;
}

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
