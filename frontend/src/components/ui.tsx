import { MEASUREMENT, cn } from "@/lib/format";
import { t } from "@/lib/i18n";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import * as TooltipPrimitive from "@radix-ui/react-tooltip";
import { type VariantProps, cva } from "class-variance-authority";
import {
  CheckCircle2,
  ChevronDown,
  CircleHelp,
  FileSignature,
  FlaskConical,
  Gauge,
  Info,
  Loader2,
  MinusCircle,
  X,
} from "lucide-react";
import { type ButtonHTMLAttributes, type ReactNode, useState } from "react";

/* shadcn-style primitives, styled with the project tokens */

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 rounded-[var(--radius-control)] text-sm font-medium transition-colors disabled:pointer-events-none disabled:opacity-50 whitespace-nowrap",
  {
    variants: {
      variant: {
        primary: "bg-navy-900 text-white hover:bg-navy-800",
        accent: "border border-teal-700 bg-surface text-teal-700 hover:bg-teal-50",
        outline: "border border-line-strong bg-surface text-ink hover:bg-paper",
        ghost: "text-muted hover:bg-navy-100/60 hover:text-ink",
        danger: "border border-red-700/30 bg-surface text-red-700 hover:bg-red-100",
      },
      size: { sm: "h-8 px-3 text-[13px]", md: "h-9 px-4", lg: "h-11 px-5 text-[15px]", icon: "h-8 w-8" },
    },
    defaultVariants: { variant: "primary", size: "md" },
  },
);

