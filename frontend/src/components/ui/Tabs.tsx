import { useRef, type KeyboardEvent, type ReactNode } from "react";
import { cn } from "@/lib/utils";

export type TabItem = { id: string; label: string; count?: number; icon?: ReactNode };

/**
 * Abas acessíveis (padrão WAI-ARIA): setas esquerda/direita, Home e End
 * movem entre as abas. O conteúdo da aba ativa vem em ``children``.
 */
export const Tabs = ({
  tabs,
  active,
  onChange,
  label,
  children,
  className,
}: {
  tabs: TabItem[];
  active: string;
  onChange: (id: string) => void;
  label: string;
  children: ReactNode;
  className?: string;
}) => {
  const refs = useRef<Record<string, HTMLButtonElement | null>>({});

  const onKeyDown = (event: KeyboardEvent, index: number) => {
    const last = tabs.length - 1;
    const next =
      event.key === "ArrowRight" ? (index === last ? 0 : index + 1)
      : event.key === "ArrowLeft" ? (index === 0 ? last : index - 1)
      : event.key === "Home" ? 0
      : event.key === "End" ? last
      : null;
    if (next === null) return;
    event.preventDefault();
    onChange(tabs[next].id);
    refs.current[tabs[next].id]?.focus();
  };

  return (
    <div className={className}>
      <div
        role="tablist"
        aria-label={label}
        className="flex gap-1 overflow-x-auto border-b border-slate-200 scrollbar-none"
      >
        {tabs.map((tab, index) => {
          const selected = tab.id === active;
          return (
            <button
              key={tab.id}
              ref={(el) => { refs.current[tab.id] = el; }}
              role="tab"
              type="button"
              id={`tab-${tab.id}`}
              aria-selected={selected}
              aria-controls={`panel-${tab.id}`}
              tabIndex={selected ? 0 : -1}
              onClick={() => onChange(tab.id)}
              onKeyDown={(e) => onKeyDown(e, index)}
              className={cn(
                "-mb-px inline-flex shrink-0 items-center gap-2 border-b-2 px-3 py-2.5 text-sm font-medium transition-colors",
                "focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-primary/40 rounded-t-md",
                selected
                  ? "border-amber-500 text-slate-950"
                  : "border-transparent text-slate-500 hover:text-slate-800",
              )}
            >
              {tab.icon}
              {tab.label}
              {tab.count != null && (
                <span
                  className={cn(
                    "rounded-full px-1.5 text-[11px] tabular-nums",
                    selected ? "bg-amber-100 text-amber-800" : "bg-slate-100 text-slate-500",
                  )}
                >
                  {tab.count}
                </span>
              )}
            </button>
          );
        })}
      </div>
      <div role="tabpanel" id={`panel-${active}`} aria-labelledby={`tab-${active}`} className="pt-5" tabIndex={0}>
        {children}
      </div>
    </div>
  );
};
