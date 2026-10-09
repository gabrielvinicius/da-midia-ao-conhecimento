import type { ReactNode } from "react";
import { NavLink } from "react-router-dom";
import { cn } from "@/lib/utils";

export type NavItem = { to: string; label: string; icon: ReactNode };

/**
 * Navegação no celular, abaixo do cabeçalho. O menu lateral some abaixo de
 * 768 px e não havia outro caminho: a Busca e as páginas da administração
 * ficavam inacessíveis no telefone.
 */
export const MobileNav = ({ items }: { items: NavItem[] }) => (
  <nav aria-label="Navegação" className="flex gap-1 overflow-x-auto border-b border-[#f2eadf] bg-white px-2 py-1.5 md:hidden">
    {items.map((item) => (
      <NavLink
        key={item.to}
        to={item.to}
        className={({ isActive }) =>
          cn(
            "flex items-center gap-1.5 whitespace-nowrap rounded-md px-3 py-1.5 text-sm font-medium",
            isActive ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-accent",
          )
        }
      >
        {item.icon}
        {item.label}
      </NavLink>
    ))}
  </nav>
);
