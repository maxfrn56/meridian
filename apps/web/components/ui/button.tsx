import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

/*
 * Boutons en pilule (voir DESIGN.md).
 * - default : l'action principale de l'écran, en orange. Une seule par écran.
 * - outline : toutes les autres actions.
 * - ghost : actions discrètes dans une liste (retirer, annuler).
 * - secondary : action neutre sur fond de surface.
 */
const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-full text-sm font-semibold transition-[background-color,box-shadow,color] duration-300 ease-out disabled:pointer-events-none disabled:opacity-50 outline-none focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-foreground [&_svg]:size-4",
  {
    variants: {
      variant: {
        default:
          "bg-primary text-primary-foreground shadow-[0_1px_2px_rgb(17_19_24/0.1),inset_0_1px_0_rgb(255_255_255/0.22)] hover:bg-primary-hover",
        outline: "border border-border bg-background text-foreground shadow-xs hover:bg-muted",
        ghost: "text-muted-foreground hover:bg-muted hover:text-foreground",
        secondary: "bg-muted text-foreground hover:bg-border",
      },
      size: {
        default: "h-10 px-4",
        sm: "h-8 px-3 text-xs",
        lg: "h-12 px-6 text-base",
        icon: "size-10",
      },
    },
    defaultVariants: { variant: "default", size: "default" },
  },
);

export function Button({
  className,
  variant,
  size,
  asChild = false,
  ...props
}: React.ComponentProps<"button"> & VariantProps<typeof buttonVariants> & { asChild?: boolean }) {
  const Comp = asChild ? Slot : "button";
  return <Comp className={cn(buttonVariants({ variant, size }), className)} {...props} />;
}
