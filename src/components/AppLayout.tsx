import { useState } from 'react';
import { Outlet, Link, NavLink, useLocation } from 'react-router-dom';
import { Home, Upload, LogOut, UserCircle, Settings, ShieldCheck, Menu, Search } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from './ui/Button';
import { NotificationBell } from '@/features/notifications/components/NotificationBell';
import { ConnectionStatusIndicator } from './ConnectionStatusIndicator';
import { SystemHealthBanner } from './SystemHealthBanner';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/DropdownMenu";

const AppLayout = () => {
  const { user, logout } = useAuth();
  const location = useLocation();
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const isAdmin = user?.role && user.role.toString().toUpperCase().includes('ADMIN');
  const layoutClass = isSidebarCollapsed
    ? 'grid min-h-screen w-full md:grid-cols-[72px_1fr]'
    : 'grid min-h-screen w-full md:grid-cols-[220px_1fr] lg:grid-cols-[280px_1fr]';

  const navLinkClasses = (isActive: boolean) =>
    `flex items-center px-4 py-2 text-sm font-medium rounded-md transition-colors ${
      isActive
        ? 'bg-primary text-primary-foreground'
        : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
    }`;

  return (
    <div className={`${layoutClass} bg-white text-slate-900`}>
      <div className={`hidden border-r border-[#f2eadf] bg-white/80 backdrop-blur md:block ${isSidebarCollapsed ? 'w-[72px]' : ''}`}>
        <div className="flex h-full max-h-screen flex-col gap-2">
          <div className={`flex h-14 items-center border-b border-[#f2eadf] ${isSidebarCollapsed ? 'justify-center px-0' : 'px-4 lg:px-6' } lg:h-[60px]`}>
            <button
              className="inline-flex items-center justify-center rounded-md border p-2 text-sm"
              onClick={() => setIsSidebarCollapsed((prev) => !prev)}
              aria-label="Alternar menu lateral"
            >
              <Menu className="h-4 w-4" />
            </button>
            {!isSidebarCollapsed && (
              <Link to="/" className="ml-3 flex items-center gap-2 font-semibold">
                <span>Síntese</span>
              </Link>
            )}
          </div>
          <div className="flex-1">
            <nav className={`grid items-start ${isSidebarCollapsed ? 'px-1' : 'px-2 text-sm font-medium lg:px-4'}`}>
              <NavLink to="/dashboard" className={({ isActive }) => navLinkClasses(isActive)}>
                <Home className="mr-3 h-4 w-4" />
                {!isSidebarCollapsed && 'Painel'}
              </NavLink>
              <NavLink to="/upload" className={({ isActive }) => navLinkClasses(isActive)}>
                <Upload className="mr-3 h-4 w-4" />
                {!isSidebarCollapsed && 'Envios'}
              </NavLink>
              <NavLink to="/search" className={({ isActive }) => navLinkClasses(isActive)}>
                <Search className="mr-3 h-4 w-4" />
                {!isSidebarCollapsed && 'Busca'}
              </NavLink>
              {isAdmin && (
                <NavLink to="/admin/dashboard" className={({ isActive }) => navLinkClasses(isActive)}>
                  <ShieldCheck className="mr-3 h-4 w-4" />
                  {!isSidebarCollapsed && 'Painel Admin'}
                </NavLink>
              )}
            </nav>
          </div>
        </div>
      </div>
      <div className="flex min-w-0 flex-col">
        <SystemHealthBanner />
        <header className="flex h-14 items-center gap-4 border-b border-[#f2eadf] bg-white/70 px-4 backdrop-blur lg:h-[60px] lg:px-6">
          <div className="w-full flex-1"></div>
          <div className="flex items-center gap-4">
            <ConnectionStatusIndicator /> {/* Add the indicator */}
            <NotificationBell />
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="secondary" size="icon" className="rounded-full">
                  <UserCircle className="h-5 w-5" />
                  <span className="sr-only">Toggle user menu</span>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuLabel>{user?.email}</DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem asChild>
                  <Link to="/settings">
                    <Settings className="mr-2 h-4 w-4" />
                    <span>Configurações</span>
                  </Link>
                </DropdownMenuItem>
                {isAdmin && (
                  <DropdownMenuItem asChild>
                    <Link to={location.pathname.startsWith('/admin') ? '/dashboard' : '/admin/dashboard'}>
                      <ShieldCheck className="mr-2 h-4 w-4" />
                      <span>{location.pathname.startsWith('/admin') ? 'Painel do usuário' : 'Painel Admin'}</span>
                    </Link>
                  </DropdownMenuItem>
                )}
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={logout}>
                  <LogOut className="mr-2 h-4 w-4" />
                  <span>Sair</span>
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </header>
        <main className="flex min-w-0 flex-1 flex-col gap-4 bg-transparent p-4 lg:gap-6 lg:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
};

export default AppLayout;
