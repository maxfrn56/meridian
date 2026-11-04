import { cn } from "@/lib/utils";

/* Champ : bord gris à 3:1 pour rester visible (AA), contour encre au focus. */
export function Input({ className, ...props }: React.ComponentProps<"input">) {
  return (
    <input
      className={cn(
        "h-10 w-full rounded-lg border border-input bg-background px-3 text-sm font-medium text-foreground shadow-xs outline-none transition-[border-color,box-shadow] duration-300 ease-out placeholder:text-muted-foreground focus-visible:border-foreground focus-visible:ring-4 focus-visible:ring-foreground/10 aria-invalid:border-foreground aria-invalid:ring-1 aria-invalid:ring-foreground",
        className,
      )}
      {...props}
    />
  );
}
