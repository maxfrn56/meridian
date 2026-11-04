import { cn } from "@/lib/utils";

/* Carte : fond blanc, filet de 1 px, rayon de 12 px, ombre très légère (voir DESIGN.md). */
export function Card({ className, ...props }: React.ComponentProps<"section">) {
  return (
    <section
      className={cn("print-surface rounded-xl border border-border bg-card shadow-xs", className)}
      {...props}
    />
  );
}

export function CardHeader({ className, ...props }: React.ComponentProps<"div">) {
  return <div className={cn("flex items-start justify-between gap-3 px-5 pt-5", className)} {...props} />;
}

export function CardTitle({ className, ...props }: React.ComponentProps<"h2">) {
  return <h2 className={cn("text-sm font-semibold text-foreground", className)} {...props} />;
}

export function CardContent({ className, ...props }: React.ComponentProps<"div">) {
  return <div className={cn("px-5 pb-5", className)} {...props} />;
}
