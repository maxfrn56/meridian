import { cn } from "@/lib/utils";

/*
 * Pastilles. Pas de vert ni de rouge : l'état se lit par la forme et le libellé (voir DESIGN.md).
 * - neutral : information.
 * - good : réussi, en place.
 * - warn : à surveiller (contour).
 * - bad : à corriger en priorité (plein, encre).
 * - brand : donnée de la marque du client (seul usage de l'orange dans une pastille).
 */
const tones = {
  neutral: "bg-muted text-muted-foreground border border-border",
  good: "bg-muted text-foreground border border-border",
  warn: "bg-background text-foreground border border-foreground/40",
  bad: "bg-foreground text-background border border-foreground",
  brand: "bg-primary-soft text-foreground border border-primary/30",
};

export function Badge({
  className,
  tone = "neutral",
  ...props
}: React.ComponentProps<"span"> & { tone?: keyof typeof tones }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-semibold tabular-nums",
        tones[tone],
        className,
      )}
      {...props}
    />
  );
}
