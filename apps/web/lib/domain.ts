const DOMAIN_PATTERN = /^(?=.{4,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$/;

/** Le domaine saisi sur la page d'accueil, gardé jusqu'à l'ouverture de l'espace. */
export const PENDING_DOMAIN_KEY = "meridian_domain";

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

export function rememberDomain(raw: string) {
  const domain = normalizeDomain(raw);
  if (!domain) return;
  localStorage.setItem(PENDING_DOMAIN_KEY, domain);
}

export function rememberedDomain(): string {
  return normalizeDomain(localStorage.getItem(PENDING_DOMAIN_KEY) ?? "") ?? "";
}

export function forgetDomain() {
  localStorage.removeItem(PENDING_DOMAIN_KEY);
}
