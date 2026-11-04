import { cn } from "@/lib/utils";

export function Textarea({ className, ...props }: React.ComponentProps<"textarea">) {
  return (
    <textarea
      className={cn(
        "min-h-20 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm font-medium text-foreground shadow-xs outline-none transition-[border-color,box-shadow] duration-300 ease-out placeholder:text-muted-foreground focus-visible:border-foreground focus-visible:ring-4 focus-visible:ring-foreground/10",
        className,
      )}
      {...props}
    />
  );
}