export function Button({
  className,
  variant,
  size,
  loading,
  children,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & VariantProps<typeof buttonVariants> & { loading?: boolean }) {
  return (
    <button type="button" className={cn(buttonVariants({ variant, size }), className)} {...props}>
      {loading && <Loader2 className="h-4 w-4 animate-spin" />}
      {children}
    </button>
  );
}

export function Card({ className, children, ...p }: { className?: string; children: ReactNode; id?: string }) {
  return (
    <section className={cn("min-w-0 rounded-[var(--radius-card)] border border-line bg-surface", className)} {...p}>
      {children}
    </section>
  );
}

export function CardHeader({
  title,
  subtitle,
  actions,
  className,
}: { title: ReactNode; subtitle?: ReactNode; actions?: ReactNode; className?: string }) {
  return (
    <div
      className={cn(
        "flex min-h-[52px] flex-wrap items-center justify-between gap-x-4 gap-y-2 border-b border-line px-5 py-3",
        className,
      )}
    >
      <div className="flex min-w-0 items-center gap-1.5">
        <h2 className="text-[15px] font-semibold text-navy-900">{title}</h2>
        {subtitle && <InfoTip>{subtitle}</InfoTip>}
      </div>
      {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
    </div>
  );
}

const TONES: Record<string, string> = {
  teal: "bg-teal-50 text-teal-700 ring-teal-700/15",
  green: "bg-green-100 text-green-700 ring-green-700/20",
  navy: "bg-navy-100 text-navy-800 ring-navy-800/15",
  "navy-soft": "bg-[#eef2f8] text-navy-700 ring-navy-700/10",
  violet: "bg-violet-100 text-violet-700 ring-violet-700/15",
  amber: "bg-amber-100 text-amber-700 ring-amber-700/20",
  red: "bg-red-100 text-red-700 ring-red-700/20",
  grey: "bg-[#efeee9] text-muted ring-black/5",
};

export function Badge({
  tone = "grey",
  children,
  className,
  title,
}: { tone?: string; children: ReactNode; className?: string; title?: string }) {
  return (
    <span
      title={title}
      className={cn(
        "inline-flex items-center gap-1 rounded-[3px] px-1.5 py-0.5 text-[11.5px] font-medium ring-1 ring-inset whitespace-nowrap",
        TONES[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}

const STATUS_ICON = {
  observed: CheckCircle2,
  contractual: FileSignature,
  estimated: Gauge,
  illustrative: FlaskConical,
  unknown: CircleHelp,
  na: MinusCircle,
} as const;

/** Evidence status chip: label + icon + tone (never colour alone). */
export function StatusBadge({ m }: { m: string }) {
  const s = MEASUREMENT[m] ?? { label: m, tone: "grey", help: "", icon: "na" };
  const Icon = STATUS_ICON[s.icon as keyof typeof STATUS_ICON] ?? MinusCircle;
  return (
    <Badge tone={s.tone} title={s.help && t(s.help)}>
      <Icon className="h-3 w-3" aria-hidden />
      {t(s.label)}
    </Badge>
  );
}

const MONEY = /^(−?)([A-Z]{3}) (.+)$/;

/** An amount as one unit: small currency code, tabular figure, never wrapped. Plain text passes through. */
export function Money({ value, className }: { value: ReactNode; className?: string }) {
  const m = typeof value === "string" ? MONEY.exec(value) : null;
  if (!m) return <span className={cn("money num", className)}>{value}</span>;
  return (
    <span className={cn("money num", className)}>
      <span className="mr-[0.3em] align-[0.12em] text-[0.6em] font-medium tracking-wide opacity-70">{m[2]}</span>
      {m[1]}
      {m[3]}
    </span>
  );
}

/** Figures in a row of equal cards that reflow instead of squeezing (no wrapped numbers on narrow screens). */
export function StatGrid({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cn("grid grid-cols-[repeat(auto-fit,minmax(220px,1fr))] gap-3", className)}>{children}</div>;
}

export function Kpi({
  label,
  value,
  sub,
  tone,
  help,
  onClick,
}: {
  label: string;
  value: ReactNode;
  sub?: ReactNode;
  tone?: "teal" | "amber" | "navy";
  help?: string;
  /** Opens how the number is calculated. */
  onClick?: () => void;
}) {
  const cls = cn(
    "mt-2 block text-[26px] font-semibold leading-none tracking-tight",
    tone === "teal" ? "text-teal-700" : tone === "amber" ? "text-amber-700" : "text-navy-900",
  );
  return (
    <div
      className="flex min-h-[116px] flex-col rounded-[var(--radius-card)] border border-line bg-surface px-5 py-4"
      title={help}
    >
      <div className="truncate text-[12.5px] font-medium text-muted" title={label}>
        {label}
      </div>
      {onClick ? (
        <button
          type="button"
          onClick={onClick}
          title={t("How is this calculated?")}
          className={cn(cls, "text-left decoration-dotted decoration-1 underline-offset-[6px] hover:underline")}
        >
          <Money value={value} />
        </button>
      ) : (
        <div className={cls}>
          <Money value={value} />
        </div>
      )}
      {sub && <div className="mt-auto pt-3 text-[12.5px] leading-snug text-muted">{sub}</div>}
    </div>
  );
}

export function Dialog({
  open,
  onOpenChange,
  title,
  description,
  children,
  wide,
}: {
  open: boolean;
  onOpenChange: (o: boolean) => void;
  title: string;
  description?: string;
  children: ReactNode;
  wide?: boolean;
}) {
  return (
    <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="fixed inset-0 z-40 bg-navy-950/40 backdrop-blur-[1px]" />
        <DialogPrimitive.Content
          className={cn(
            "fixed left-1/2 top-1/2 z-50 max-h-[88vh] w-[calc(100vw-32px)] -translate-x-1/2 -translate-y-1/2 overflow-auto rounded-xl border border-line bg-surface p-5 shadow-2xl",
            wide ? "max-w-4xl" : "max-w-lg",
          )}
        >
          <div className="mb-3 flex items-start justify-between gap-3">
            <div>
              <DialogPrimitive.Title className="text-base font-semibold text-navy-900">{title}</DialogPrimitive.Title>
              {description && (
                <DialogPrimitive.Description className="mt-1 text-[13px] text-muted">
                  {description}
                </DialogPrimitive.Description>
              )}
            </div>
            <DialogPrimitive.Close className="rounded p-1 text-muted hover:bg-paper" aria-label={t("Close")}>
              <X className="h-4 w-4" />
            </DialogPrimitive.Close>
          </div>
          {children}
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}

export function Tip({
  content,
  children,
  open,
  onOpenChange,
}: { content: ReactNode; children: ReactNode; open?: boolean; onOpenChange?: (o: boolean) => void }) {
  return (
    <TooltipPrimitive.Provider delayDuration={150}>
      <TooltipPrimitive.Root open={open} onOpenChange={onOpenChange}>
        <TooltipPrimitive.Trigger asChild>{children}</TooltipPrimitive.Trigger>
        <TooltipPrimitive.Portal>
          <TooltipPrimitive.Content
            sideOffset={6}
            className="pce-in z-50 max-w-[min(20rem,calc(100vw-2rem))] rounded-[var(--radius-control)] bg-navy-950 px-2.5 py-1.5 text-[12px] leading-snug text-white shadow-lg"
          >
            {content}
          </TooltipPrimitive.Content>
        </TooltipPrimitive.Portal>
      </TooltipPrimitive.Root>
    </TooltipPrimitive.Provider>
  );
}

export function Field({ label, hint, children }: { label: string; hint?: string; children: ReactNode }) {
  return (
    // biome-ignore lint/a11y/noLabelWithoutControl: the control is passed as children
    <label className="block">
      <span className="text-[12.5px] font-medium text-ink">{label}</span>
      <div className="mt-1">{children}</div>
      {hint && <span className="mt-1 block text-[11.5px] text-subtle">{hint}</span>}
    </label>
  );
}

export const inputCls =
  "h-9 w-full rounded-[var(--radius-control)] border border-line-strong bg-surface px-3 text-sm text-ink placeholder:text-subtle focus:border-teal-600 focus:outline-none focus:ring-2 focus:ring-teal-600/20 num";

export function Empty({ icon, title, children }: { icon?: ReactNode; title: string; children?: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 px-6 py-12 text-center">
      {icon && <div className="text-subtle">{icon}</div>}
      <div className="text-[15px] font-semibold text-navy-900">{title}</div>
      {children && <div className="max-w-md text-[13px] text-muted">{children}</div>}
    </div>
  );
}

export function Spinner({ label }: { label?: string }) {
  return (
    <output className="flex items-center gap-2 p-8 text-sm text-muted">
      <Loader2 className="h-4 w-4 animate-spin" /> {label ?? t("Loading")}…
    </output>
  );
}

export function ErrorBox({ error }: { error: unknown }) {
  return (
    <div className="m-4 rounded-md border border-red-700/20 bg-red-100 px-4 py-3 text-sm text-red-700" role="alert">
      {error instanceof Error ? error.message : String(error)}
    </div>
  );
}

/** The (i) next to a title: explanations stay one hover or tap away instead of crowding the screen. */
/** (i) next to a title: opens on hover and focus, and on tap, so it also works on touch screens. */
export function InfoTip({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);
  return (
    <Tip content={children} open={open} onOpenChange={setOpen}>
      <button
        type="button"
        aria-label={t("More information")}
        aria-expanded={open}
        onClick={(e) => {
          e.preventDefault(); // Radix closes a tooltip on click; a tap must open it instead
          setOpen(!open);
        }}
        className="inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-subtle hover:bg-paper hover:text-navy-900 focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-600/30"
      >
        <Info className="h-4 w-4" />
      </button>
    </Tip>
  );
}

/** A secondary section folded behind one line: title, a short summary, and "Show details". */
export function Fold({ title, summary, children }: { title: string; summary?: ReactNode; children: ReactNode }) {
  const [open, setOpen] = useState(false);
  return (
    <div>
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between gap-3 rounded-[var(--radius-card)] border border-line bg-surface px-5 py-3 text-left hover:bg-paper"
      >
        <span className="flex min-w-0 items-center gap-2">
          <ChevronDown className={cn("h-4 w-4 shrink-0 text-subtle transition-transform", open && "rotate-180")} />
          <span className="text-[14px] font-semibold text-navy-900">{title}</span>
          {summary && <span className="truncate text-[13px] text-muted">{summary}</span>}
        </span>
        <span className="shrink-0 text-[12.5px] font-medium text-teal-700">
          {open ? t("Hide details") : t("Show details")}
        </span>
      </button>
      {open && <div className="mt-2">{children}</div>}
    </div>
  );
}
