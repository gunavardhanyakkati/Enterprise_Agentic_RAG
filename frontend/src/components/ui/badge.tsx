import { cn } from "@/lib/utils";

export function Badge({
  className,
  variant = "default",
  ...props
}: React.HTMLAttributes<HTMLDivElement> & { variant?: "default" | "secondary" | "success" | "warning" | "destructive" }) {
  return (
    <div
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold",
        variant === "default" && "border-transparent bg-primary text-primary-foreground",
        variant === "secondary" && "border-transparent bg-secondary text-secondary-foreground",
        variant === "success" && "border-transparent bg-emerald-600/20 text-emerald-300",
        variant === "warning" && "border-transparent bg-amber-600/20 text-amber-300",
        variant === "destructive" && "border-transparent bg-destructive/20 text-red-300",
        className,
      )}
      {...props}
    />
  );
}
