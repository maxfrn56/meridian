/*
 * En-tête de page. Pas de petit label en capitales au-dessus du titre (voir DESIGN.md) :
 * une précision de contexte (semaine, secteur) se place sous le titre, en texte secondaire.
 */
export function PageHeader({
  meta,
  title,
  description,
  action,
}: {
  meta?: string;
  title: string;
  description?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="text-3xl font-semibold tracking-[-0.03em] text-balance sm:text-4xl">{title}</h1>
        {meta ? <p className="mt-1 text-sm text-muted-foreground">{meta}</p> : null}
        {description ? <p className="mt-3 max-w-2xl text-base leading-7 text-muted-foreground text-pretty">{description}</p> : null}
      </div>
      <div className="no-print flex flex-wrap gap-2">{action}</div>
    </div>
  );
}
